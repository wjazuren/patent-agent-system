"""基于 PostgreSQL 的交底书业务数据持久化服务。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.db.postgres import get_connection, init_database, table_name
from app.models.schemas import PatentState

logger = logging.getLogger(__name__)
_db_initialized = False


def _ensure_database() -> None:
    global _db_initialized
    if not _db_initialized:
        init_database()
        _db_initialized = True


def save_document(state: PatentState, user_id: Optional[str] = None) -> bool:
    if state.final_document is None:
        return False
    doc = state.final_document
    try:
        _ensure_database()
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {table_name('patent_documents')}
                    (document_id, request_id, user_id, title, abstract, content,
                     risk_level, iteration_count, token_usage, state_data, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (document_id) DO UPDATE SET
                    request_id = EXCLUDED.request_id,
                    user_id = EXCLUDED.user_id,
                    title = EXCLUDED.title,
                    abstract = EXCLUDED.abstract,
                    content = EXCLUDED.content,
                    risk_level = EXCLUDED.risk_level,
                    iteration_count = EXCLUDED.iteration_count,
                    token_usage = EXCLUDED.token_usage,
                    state_data = EXCLUDED.state_data,
                    updated_at = NOW()
                """,
                (
                    doc.document_id,
                    state.request_id,
                    user_id,
                    doc.full_markdown.split("\n")[0].replace("# ", "").strip(),
                    doc.abstract,
                    doc.full_markdown,
                    doc.final_risk_level,
                    doc.iteration_count,
                    Jsonb(state.token_usage.model_dump()),
                    Jsonb(state.model_dump(mode="json")),
                ),
            )
        logger.info("文档保存成功: %s", doc.document_id)
        return True
    except Exception as exc:
        logger.error("文档保存失败: %s", exc)
        return False


def get_document(document_id: str) -> Optional[dict]:
    try:
        _ensure_database()
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"SELECT * FROM {table_name('patent_documents')} WHERE document_id = %s",
                (document_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as exc:
        logger.error("查询文档失败: %s", exc)
        return None


def list_documents(
    user_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[int, List[dict]]:
    try:
        _ensure_database()
        table = table_name("patent_documents")
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            if user_id:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM {table} WHERE user_id = %s", (user_id,))
                total = cur.fetchone()["cnt"]
                cur.execute(
                    f"""SELECT document_id, title, abstract, risk_level,
                               iteration_count, created_at
                        FROM {table} WHERE user_id = %s
                        ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                    (user_id, limit, offset),
                )
            else:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
                total = cur.fetchone()["cnt"]
                cur.execute(
                    f"""SELECT document_id, title, abstract, risk_level,
                               iteration_count, created_at
                        FROM {table} ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                    (limit, offset),
                )
            return total, [dict(row) for row in cur.fetchall()]
    except Exception as exc:
        logger.error("查询文档列表失败: %s", exc)
        return 0, []


def get_total_count() -> int:
    try:
        _ensure_database()
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name('patent_documents')}")
            return cur.fetchone()[0]
    except Exception as exc:
        logger.error("统计失败: %s", exc)
        return 0


def get_stats_summary() -> dict:
    empty = {
        "total_documents": 0,
        "total_tokens": 0,
        "today_count": 0,
        "risk_distribution": {"low": 0, "medium": 0, "high": 0},
        "trend_dates": [],
        "trend_values": [],
        "requirement_tokens": 0,
        "search_tokens": 0,
        "writer_tokens": 0,
        "compliance_tokens": 0,
        "review_tokens": 0,
        "avg_iterations": 0.0,
    }
    try:
        _ensure_database()
        table = table_name("patent_documents")
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
            empty["total_documents"] = cur.fetchone()["cnt"]
            cur.execute(f"SELECT COUNT(*) AS cnt FROM {table} WHERE created_at::date = CURRENT_DATE")
            empty["today_count"] = cur.fetchone()["cnt"]
            cur.execute(f"SELECT risk_level, COUNT(*) AS cnt FROM {table} GROUP BY risk_level")
            for row in cur.fetchall():
                if row["risk_level"] in empty["risk_distribution"]:
                    empty["risk_distribution"][row["risk_level"]] = row["cnt"]
            cur.execute(f"SELECT token_usage, iteration_count FROM {table}")
            rows = cur.fetchall()
            stage_fields = {
                "requirement_tokens": ("requirement_prompt", "requirement_completion"),
                "search_tokens": ("search_prompt", "search_completion"),
                "writer_tokens": ("writer_prompt", "writer_completion"),
                "compliance_tokens": ("compliance_prompt", "compliance_completion"),
                "review_tokens": ("review_prompt", "review_completion"),
            }
            for row in rows:
                usage = row["token_usage"] or {}
                for output_key, (prompt_key, completion_key) in stage_fields.items():
                    empty[output_key] += (usage.get(prompt_key) or 0) + (usage.get(completion_key) or 0)
            empty["total_tokens"] = sum(empty[key] for key in stage_fields)
            if rows:
                empty["avg_iterations"] = round(
                    sum(row["iteration_count"] for row in rows) / len(rows), 1
                )
            cur.execute(
                f"""SELECT created_at::date AS date, COUNT(*) AS cnt
                    FROM {table}
                    WHERE created_at >= CURRENT_DATE - INTERVAL '6 days'
                    GROUP BY created_at::date ORDER BY date"""
            )
            trend_map = {str(row["date"]): row["cnt"] for row in cur.fetchall()}
            for days_ago in range(6, -1, -1):
                date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                empty["trend_dates"].append(date)
                empty["trend_values"].append(trend_map.get(date, 0))
        return empty
    except Exception as exc:
        logger.error("统计数据查询失败: %s", exc)
        return empty
