"""书籍管理 API 路由 — 作者：Axelton"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from application.admin.book_admin_service import BookAdminService
from domain.auth.entities.user import User
from domain.novel.value_objects.novel_id import NovelId
from interfaces.api.dependencies import require_admin
from interfaces.api.responses import SuccessResponse, PaginatedResponse
from infrastructure.persistence.database.connection import get_database
from infrastructure.persistence.database.sqlite_novel_repository import SqliteNovelRepository

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_book_admin_service() -> BookAdminService:
    """依赖注入：创建 BookAdminService 实例"""
    repo = SqliteNovelRepository(get_database())
    return BookAdminService(novel_repository=repo, db=get_database())


class TransferOwnerRequest(BaseModel):
    """书籍归属转移请求体"""
    user_id: str = Field(..., description="新所有者的用户 ID")


@router.get("/books", response_model=PaginatedResponse)
async def list_books(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str = Query("", description="搜索关键词（匹配标题或 ID）"),
    user_id: str = Query("", description="按所属用户过滤"),
    stage: str = Query("", description="按当前阶段过滤"),
    _admin: User = Depends(require_admin),
    service: BookAdminService = Depends(_get_book_admin_service),
):
    """获取书籍列表（仅管理员）"""
    result = service.list_books(
        page=page, page_size=page_size,
        search=search, user_id=user_id, stage=stage,
    )
    return PaginatedResponse(
        data=result["data"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/books/{novel_id}", response_model=SuccessResponse)
async def get_book_detail(
    novel_id: str,
    _admin: User = Depends(require_admin),
    service: BookAdminService = Depends(_get_book_admin_service),
):
    """获取书籍详情（仅管理员）"""
    # 使用搜索匹配标题或 ID，然后精确匹配
    result = service.list_books(search=novel_id, page_size=1)
    for book in result["data"]:
        if book["id"] == novel_id:
            return SuccessResponse(data=book)
    raise HTTPException(status_code=404, detail="书籍不存在")


@router.delete("/books/{novel_id}", response_model=SuccessResponse)
async def delete_book(
    novel_id: str,
    _admin: User = Depends(require_admin),
    service: BookAdminService = Depends(_get_book_admin_service),
):
    """删除书籍（仅管理员）"""
    service.delete_book(novel_id)
    return SuccessResponse(message="书籍已删除")


@router.patch("/books/{novel_id}/owner", response_model=SuccessResponse)
async def transfer_book_owner(
    novel_id: str,
    request: TransferOwnerRequest,
    _admin: User = Depends(require_admin),
    service: BookAdminService = Depends(_get_book_admin_service),
):
    """转移书籍归属（仅管理员）"""
    service.transfer_owner(novel_id, request.user_id)
    return SuccessResponse(message="归属已转移")
