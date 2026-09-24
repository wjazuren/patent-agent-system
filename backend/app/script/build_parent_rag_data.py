"""将清洗后的 SQLite 专利数据导入 PostgreSQL/pgvector 父子索引。"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

BACKEND_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.db.postgres import init_database
from app.db.repositories import clear_patents, upsert_patent_batch
from app.tools.rag_tool import embed_documents, init_bm25_patent_corpus

DEFAULT_SOURCE = os.getenv("PATENT_SOURCE_SQLITE_PATH", "./data/patent_meta.db")
DEFAULT_BATCH_SIZE = int(os.getenv("PATENT_IMPORT_BATCH_SIZE", "500"))

child_splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=40,
    separators=["\n\n", "\n", "；", "。", "！", "？", " ", ""],
)


def iter_patent_batches(source: str, batch_size: int):
    conn = sqlite3.connect(source)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(patent_meta)")
        available_columns = {row[1] for row in cur.fetchall()}
        ipc_column = next(
            (name for name in ("ipc_classification", "ipc", "ipc_code") if name in available_columns),
            None,
        )
        publication_column = next(
            (name for name in ("publication_date", "published_date") if name in available_columns),
            None,
        )
        ipc_select = ipc_column or "NULL"
        publication_select = publication_column or "NULL"
        cur.execute(
            f"""SELECT patent_number, title, applicant, application_date,
                       abstract, technical_field, {ipc_select}, {publication_select}
                FROM patent_meta ORDER BY patent_number"""
        )
        while rows := cur.fetchmany(batch_size):
            yield rows
    finally:
        conn.close()


def import_patents(source: str, batch_size: int) -> tuple[int, int]:
    total_patents = 0
    total_chunks = 0
    for batch_number, rows in enumerate(iter_patent_batches(source, batch_size), start=1):
        records = []
        all_chunks: list[str] = []
        for (
            patent_number,
            title,
            applicant,
            application_date,
            abstract,
            technical_field,
            ipc_classification,
            publication_date,
        ) in rows:
            if not abstract or not abstract.strip():
                continue
            chunks = child_splitter.split_text(abstract)
            record = {
                "patent_number": patent_number,
                "title": title or "",
                "applicant": applicant or "",
                "application_date": application_date,
                "publication_date": publication_date,
                "ipc_classification": ipc_classification,
                "abstract": abstract,
                "technical_field": technical_field or "",
                "chunks": chunks,
            }
            records.append(record)
            all_chunks.extend(chunks)

        embeddings = embed_documents(all_chunks) if all_chunks else []
        offset = 0
        for record in records:
            size = len(record["chunks"])
            record["embeddings"] = embeddings[offset : offset + size]
            offset += size
        patent_count, chunk_count = upsert_patent_batch(records)
        total_patents += patent_count
        total_chunks += chunk_count
        print(
            f"第 {batch_number} 批完成：{patent_count} 篇专利，"
            f"{chunk_count} 个 Chunk；累计 {total_patents}/{total_chunks}"
        )

    init_bm25_patent_corpus(force=True)
    return total_patents, total_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="源 SQLite 文件")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--clear", action="store_true", help="导入前清空原有专利与 Chunk")
    args = parser.parse_args()

    init_database()
    if args.clear:
        clear_patents()
        print("已清空 PostgreSQL 中的旧专利数据")
    patents, chunks = import_patents(args.source, args.batch_size)
    print(f"导入完成：共 {patents} 篇专利、{chunks} 个向量 Chunk")


if __name__ == "__main__":
    main()
