"""灵感助手 SSE 流式端点 — 作者：Axelton"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from application.assist.assist_service import AssistService
from infrastructure.persistence.assist_repository import SqliteAssistRepository
from infrastructure.persistence.database.connection import get_database
from infrastructure.ai.llm_client import LLMClient

router = APIRouter()


class InspireRequest(BaseModel):
    """灵感助手请求体"""
    novel_id: str = Field(..., description="书目 ID")
    session_id: Optional[str] = Field(None, description="会话 ID，首次为空")
    strategy: Optional[str] = Field(None, description="策略名，首次必传")
    action: str = Field(..., description="操作类型: chat / generate_fields / resume")
    message: Optional[str] = Field(None, description="用户消息（action=chat 时必传）")


def _get_service() -> AssistService:
    """创建服务实例"""
    db = get_database()
    repo = SqliteAssistRepository(db)
    llm = LLMClient()
    return AssistService(repo, llm)


async def _event_gen(service: AssistService, req: InspireRequest, request: Request):
    """SSE 事件生成器"""
    try:
        if req.action == "resume":
            # 恢复会话 — 非流式 JSON
            if not req.session_id:
                yield f"data: {json.dumps({'error': 'session_id 不能为空'})}\n\n"
                return
            try:
                data = await service.resume_session(req.session_id)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            except ValueError as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # 获取或创建会话
        if req.session_id:
            session = await service.get_session(req.session_id)
            if not session:
                yield f"data: {json.dumps({'error': '会话不存在'})}\n\n"
                return
        else:
            if not req.strategy:
                yield f"data: {json.dumps({'error': '首次请求必须提供 strategy'})}\n\n"
                return
            session = await service.get_or_create_session(req.novel_id, req.strategy)
            # 发送 session_created 事件
            yield (
                f"event: session_created\n"
                f"data: {json.dumps({'session_id': session.id, 'strategy': session.strategy.value})}\n\n"
            )

        if req.action == "chat":
            if not req.message:
                yield f"data: {json.dumps({'error': 'message 不能为空'})}\n\n"
                return

            async for event in service.chat(session, req.message):
                if await request.is_disconnected():
                    break

                event_type = event["type"]

                if event_type == "chat_chunk":
                    yield f"event: chat_chunk\ndata: {json.dumps({'content': event['content']})}\n\n"

                elif event_type == "tool_call":
                    yield f"event: tool_call\ndata: {json.dumps({'name': event['name'], 'args': event['args']}, ensure_ascii=False)}\n\n"

                elif event_type == "tool_result":
                    yield f"event: tool_result\ndata: {json.dumps({'name': event['name'], 'summary': event['summary']}, ensure_ascii=False)}\n\n"

                elif event_type == "chat_done":
                    yield f"event: chat_done\ndata: {json.dumps({'message_type': event['message_type']})}\n\n"

        elif req.action == "generate_fields":
            # 字段提取（非流式）
            fields = await service.generate_fields(session)
            yield (
                f"event: fields_done\n"
                f"data: {json.dumps(fields.to_dict(), ensure_ascii=False)}\n\n"
            )

        else:
            yield f"data: {json.dumps({'error': f'未知 action: {req.action}'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/assist/inspire", tags=["灵感助手"])
async def inspire(request: Request, body: InspireRequest):
    """灵感助手 SSE 流式端点"""
    service = _get_service()
    return StreamingResponse(
        _event_gen(service, body, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
