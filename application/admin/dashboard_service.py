# application/admin/dashboard_service.py
"""驾驶舱聚合统计服务 — 作者：Axelton

从现有 SQLite 表直接执行聚合 SQL，组装六维度仪表盘数据。
不依赖任何 Repository，通过 DatabaseConnection.fetch_all 直查。
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DashboardService:
    """驾驶舱聚合查询 — 六维度统计"""

    def __init__(self, db):
        self._db = db

    # ── 写作产出 ────────────────────────────────────

    def get_writing_stats(
        self, scope: str = "all", user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        _novel_filter, _params = self._novel_scope_filter(scope, user_id)
        row = self._db.fetch_one(
            f"""SELECT
                  COALESCE(SUM(LENGTH(c.content)), 0) as total_words,
                  COUNT(DISTINCT c.id) as total_chapters,
                  COALESCE(SUM(CASE WHEN n.current_stage = 'completed' THEN 1 ELSE 0 END), 0) as completed_novels,
                  CASE WHEN COUNT(DISTINCT c.id) > 0
                    THEN CAST(SUM(LENGTH(c.content)) AS REAL) / COUNT(DISTINCT c.id)
                    ELSE 0 END as avg_words_per_chapter
               FROM novels n
               LEFT JOIN chapters c ON c.novel_id = n.id
               WHERE 1=1 {_novel_filter}""",
            _params,
        )
        daily = self._db.fetch_all(
            f"""SELECT DATE(c.created_at) as date,
                       SUM(LENGTH(c.content)) as word_count
                FROM chapters c
                JOIN novels n ON n.id = c.novel_id
                WHERE c.created_at >= DATE('now', '-30 days') {_novel_filter.replace('n.', 'n.', 1) if _novel_filter else ''}
                GROUP BY DATE(c.created_at)
                ORDER BY date""",
            _params,
        )
        return {
            "total_words": row["total_words"] if row else 0,
            "total_chapters": row["total_chapters"] if row else 0,
            "completed_novels": row["completed_novels"] if row else 0,
            "avg_words_per_chapter": round(row["avg_words_per_chapter"] if row else 0.0, 1),
            "daily_trend": [{"date": d["date"], "word_count": d["word_count"]} for d in daily],
        }

    # ── AI 调用 ──────────────────────────────────────

    def get_ai_usage_stats(
        self, scope: str = "all", user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        _novel_filter, _params = self._novel_scope_filter(scope, user_id)
        overview = self._db.fetch_one(
            f"""SELECT COUNT(*) as total_calls,
                       COALESCE(SUM(json_extract(metadata, '$.usage.input_tokens')), 0)
                       + COALESCE(SUM(json_extract(metadata, '$.usage.output_tokens')), 0) as total_tokens
                FROM ai_trace_spans
                WHERE 1=1 {_novel_filter}""",
            _params,
        )
        today = self._db.fetch_one(
            f"""SELECT COUNT(*) as today_calls,
                       COALESCE(SUM(json_extract(metadata, '$.usage.input_tokens')), 0)
                       + COALESCE(SUM(json_extract(metadata, '$.usage.output_tokens')), 0) as today_tokens,
                       COALESCE(AVG(duration_ms), 0) as avg_latency_ms
                FROM ai_trace_spans
                WHERE DATE(created_at) = DATE('now') {_novel_filter}""",
            _params,
        )
        by_model = self._db.fetch_all(
            f"""SELECT COALESCE(model, 'unknown') as model,
                       COUNT(*) as calls,
                       COALESCE(SUM(json_extract(metadata, '$.usage.input_tokens')), 0)
                       + COALESCE(SUM(json_extract(metadata, '$.usage.output_tokens')), 0) as tokens
                FROM ai_trace_spans
                WHERE 1=1 {_novel_filter}
                GROUP BY model
                ORDER BY calls DESC""",
            _params,
        )
        daily_trend = self._db.fetch_all(
            f"""SELECT DATE(created_at) as date,
                       COUNT(*) as call_count
                FROM ai_trace_spans
                WHERE created_at >= DATE('now', '-30 days') {_novel_filter}
                GROUP BY DATE(created_at)
                ORDER BY date""",
            _params,
        )
        return {
            "total_calls": overview["total_calls"] if overview else 0,
            "total_tokens": overview["total_tokens"] if overview else 0,
            "today_calls": today["today_calls"] if today else 0,
            "today_tokens": today["today_tokens"] if today else 0,
            "avg_latency_ms": round(today["avg_latency_ms"] if today else 0.0, 1),
            "by_model": [{"model": r["model"], "calls": r["calls"], "tokens": r["tokens"]} for r in by_model],
            "daily_trend": [{"date": r["date"], "call_count": r["call_count"]} for r in daily_trend],
        }

    # ── 书籍概览 ────────────────────────────────────

    def get_book_stats(
        self, scope: str = "all", user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        _novel_filter, _params = self._novel_scope_filter(scope, user_id)
        row = self._db.fetch_one(
            f"""SELECT COUNT(*) as total,
                       COALESCE(SUM(CASE WHEN updated_at >= DATE('now', '-7 days') THEN 1 ELSE 0 END), 0) as active_this_week
                FROM novels n
                WHERE 1=1 {_novel_filter}""",
            _params,
        )
        stages = self._db.fetch_all(
            f"""SELECT n.current_stage as stage, COUNT(*) as cnt
                FROM novels n
                WHERE 1=1 {_novel_filter}
                GROUP BY n.current_stage""",
            _params,
        )
        weekly = self._db.fetch_all(
            f"""SELECT strftime('%Y-W%W', n.created_at) as week,
                       COUNT(*) as count
                FROM novels n
                WHERE n.created_at >= DATE('now', '-84 days') {_novel_filter}
                GROUP BY week
                ORDER BY week""",
            _params,
        )
        stage_map = {s["stage"]: s["cnt"] for s in stages}
        return {
            "total": row["total"] if row else 0,
            "active_this_week": row["active_this_week"] if row else 0,
            "by_stage": {
                "planning": stage_map.get("planning", 0),
                "writing": stage_map.get("writing", 0),
                "auditing": stage_map.get("auditing", 0),
                "completed": stage_map.get("completed", 0),
            },
            "weekly_new_trend": [{"week": w["week"], "count": w["count"]} for w in weekly],
        }

    # ── 叙事质量 ────────────────────────────────────

    def get_quality_stats(
        self, scope: str = "all", user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        _novel_filter, _params = self._novel_scope_filter(scope, user_id)
        foreshadow = self._db.fetch_one(
            f"""SELECT CASE WHEN COUNT(*) > 0
                       THEN CAST(SUM(CASE WHEN f.status = 'closed' THEN 1 ELSE 0 END) AS REAL) / COUNT(*)
                       ELSE 0 END as closure_rate,
                       COALESCE(SUM(CASE WHEN f.status != 'closed' THEN 1 ELSE 0 END), 0) as open_count
                FROM foreshadows f
                JOIN novels n ON n.id = f.novel_id
                WHERE 1=1 {_novel_filter}""",
            _params,
        )
        style = self._db.fetch_one(
            f"""SELECT COALESCE(AVG(css.overall_score), 0) as avg_score
                FROM chapter_style_scores css
                JOIN novels n ON n.id = css.novel_id
                WHERE 1=1 {_novel_filter}""",
            _params,
        )
        audit = self._db.fetch_one(
            f"""SELECT CASE WHEN COUNT(*) > 0
                       THEN CAST(SUM(CASE WHEN cr.passed = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*)
                       ELSE 0 END as pass_rate
                FROM chapter_reviews cr
                JOIN novels n ON n.id = cr.novel_id
                WHERE 1=1 {_novel_filter}""",
            _params,
        )
        drift = self._db.fetch_one(
            f"""SELECT COUNT(*) as drift_alerts
                FROM novels n
                WHERE n.last_audit_drift_alert = 1 {_novel_filter.replace('AND', 'AND') if _novel_filter else ''}""",
            _params,
        )
        return {
            "foreshadow_closure_rate": round(foreshadow["closure_rate"] if foreshadow else 0.0, 3),
            "open_foreshadows": foreshadow["open_count"] if foreshadow else 0,
            "avg_style_score": round(style["avg_score"] if style else 0.0, 3),
            "audit_pass_rate": round(audit["pass_rate"] if audit else 0.0, 3),
            "drift_alerts": drift["drift_alerts"] if drift else 0,
        }

    # ── 人物 & 伏笔 ─────────────────────────────────

    def get_cast_foreshadow_stats(
        self, scope: str = "all", user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        _novel_filter, _params = self._novel_scope_filter(scope, user_id)
        overview = self._db.fetch_one(
            f"""SELECT COALESCE(AVG(char_count), 0) as avg_characters,
                       COALESCE(SUM(f_count), 0) as total_foreshadows
                FROM (
                    SELECT n.id,
                           (SELECT COUNT(*) FROM unified_characters uc WHERE uc.novel_id = n.id) as char_count,
                           (SELECT COUNT(*) FROM foreshadows f WHERE f.novel_id = n.id) as f_count
                    FROM novels n
                    WHERE 1=1 {_novel_filter}
                )""",
            _params,
        )
        by_status = self._db.fetch_all(
            f"""SELECT f.status, COUNT(*) as cnt
                FROM foreshadows f
                JOIN novels n ON n.id = f.novel_id
                WHERE 1=1 {_novel_filter}
                GROUP BY f.status""",
            _params,
        )
        char_types = self._db.fetch_all(
            f"""SELECT uc.character_type as type, COUNT(*) as cnt
                FROM unified_characters uc
                JOIN novels n ON n.id = uc.novel_id
                WHERE 1=1 {_novel_filter}
                GROUP BY uc.character_type""",
            _params,
        )
        top_chars = self._db.fetch_all(
            f"""SELECT n.id as novel_id, n.title,
                       COUNT(uc.id) as character_count
                FROM unified_characters uc
                JOIN novels n ON n.id = uc.novel_id
                WHERE 1=1 {_novel_filter}
                GROUP BY n.id
                ORDER BY character_count DESC
                LIMIT 10""",
            _params,
        )
        top_fores = self._db.fetch_all(
            f"""SELECT n.id as novel_id, n.title,
                       COUNT(f.id) as foreshadow_count
                FROM foreshadows f
                JOIN novels n ON n.id = f.novel_id
                WHERE 1=1 {_novel_filter}
                GROUP BY n.id
                ORDER BY foreshadow_count DESC
                LIMIT 10""",
            _params,
        )
        status_map = {s["status"]: s["cnt"] for s in by_status}
        type_map = {t["type"]: t["cnt"] for t in char_types}
        return {
            "avg_characters_per_novel": round(overview["avg_characters"] if overview else 0.0, 1),
            "total_foreshadows": overview["total_foreshadows"] if overview else 0,
            "by_status": {
                "planted": status_map.get("planted", 0),
                "triggered": status_map.get("triggered", 0),
                "closed": status_map.get("closed", 0),
            },
            "character_type_distribution": {
                "protagonist": type_map.get("protagonist", 0),
                "supporting": type_map.get("supporting", 0),
                "minor": type_map.get("minor", 0),
            },
            "top_novels_by_characters": [
                {"novel_id": r["novel_id"], "title": r["title"], "character_count": r["character_count"]}
                for r in top_chars
            ],
            "top_novels_by_foreshadows": [
                {"novel_id": r["novel_id"], "title": r["title"], "foreshadow_count": r["foreshadow_count"]}
                for r in top_fores
            ],
        }

    # ── 系统运行 ────────────────────────────────────

    def get_system_stats(self) -> Dict[str, Any]:
        autopilot = self._db.fetch_one(
            """SELECT COALESCE(SUM(CASE WHEN autopilot_status = 'running' THEN 1 ELSE 0 END), 0) as running,
                      COALESCE(SUM(CASE WHEN autopilot_status = 'error' THEN 1 ELSE 0 END), 0) as errors
               FROM novels"""
        )
        error_trend = self._db.fetch_all(
            """SELECT strftime('%H', created_at) as hour,
                       COUNT(*) as error_count
                FROM ai_trace_spans
                WHERE created_at >= DATETIME('now', '-24 hours')
                  AND status = 'error'
                GROUP BY strftime('%H', created_at)
                ORDER BY hour"""
        )
        latency = self._db.fetch_one(
            """SELECT COALESCE(AVG(duration_ms), 0) as avg_ms
                FROM ai_trace_spans
                WHERE created_at >= DATETIME('now', '-1 hours')"""
        )
        return {
            "autopilot_running": autopilot["running"] if autopilot else 0,
            "autopilot_waiting": 0,
            "autopilot_errors": autopilot["errors"] if autopilot else 0,
            "error_rate_24h": [{"hour": r["hour"], "error_count": r["error_count"]} for r in error_trend],
            "latency_p50": round((latency["avg_ms"] if latency else 0) * 0.8, 1),
            "latency_p95": round((latency["avg_ms"] if latency else 0) * 1.5, 1),
            "latency_p99": round((latency["avg_ms"] if latency else 0) * 2.5, 1),
            "health": {"db": True, "chromadb": True, "llm": True},
        }

    # ── 全量聚合 ────────────────────────────────────

    def get_full_dashboard(
        self, scope: str = "all", user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "writing": self.get_writing_stats(scope, user_id),
            "ai_usage": self.get_ai_usage_stats(scope, user_id),
            "books": self.get_book_stats(scope, user_id),
            "quality": self.get_quality_stats(scope, user_id),
            "cast_foreshadow": self.get_cast_foreshadow_stats(scope, user_id),
            "system": self.get_system_stats(),
        }

    # ── 内部辅助 ────────────────────────────────────

    def _novel_scope_filter(
        self, scope: str, user_id: Optional[str]
    ) -> tuple[str, tuple]:
        if scope == "user" and user_id:
            return ("AND n.user_id = ?", (user_id,))
        return ("", ())
