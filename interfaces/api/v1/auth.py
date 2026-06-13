"""认证 API 路由

作者: Axelton
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from domain.auth.entities.user import User, UserRole
from interfaces.api.dependencies import (
    _get_auth_service,
    get_current_user,
    require_admin,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名", min_length=1, max_length=64)
    password: str = Field(..., description="密码", min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., description="用户名", min_length=1, max_length=64)
    password: str = Field(..., description="密码", min_length=6, max_length=128)
    role: Optional[str] = Field(None, description="角色：user 或 admin（仅管理员可指定）")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录

    Args:
        request: 登录请求（用户名 + 密码）

    Returns:
        TokenResponse: JWT Token 及用户信息

    Raises:
        HTTPException 401: 用户名或密码错误
    """
    auth_service = _get_auth_service()
    result = auth_service.login(request.username, request.password)
    if result is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user, token = result
    return TokenResponse(
        access_token=token,
        username=user.username,
        role=user.role.value,
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    request: RegisterRequest,
    current_user: User = Depends(require_admin),
):
    """注册新用户（仅管理员可操作）

    Args:
        request: 注册请求（用户名、密码、可选角色）
        current_user: 当前管理员（自动注入）

    Returns:
        UserResponse: 已创建的用户信息

    Raises:
        HTTPException 403: 非管理员操作
        HTTPException 409: 用户名已存在
    """
    auth_service = _get_auth_service()

    role = UserRole.USER
    if request.role == "admin":
        role = UserRole.ADMIN

    user = auth_service.register(
        username=request.username,
        password=request.password,
        role=role,
        admin_user=current_user,
    )
    if user is None:
        raise HTTPException(status_code=409, detail=f"用户名 '{request.username}' 已存在")

    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role.value,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息

    Args:
        current_user: 当前用户（自动注入）

    Returns:
        UserResponse: 当前用户信息
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
    )
