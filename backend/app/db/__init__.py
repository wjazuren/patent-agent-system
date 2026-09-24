"""PostgreSQL 数据访问层。"""

from app.db.postgres import get_connection, init_database

__all__ = ["get_connection", "init_database"]
