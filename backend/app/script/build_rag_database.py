"""兼容入口：统一调用父子 Chunk 的 PostgreSQL/pgvector 建库脚本。"""
from app.script.build_parent_rag_data import main


if __name__ == "__main__":
    main()
