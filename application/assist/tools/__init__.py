"""灵感助手工具包 — 作者：Axelton"""
from infrastructure.ai.tool_registry import ToolRegistry, Tool

from .lookup_genre import lookup_genre_templates


async def _handle_lookup(args: dict) -> str:
    """异步包装 lookup_genre_templates，满足 Tool.handler 的 Callable 签名"""
    return await lookup_genre_templates(args["genre_keyword"])


def register_assist_tools(registry: ToolRegistry) -> None:
    """将灵感助手工具注册到全局注册表"""
    registry.register(Tool(
        name="lookup_genre_templates",
        description="搜索小说类型的写作模板。当用户提到具体类型（末世、玄幻、悬疑、科幻等）时调用，获取该类型的世界观基调和写作画像作为建议参考。",
        parameters={
            "type": "object",
            "properties": {
                "genre_keyword": {
                    "type": "string",
                    "description": "用户提到的类型关键词，如「末世」「玄幻」「悬疑」「科幻」",
                },
            },
            "required": ["genre_keyword"],
        },
        handler=_handle_lookup,
    ))
