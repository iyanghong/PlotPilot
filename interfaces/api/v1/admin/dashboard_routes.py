"""驾驶舱 API 路由 — 作者：Axelton"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from application.admin.dashboard_service import DashboardService
from domain.auth.entities.user import User
from interfaces.api.dependencies import get_current_user, require_admin
from interfaces.api.responses import SuccessResponse
from infrastructure.persistence.database.connection import get_database

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_dashboard_service() -> DashboardService:
    """获取驾驶舱聚合统计服务"""
    return DashboardService(get_database())


@router.get("/dashboard", response_model=SuccessResponse)
async def get_dashboard(
    scope: str = Query("all", description="统计范围: all 或 user"),
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(_get_dashboard_service),
):
    """获取驾驶舱全量统计数据。

    admin 用户 scope=all 返回全局数据；
    普通用户 scope=user 仅返回自己的书籍数据。
    """
    if scope == "all" and not user.is_admin():
        scope = "user"
    user_id = user.id if scope == "user" else None
    data = service.get_full_dashboard(scope=scope, user_id=user_id)
    return SuccessResponse(data=data, message="ok")
