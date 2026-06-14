"""守护进程主循环 — Phase 5 从 AutopilotDaemon 收拢到 engine/runtime

Phase 11: 并行调度 — 多本小说在同一轮循环中并发处理，每本小说拥有独立熔断器。
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# 最大并行小说数（环境变量可控，默认 3）
_MAX_CONCURRENT_NOVELS = int(os.getenv("AUTOPILOT_MAX_CONCURRENT_NOVELS", "3"))


@runtime_checkable
class DaemonLoopHost(Protocol):
    """守护进程主循环所需的最小 host 接口"""

    poll_interval: int
    circuit_breaker: Any

    def _write_daemon_heartbeat(self) -> None: ...
    def _get_active_novels(self) -> list: ...
    def _cleanup_stale_stop_signals(self, active_novels: list) -> None: ...
    async def _process_novel(self, novel: Any) -> None: ...


def run_daemon_loop(host: DaemonLoopHost, *, banner: str | None = None) -> None:
    """守护进程主循环（并行调度）

    每轮循环中所有活跃小说并发处理，via ``asyncio.Semaphore`` 控制最大并行数。
    AutopilotDaemon、StoryPipelineRunner、EngineDaemon 共用此循环。
    """
    if banner:
        logger.info("=" * 80)
        logger.info(banner)
        logger.info("=" * 80)

    logger.info("并行调度模式：最多 %d 本小说同时处理", _MAX_CONCURRENT_NOVELS)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop_count = 0
    while True:
        loop_count += 1
        loop_start = time.time()

        host._write_daemon_heartbeat()

        # 全局熔断检查：仅当所有 per-novel 熔断器都打开时暂停
        if _all_breakers_open(host):
            cb = getattr(host, 'circuit_breaker', None)
            wait = cb.wait_seconds() if cb else host.poll_interval
            logger.warning("全部熔断器打开，暂停 %.0fs", wait)
            time.sleep(min(wait, host.poll_interval))
            continue

        try:
            try:
                from application.engine.services.streaming_bus import streaming_bus

                streaming_bus.consume_stop_signals()
            except Exception:
                pass

            active_novels = host._get_active_novels()

            if active_novels:
                host._cleanup_stale_stop_signals(active_novels)

            if loop_count % 10 == 1:
                logger.info("Loop #%s: 发现 %s 本活跃小说", loop_count, len(active_novels))

            if active_novels:
                # 并行调度：每本小说一个 asyncio.Task，Semaphore 控制槽位
                semaphore = asyncio.Semaphore(_MAX_CONCURRENT_NOVELS)

                async def _process_one(novel):
                    """单本小说的处理协程 — 获取槽位后执行全流程"""
                    nid = _novel_id_str(novel)
                    async with semaphore:
                        logger.debug("[%s] 获取处理槽位，开始本轮", nid)
                        novel_start = time.time()
                        try:
                            await host._process_novel(novel)
                        except Exception as e:
                            logger.error("[%s] 处理异常: %s", nid, e, exc_info=True)
                        novel_elapsed = time.time() - novel_start
                        logger.debug("[%s] 处理耗时: %.2fs", nid, novel_elapsed)

                async def _run_parallel():
                    tasks = [
                        asyncio.create_task(_process_one(novel))
                        for novel in active_novels
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)

                loop.run_until_complete(_run_parallel())

        except Exception as e:
            logger.error("Daemon 顶层异常: %s", e, exc_info=True)

        loop_elapsed = time.time() - loop_start
        if loop_elapsed > host.poll_interval * 2:
            logger.warning("Loop #%s 耗时过长: %.2fs", loop_count, loop_elapsed)

        time.sleep(host.poll_interval)


def _all_breakers_open(host) -> bool:
    """检查是否所有 per-novel 熔断器都已打开

    仅当每个已创建的小说熔断器都是 OPEN 状态时返回 True。
    如果还没有任何 per-novel 熔断器，回退到全局 circuit_breaker。
    """
    per_novel = getattr(host, '_circuit_breakers', None)
    if per_novel:
        if not per_novel:
            # 无活跃熔断器 → 不暂停
            return False
        return all(cb.is_open() for cb in per_novel.values())

    # 回退：全局熔断器
    cb = getattr(host, 'circuit_breaker', None)
    return cb is not None and cb.is_open()


def _novel_id_str(novel) -> str:
    """从 novel 对象安全提取 id 字符串"""
    try:
        return getattr(getattr(novel, 'novel_id', None), 'value', str(novel))
    except Exception:
        return str(novel)
