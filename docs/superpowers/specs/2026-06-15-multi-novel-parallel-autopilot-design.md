# 多小说并行自动驾驶 — 设计规格

## 背景

当前自动驾驶守护进程 (`daemon_loop.py`) 使用 `for novel in active_novels` 顺序处理每本小说——小说 A 写完第 3 章后，小说 B 才能开始宏观规划，小说 C 才能开始章节审计。用户要求支持多本小说同时在不同生命周期阶段独立推进，互不等待。

## 目标

支持可配置的 N 本小说同时自动驾驶，每本小说拥有独立的：
- 生命周期状态机推进
- 熔断器隔离（一本小说的 API 故障不影响其他小说）
- LLM 调用（受全局限流控制）
- 停止信号响应（停止小说 A 不影响小说 B/C）

## 核心方案：`asyncio.Task` + `asyncio.Semaphore`

在守护进程的单进程中，将每本小说的 `_process_novel()` 调度为独立 `asyncio.Task`，用 `asyncio.Semaphore` 控制最大活跃小说数。

### 为什么选单进程 asyncio 而非多进程

| 维度 | 单进程 asyncio（选用） | 多进程 per novel |
|------|----------------------|-------------------|
| SQLite 写竞争 | 已通过 CQRS 持久化队列解决 | 每个子进程都需要 IPC 到消费者线程 |
| 共享内存 | 直接读写 `__shared_state` dict | 需要 `multiprocessing.Manager` 代理（性能差） |
| 流式推送 | `streaming_bus` 直接 push 到 `mp.Queue` | 进程间 Queue 已存在，但需额外路由 |
| 内存开销 | 1 个 Python 进程 ~200MB | N 个进程 × ~200MB |
| 复杂度 | 低，仅改调度层 | 高，需重写进程管理、信号、共享状态 |
| 调试 | 单进程，pdb 直接附着 | 多进程，调试困难 |

**结论**：当前架构已具备 CQRS 持久化队列（杜绝 SQLite 写竞争），单进程 asyncio 并行即可实现目标，无需引入多进程的复杂性。

## 架构设计

### 1. 调度层改造：`daemon_loop.py`

```
当前：
  for novel in active_novels:
      run_until_complete(_process_novel(novel))  # 顺序阻塞

改后：
  semaphore = asyncio.Semaphore(max_concurrent_novels)
  tasks = []
  for novel in active_novels:
      task = asyncio.create_task(_process_one_novel(novel, semaphore))
      tasks.append(task)
  # 并行执行所有任务，但只允许 max_concurrent_novels 本同时持有信号量
  await asyncio.gather(*tasks, return_exceptions=True)
```

每本小说的 `_process_one_novel` 在执行前先 `async with semaphore:` 获取槽位，无槽位时自动挂起（不消耗 CPU）。池中某小说完成当前阶段并释放槽位后，等待中的小说自动接管。

### 2. 熔断器隔离：per-novel CircuitBreaker

**当前状态**：全局单例 `CircuitBreaker`——一本小说的 API 故障会让所有小说一起熔断。

**改后**：`DaemonHostMixin` 维护 `_circuit_breakers: Dict[str, CircuitBreaker]`（key = novel_id.value），每本小说独立计数：

```python
def _get_circuit_breaker(self, novel_id: str) -> CircuitBreaker:
    if novel_id not in self._circuit_breakers:
        self._circuit_breakers[novel_id] = CircuitBreaker(
            failure_threshold=5,
            reset_timeout=120,
        )
    return self._circuit_breakers[novel_id]
```

主循环的全局熔断检查改为：只当**所有**小说的熔断器都打开时，才暂停主循环。

### 3. LLM 全局限流

新增 `asyncio.Semaphore` 控制同时进行的 LLM 调用数量，防止超出 API 速率限制或本地内存上限：

```python
# daemon_loop.py 或 daemon_host.py
LLM_SEMAPHORE = asyncio.Semaphore(llm_max_concurrency)
```

所有 LLM 调用路径在执行前 `async with LLM_SEMAPHORE:` 获取许可。

影响的方法（均已有 `async` 签名）：
- `_call_with_timeout()` — 已有超时保护，仅需外包信号量
- `_stream_llm_with_stop_watch()` — 流式生成
- `_stream_one_beat()` — 节拍写作
- `generate_fields()` — 灵感助手字段提取（非自动驾驶路径，但也受益）

