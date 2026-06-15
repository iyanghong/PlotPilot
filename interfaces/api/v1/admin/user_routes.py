"""用户管理 API 路由 — 作者：Axelton"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from application.admin.user_admin_service import UserAdminService
from application.auth.auth_service import AuthService
from domain.auth.entities.user import User
from interfaces.api.dependencies import (
    _get_auth_service,
    require_admin,
)
from interfaces.api.responses import SuccessResponse, PaginatedResponse
from infrastructure.persistence.database.connection import get_database
from infrastructure.persistence.repositories.sqlite_user_repository import (
    SqliteUserRepository,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_user_admin_service(
    auth_service: AuthService = Depends(_get_auth_service),
) -> UserAdminService:
    """依赖注入：创建 UserAdminService 实例"""
    repo = SqliteUserRepository(get_database())
    return UserAdminService(user_repository=repo, auth_service=auth_service)


class CreateUserRequest(BaseModel):
    """创建用户请求体"""
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    role: str | None = Field(None, description="角色：admin 或 user，默认 user")


class UpdateUserRequest(BaseModel):
    """更新用户请求体"""
    role: str | None = Field(None, description="角色：admin 或 user")
    password: str | None = Field(None, min_length=6, max_length=128, description="新密码")


@router.get("/users", response_model=PaginatedResponse)
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str = Query("", description="用户名搜索关键词"),
    _admin: User = Depends(require_admin),
    service: UserAdminService = Depends(_get_user_admin_service),
):
    """获取用户列表（仅管理员）"""
    result = service.list_users(page=page, page_size=page_size, search=search)
    return PaginatedResponse(
        data=result["data"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/users", response_model=SuccessResponse)
async def create_user(
    request: CreateUserRequest,
    _admin: User = Depends(require_admin),
    service: UserAdminService = Depends(_get_user_admin_service),
):
    """创建用户（仅管理员）"""
    try:
        user = service.create_user(request.username, request.password, request.role)
        return SuccessResponse(
            data={"id": user.id, "username": user.username, "role": user.role.value},
            message="用户创建成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/users/{user_id}", response_model=SuccessResponse)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    _admin: User = Depends(require_admin),
    service: UserAdminService = Depends(_get_user_admin_service),
):
    """更新用户信息（仅管理员）"""
    try:
        user = service.update_user(user_id, role=request.role, password=request.password)
        return SuccessResponse(
            data={"id": user.id, "username": user.username, "role": user.role.value},
            message="用户更新成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: str,
    _admin: User = Depends(require_admin),
    service: UserAdminService = Depends(_get_user_admin_service),
):
    """删除用户（仅管理员）"""
    try:
        service.delete_user(user_id)
        return SuccessResponse(message="用户已删除")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
