"""根据关键词搜索类型模板 — 灵感助手首批工具 — 作者：Axelton"""
from __future__ import annotations

import logging
from pathlib import Path
from functools import lru_cache

import yaml

logger = logging.getLogger(__name__)

# 从当前文件位置向上 3 级到达项目根目录（application/assist/tools -> application/assist -> application -> 项目根）
_TAXONOMY_YAML_PATH = (
    Path(__file__).resolve().parents[3] / "shared" / "taxonomy" / "builtin_cn_v1.yaml"
)


@lru_cache(maxsize=1)
def _load_lookup() -> dict[str, dict[str, str]]:
    """加载 taxonomy 并构建扁平查找表（模块级缓存）"""
    if not _TAXONOMY_YAML_PATH.is_file():
        logger.warning("taxonomy 文件不存在: %s", _TAXONOMY_YAML_PATH)
        return {}

    raw = yaml.safe_load(_TAXONOMY_YAML_PATH.read_text(encoding="utf-8"))
    lookup: dict[str, dict[str, str]] = {}

    for root in raw.get("roots", []):
        root_label = root.get("labels", {}).get("zh-CN", "").strip()
        facets = root.get("facets", {})
        root_wt = facets.get("world_tone", "")
        wp = facets.get("writing_profile", {})
        entry = {
            "world_tone": root_wt,
            "story_structure": wp.get("story_structure", ""),
            "pacing_control": wp.get("pacing_control", ""),
            "writing_style": wp.get("writing_style", ""),
            "special_requirements": wp.get("special_requirements", ""),
        }
        if root_label:
            lookup[root_label] = entry

        for child in root.get("children", []):
            child_label = child.get("labels", {}).get("zh-CN", "").strip()
            child_facets = child.get("facets", {})
            child_wt = child_facets.get("world_tone", "") or root_wt
            child_wp = child_facets.get("writing_profile", {})
            child_entry = {
                "world_tone": child_wt,
                "story_structure": child_wp.get("story_structure", "") or wp.get("story_structure", ""),
                "pacing_control": child_wp.get("pacing_control", "") or wp.get("pacing_control", ""),
                "writing_style": child_wp.get("writing_style", "") or wp.get("writing_style", ""),
                "special_requirements": child_wp.get("special_requirements", "") or wp.get("special_requirements", ""),
            }
            if child_label:
                lookup[child_label] = child_entry

    logger.info("lookup_genre: 已加载 %d 个类型模板", len(lookup))
    return lookup


async def lookup_genre_templates(genre_keyword: str) -> str:
    """搜索 builtin_cn_v1.yaml 中匹配的类型写作模板

    返回该类型的世界观基调和四个写作画像字段，
    作为 Agent 展开创意建议的参考框架。
    """
    lookup = _load_lookup()
    if not lookup:
        return "未找到类型模板数据，请基于通用的写作知识给出建议。"

    keyword = genre_keyword.strip()

    # 精确匹配
    if keyword in lookup:
        entry = lookup[keyword]
        return _format_entry(keyword, entry)

    # 模糊匹配：关键词包含在标签中，或标签包含关键词
    candidates = []
    for label in lookup:
        if keyword in label or label in keyword:
            candidates.append((len(label), label))

    if not candidates:
        return (
            f"未找到「{keyword}」的精确类型模板。"
            f"可用的类型包括：{', '.join(sorted(lookup.keys())[:20])}..."
        )

    # 取最长匹配（最具体）的标签
    candidates.sort(reverse=True)
    label = candidates[0][1]
    entry = lookup[label]
    return _format_entry(label, entry)


def _format_entry(label: str, entry: dict[str, str]) -> str:
    """格式化模板为文本"""
    lines = [f"【{label}】类型写作模板："]
    if entry.get("world_tone"):
        lines.append(f"世界观基调：{entry['world_tone']}")
    if entry.get("story_structure"):
        lines.append(f"剧情结构：{entry['story_structure']}")
    if entry.get("pacing_control"):
        lines.append(f"节奏把控：{entry['pacing_control']}")
    if entry.get("writing_style"):
        lines.append(f"写作风格：{entry['writing_style']}")
    if entry.get("special_requirements"):
        lines.append(f"特殊要求：{entry['special_requirements']}")
    return "\n".join(lines)
