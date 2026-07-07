"""
SQLite 数据持久化服务
负责：
1. 保存生成的交底书文档
2. 查询历史文档
3. 文档列表分页

设计思路：
- 使用SQLite轻量数据库，无需额外部署
- 简单的CRUD操作，满足项目需求
- 与业务逻辑解耦，后续可平滑替换为MySQL等
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional, Tuple, List

from app.config import SQLITE_DB_PATH
from app.models.schemas import PatentState

logger = logging.getLogger(__name__)

_db_initialized = False


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接，首次调用时初始化表结构"""
    global _db_initialized

    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row

    if not _db_initialized:
        _init_tables(conn)
        _db_initialized = True

    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """初始化数据库表结构"""
    cursor = conn.cursor()

    # 文档表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patent_documents (
            document_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            user_id TEXT,
            title TEXT NOT NULL,
            abstract TEXT,
            content TEXT NOT NULL,
            risk_level TEXT DEFAULT 'low',
            iteration_count INTEGER DEFAULT 0,
            token_usage TEXT,
            state_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_id ON patent_documents(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_at ON patent_documents(created_at)
    """)

    conn.commit()
    logger.info("数据库表初始化完成")


def save_document(state: PatentState, user_id: Optional[str] = None) -> bool:
    """
    保存生成的文档到数据库

    Args:
        state: 完整的状态对象
        user_id: 用户ID

    Returns:
        是否保存成功
    """
    if state.final_document is None:
        return False

    doc = state.final_document

    try:
        conn = _get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO patent_documents
            (document_id, request_id, user_id, title, abstract, content,
             risk_level, iteration_count, token_usage, state_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc.document_id,
                state.request_id,
                user_id,
                doc.full_markdown.split('\n')[0].replace('# ', '').strip(),
                doc.abstract,
                doc.full_markdown,
                doc.final_risk_level,
                doc.iteration_count,
                json.dumps(state.token_usage.model_dump(), ensure_ascii=False),
                json.dumps(state.model_dump(mode="json"), ensure_ascii=False),
            ),
        )

        conn.commit()
        conn.close()
        logger.info("文档保存成功: %s", doc.document_id)
        return True

    except Exception as exc:
        logger.error("文档保存失败: %s", exc)
        return False


def get_document(document_id: str) -> Optional[dict]:
    """根据文档ID获取详情"""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM patent_documents WHERE document_id = ?",
            (document_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return dict(row)

    except Exception as exc:
        logger.error("查询文档失败: %s", exc)
        return None


def list_documents(
    user_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[int, List[dict]]:
    """
    获取文档列表

    Returns:
        (总数, 文档列表)
    """
    try:
        conn = _get_conn()
        cursor = conn.cursor()

        # 统计总数
        if user_id:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM patent_documents WHERE user_id = ?",
                (user_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM patent_documents")

        total = cursor.fetchone()["cnt"]

        # 查询分页数据
        query = """
            SELECT document_id, title, abstract, risk_level, iteration_count, created_at
            FROM patent_documents
        """
        params = []
        if user_id:
            query += " WHERE user_id = ?"
            params.append(user_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        items = [dict(row) for row in rows]
        return total, items

    except Exception as exc:
        logger.error("查询文档列表失败: %s", exc)
        return 0, []


def get_total_count() -> int:
    """获取总文档数"""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM patent_documents")
        total = cursor.fetchone()["cnt"]
        conn.close()
        return total
    except Exception as exc:
        logger.error("统计失败: %s", exc)
        return 0

def get_stats_summary() -> dict:
    """
    获取系统统计汇总数据（全部真实计算）
    返回：总文档数、各阶段Token消耗、今日生成数、风险分布、近7日趋势
    """
    try:
        conn = _get_conn()
        cursor = conn.cursor()

        # 1. 总文档数
        cursor.execute("SELECT COUNT(*) as cnt FROM patent_documents")
        total_documents = cursor.fetchone()["cnt"]

        # 2. 今日生成数
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM patent_documents
            WHERE DATE(created_at) = DATE('now', 'localtime')
        """)
        today_count = cursor.fetchone()["cnt"]

        # 3. 风险等级分布
        cursor.execute("""
            SELECT risk_level, COUNT(*) as cnt
            FROM patent_documents
            GROUP BY risk_level
        """)
        risk_rows = cursor.fetchall()
        risk_distribution = {"low": 0, "medium": 0, "high": 0}
        for row in risk_rows:
            level = row["risk_level"]
            if level in risk_distribution:
                risk_distribution[level] = row["cnt"]

        # 4. 分阶段 Token 消耗统计（从JSON字段精确累加）
        cursor.execute("SELECT token_usage FROM patent_documents WHERE token_usage IS NOT NULL")
        token_rows = cursor.fetchall()

        # 初始化各阶段统计项
        token_detail = {
            "total_tokens": 0,
            "requirement_tokens": 0,
            "search_tokens": 0,
            "writer_tokens": 0,
            "compliance_tokens": 0,
            "review_tokens": 0,
            "avg_iterations": 0.0
        }

        total_iterations = 0
        valid_doc_count = 0

        for row in token_rows:
            try:
                usage = json.loads(row["token_usage"])
                # 每个阶段 = prompt + completion
                req = (usage.get("requirement_prompt") or 0) + (usage.get("requirement_completion") or 0)
                sea = (usage.get("search_prompt") or 0) + (usage.get("search_completion") or 0)
                wri = (usage.get("writer_prompt") or 0) + (usage.get("writer_completion") or 0)
                com = (usage.get("compliance_prompt") or 0) + (usage.get("compliance_completion") or 0)
                rev = (usage.get("review_prompt") or 0) + (usage.get("review_completion") or 0)

                token_detail["requirement_tokens"] += req
                token_detail["search_tokens"] += sea
                token_detail["writer_tokens"] += wri
                token_detail["compliance_tokens"] += com
                token_detail["review_tokens"] += rev
                token_detail["total_tokens"] += req + sea + wri + com + rev
                valid_doc_count += 1
            except (json.JSONDecodeError, TypeError):
                continue

        # 5. 平均迭代轮次
        cursor.execute("SELECT AVG(iteration_count) as avg_iter FROM patent_documents")
        avg_iter_row = cursor.fetchone()
        token_detail["avg_iterations"] = round(float(avg_iter_row["avg_iter"] or 0), 1)

        # 6. 近7日生成趋势
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as cnt
            FROM patent_documents
            WHERE created_at >= DATE('now', '-6 days', 'localtime')
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """)
        trend_rows = cursor.fetchall()
        trend_map = {row["date"]: row["cnt"] for row in trend_rows}

        from datetime import datetime, timedelta
        trend_dates = []
        trend_values = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            trend_dates.append(d)
            trend_values.append(trend_map.get(d, 0))

        conn.close()

        return {
            "total_documents": total_documents,
            "total_tokens": token_detail["total_tokens"],
            "today_count": today_count,
            "risk_distribution": risk_distribution,
            "trend_dates": trend_dates,
            "trend_values": trend_values,
            # 各阶段真实 Token 消耗
            "requirement_tokens": token_detail["requirement_tokens"],
            "search_tokens": token_detail["search_tokens"],
            "writer_tokens": token_detail["writer_tokens"],
            "compliance_tokens": token_detail["compliance_tokens"],
            "review_tokens": token_detail["review_tokens"],
            # 真实平均迭代轮次
            "avg_iterations": token_detail["avg_iterations"]
        }
    except Exception as exc:
        logger.error("统计数据查询失败: %s", exc)
        return {
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
            "avg_iterations": 0.0
        }