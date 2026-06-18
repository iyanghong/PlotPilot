"""版本管理路由 — git 版本检测与更新 — 作者：Axelton"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from interfaces.api.dependencies import require_admin
from interfaces.api.settings import APP_RELEASE_VERSION, BACKEND_BUILD_ID

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# 仓库根目录（PlotPilot 项目根）
_REPO_ROOT = Path(__file__).resolve().parents[4]


class VersionStatusResponse(BaseModel):
    """版本状态响应"""
    current_version: str
    build_id: str
    git_commit: str
    git_branch: str
    commits_behind: int  # 落后远程的提交数，0 表示已是最新
    has_local_changes: bool  # 是否有未提交的本地改动
    update_available: bool  # 是否有可用的更新
    last_checked_at: str


class UpdateResponse(BaseModel):
    """更新操作响应"""
    success: bool
    previous_commit: str
    new_commit: str | None = None
    message: str = ""


def _run_git(*args: str, timeout: int = 30) -> tuple[int, str, str]:
    """在仓库根目录执行 git 命令，返回 (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return -1, "", str(e)


@router.get("/version", response_model=VersionStatusResponse)
async def check_version(_admin=Depends(require_admin)):
    """检测当前版本状态 — 比较本地与远程 git 仓库"""
    from datetime import datetime, timezone

    # 当前 commit hash
    _, commit, _ = _run_git("rev-parse", "--short", "HEAD")
    if not commit:
        commit = "unknown"

    # 当前分支
    _, branch, _ = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    if not branch:
        branch = "unknown"

    # 检查本地未提交改动
    rc, status_out, _ = _run_git("status", "--porcelain")
    has_local_changes = rc == 0 and bool(status_out)

    # 拉取远程最新信息（不合并）
    commits_behind = 0
    update_available = False
    try:
        _, _, fetch_err = _run_git("fetch", "origin", timeout=60)
        if fetch_err and "fatal" not in fetch_err.lower():
            logger.debug("git fetch 输出: %s", fetch_err)

        # 检查落后远程多少提交
        rc, behind_str, _ = _run_git(
            "rev-list", "--count", f"HEAD..@{'{u}'}"
        )
        if rc == 0 and behind_str.isdigit():
            commits_behind = int(behind_str)
            update_available = commits_behind > 0
    except Exception as e:
        logger.warning("git fetch/check 失败: %s", e)

    return VersionStatusResponse(
        current_version=APP_RELEASE_VERSION,
        build_id=BACKEND_BUILD_ID,
        git_commit=commit,
        git_branch=branch,
        commits_behind=commits_behind,
        has_local_changes=has_local_changes,
        update_available=update_available,
        last_checked_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/version/update", response_model=UpdateResponse)
async def trigger_update(_admin=Depends(require_admin)):
    """触发 git pull 更新 — 仅支持 fast-forward"""
    from datetime import datetime, timezone

    # 先检查本地是否有未提交改动
    _, status_out, _ = _run_git("status", "--porcelain")
    if status_out:
        return UpdateResponse(
            success=False,
            previous_commit="",
            message="存在未提交的本地改动，请先提交或暂存后再更新",
        )

    # 获取更新前 commit
    _, prev_commit, _ = _run_git("rev-parse", "--short", "HEAD")
    if not prev_commit:
        prev_commit = "unknown"

    # 先 fetch
    rc, _, fetch_err = _run_git("fetch", "origin", timeout=60)
    if rc != 0:
        return UpdateResponse(
            success=False,
            previous_commit=prev_commit,
            message=f"git fetch 失败: {fetch_err}",
        )

    # 检查是否已是最新
    rc, behind_str, _ = _run_git("rev-list", "--count", f"HEAD..@{'{u}'}")
    if rc != 0 or not behind_str.isdigit():
        return UpdateResponse(
            success=False,
            previous_commit=prev_commit,
            message="无法检测远程仓库状态，请确认已配置 upstream 分支",
        )
    if int(behind_str) == 0:
        # 已是最新
        return UpdateResponse(
            success=True,
            previous_commit=prev_commit,
            new_commit=prev_commit,
            message="已是最新版本，无需更新",
        )

    # 执行 ff-only pull
    rc, pull_out, pull_err = _run_git("pull", "--ff-only", timeout=120)
    if rc != 0:
        return UpdateResponse(
            success=False,
            previous_commit=prev_commit,
            message=f"git pull 失败: {pull_err or pull_out}",
        )

    # 获取更新后 commit
    _, new_commit, _ = _run_git("rev-parse", "--short", "HEAD")
    if not new_commit:
        new_commit = "unknown"

    logger.info("版本更新完成: %s → %s", prev_commit, new_commit)

    return UpdateResponse(
        success=True,
        previous_commit=prev_commit,
        new_commit=new_commit,
        message=f"更新成功: {prev_commit} → {new_commit}",
    )