### 4. 配置项

在 `.env` 中新增两项，在 `application/core/config/` 中解析：

```bash
# 自动驾驶 — 同时处理的最大小说数（默认 3）
AUTOPILOT_MAX_CONCURRENT_NOVELS=3

# LLM — 同时进行的最大 API 调用数（默认 2，防止速率限制）
LLM_MAX_CONCURRENCY=2
```

### 5. ChromaDB 并发安全

ChromaDB 的 `PersistentClient` 内部使用 `sqlite3` 连接，单进程内多协程并发访问是安全的（内部有线程锁）。但需确保不在多个 `asyncio.to_thread()` 中并发写同一 collection。当前架构已通过 CQRS 持久化队列解决多写者问题，向量写入走同一消费者线程，无需改动。

## 修改清单

### 修改文件

| 文件 | 改动 | 说明 |
|------|------|------|
| `engine/runtime/daemon_loop.py` | 核心重写 | 顺序 `for` → `asyncio.gather` + `Semaphore` |
| `engine/runtime/daemon_host.py` | per-novel 熔断器 dict | 全局 `circuit_breaker` → `_circuit_breakers: dict` |
| `application/engine/services/circuit_breaker.py` | 不变 | 类本身无需改动，只改变使用方式 |
| `interfaces/daemon_manager.py` | 不变 | 进程生命周期管理不变 |
| `.env.example` | 新增 2 个配置项 | `AUTOPILOT_MAX_CONCURRENT_NOVELS`、`LLM_MAX_CONCURRENCY` |
| `application/core/config/` | 新增配置解析 | 读取上述两项（含默认值） |
| `infrastructure/ai/llm_client.py` | 可选：LLM 信号量接入点 | 在 `stream_generate` 入口处获取信号量 |

### 不改动的文件

- `infrastructure/persistence/` — CQRS 持久化队列已解决写竞争
- `infrastructure/ai/chromadb_vector_store.py` — 单进程内安全
- `application/engine/services/streaming_bus.py` — 已有 `mp.Queue`，多协程 push 安全
- `interfaces/api/` — API 层无变化

## 数据流

```
┌──────────────────────────────────────────────────────────┐
│                    Daemon Loop (单进程)                     │
│                                                          │
│  active_novels = [A, B, C, D, E]                          │
│  semaphore = Semaphore(3)  # max_concurrent_novels=3      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │ Novel A  │  │ Novel B  │  │ Novel C  │  ← 并行执行     │
│  │ 写第3章  │  │ 宏观规划 │  │ 章节审计 │                │
│  │ CB:✓     │  │ CB:✓     │  │ CB:✓     │  ← 独立熔断器  │
│  └──────────┘  └──────────┘  └──────────┘                │
│                                                          │
│  ┌──────────┐  ┌──────────┐                              │
│  │ Novel D  │  │ Novel E  │  ← 等待槽位释放               │
│  └──────────┘  └──────────┘                              │
│                                                          │
│  LLM Semaphore(2) — 跨所有小说限流                         │
└──────────────────────────────────────────────────────────┘
```

## 停止信号处理

每本小说的 `asyncio.Task` 在执行 `_process_novel()` 前先检查停止信号：

1. **全局停止** (`__all__`)：取消所有 Task，主循环退出
2. **单小说停止**：对应 Task 的 `_process_novel()` 内部检测到 `STOPPED` 后自然退出，不影响其他 Task
3. **槽位释放**：Task 退出时 `finally` 释放信号量

## 兼容性

- 将 `max_concurrent_novels` 设为 `1` 即可回到原顺序行为
- 现有小说不受影响——每本小说的状态机逻辑不变，仅调度方式改变
- 流式推送、前端 SSE 无需改动——`streaming_bus` 按 `novel_id` 路由，天然隔离

## 风险

| 风险 | 缓解 |
|------|------|
| 内存随并行小说数增长 | `max_concurrent_novels` 上限控制，默认 3 |
| LLM API 速率限制 | `LLM_MAX_CONCURRENCY` 限流，默认 2 |
| ChromaDB 并发异常 | 已走 CQRS 单写者线程，读操作单进程内安全 |
| asyncio.Task 异常未捕获 | `return_exceptions=True` + per-task 日志 |
