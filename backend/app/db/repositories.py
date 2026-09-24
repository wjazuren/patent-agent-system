"""专利、知识库及检索评估的 PostgreSQL 仓储函数。"""
from __future__ import annotations

import json
from typing import Any, Sequence

from psycopg.rows import dict_row
from pgvector import Vector

from app.config import PGVECTOR_EF_SEARCH, VECTOR_DIMENSION
from app.db.postgres import get_connection, init_database, table_name


def _check_embeddings(embeddings: Sequence[Sequence[float]]) -> None:
    for embedding in embeddings:
        if len(embedding) != VECTOR_DIMENSION:
            raise ValueError(
                f"向量维度不匹配：期望 {VECTOR_DIMENSION}，实际 {len(embedding)}"
            )


def clear_patents() -> None:
    init_database()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table_name('patents')} RESTART IDENTITY CASCADE")


def upsert_patent_batch(records: Sequence[dict[str, Any]]) -> tuple[int, int]:
    """批量更新父专利与子 Chunk，返回（专利数，Chunk 数）。"""
    init_database()
    patents = table_name("patents")
    chunks_table = table_name("patent_chunks")
    patent_count = 0
    chunk_count = 0

    with get_connection() as conn, conn.cursor() as cur:
        for record in records:
            chunks = record.get("chunks", [])
            embeddings = record.get("embeddings", [])
            if len(chunks) != len(embeddings):
                raise ValueError("chunks 与 embeddings 数量不一致")
            _check_embeddings(embeddings)

            cur.execute(
                f"""
                INSERT INTO {patents}
                    (patent_number, title, applicant, ipc_classification,
                     application_date, publication_date, abstract,
                     technical_field, metadata, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW())
                ON CONFLICT (patent_number) DO UPDATE SET
                    title = EXCLUDED.title,
                    applicant = EXCLUDED.applicant,
                    ipc_classification = EXCLUDED.ipc_classification,
                    application_date = EXCLUDED.application_date,
                    publication_date = EXCLUDED.publication_date,
                    abstract = EXCLUDED.abstract,
                    technical_field = EXCLUDED.technical_field,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    record["patent_number"],
                    record.get("title", ""),
                    record.get("applicant", ""),
                    record.get("ipc_classification"),
                    record.get("application_date"),
                    record.get("publication_date"),
                    record["abstract"],
                    record.get("technical_field", ""),
                    json.dumps(record.get("metadata", {}), ensure_ascii=False),
                ),
            )
            patent_id = cur.fetchone()[0]
            cur.execute(f"DELETE FROM {chunks_table} WHERE patent_id = %s", (patent_id,))

            rows = []
            for index, (content, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{record['patent_number']}_chunk_{index}"
                rows.append(
                    (
                        chunk_id,
                        patent_id,
                        index,
                        content,
                        Vector(embedding),
                        json.dumps(record.get("chunk_metadata", {}), ensure_ascii=False),
                    )
                )
            if rows:
                cur.executemany(
                    f"""
                    INSERT INTO {chunks_table}
                        (id, patent_id, chunk_index, content, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    rows,
                )
            patent_count += 1
            chunk_count += len(rows)
    return patent_count, chunk_count


def search_patent_chunks(
    query_embedding: Sequence[float],
    limit: int,
    *,
    applicant: str | None = None,
    ipc_classification: str | None = None,
    publication_date_from: str | None = None,
    publication_date_to: str | None = None,
) -> list[dict[str, Any]]:
    """HNSW 余弦检索，支持业务元数据过滤。"""
    init_database()
    _check_embeddings([query_embedding])
    patents = table_name("patents")
    chunks = table_name("patent_chunks")
    conditions: list[str] = []
    params: list[Any] = []

    if applicant:
        conditions.append("p.applicant = %s")
        params.append(applicant)
    if ipc_classification:
        conditions.append("p.ipc_classification LIKE %s")
        params.append(f"{ipc_classification}%")
    if publication_date_from:
        conditions.append("p.publication_date >= %s")
        params.append(publication_date_from)
    if publication_date_to:
        conditions.append("p.publication_date <= %s")
        params.append(publication_date_to)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query_vector = Vector(query_embedding)
    query_params = [query_vector, *params, query_vector, limit]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('hnsw.ef_search', %s, true)",
                (str(PGVECTOR_EF_SEARCH),),
            )
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT c.id AS chunk_id, c.content AS chunk_content,
                       c.chunk_index, p.id AS patent_id, p.patent_number,
                       p.title, p.applicant, p.ipc_classification,
                       p.application_date, p.publication_date, p.abstract,
                       p.technical_field,
                       1 - (c.embedding <=> %s) AS vector_sim
                FROM {chunks} c
                JOIN {patents} p ON p.id = c.patent_id
                {where}
                ORDER BY c.embedding <=> %s
                LIMIT %s
                """,
                query_params,
            )
            return list(cur.fetchall())


def fetch_all_patents() -> list[dict[str, Any]]:
    init_database()
    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""SELECT id, patent_number, title, applicant, ipc_classification,
                       application_date, publication_date, abstract, technical_field
                FROM {table_name('patents')} ORDER BY patent_number"""
        )
        return list(cur.fetchall())


def fetch_patents_by_numbers(
    patent_numbers: Sequence[str],
    *,
    applicant: str | None = None,
    ipc_classification: str | None = None,
    publication_date_from: str | None = None,
    publication_date_to: str | None = None,
) -> dict[str, dict[str, Any]]:
    init_database()
    if not patent_numbers:
        return {}
    conditions = ["patent_number = ANY(%s)"]
    params: list[Any] = [list(patent_numbers)]
    if applicant:
        conditions.append("applicant = %s")
        params.append(applicant)
    if ipc_classification:
        conditions.append("ipc_classification LIKE %s")
        params.append(f"{ipc_classification}%")
    if publication_date_from:
        conditions.append("publication_date >= %s")
        params.append(publication_date_from)
    if publication_date_to:
        conditions.append("publication_date <= %s")
        params.append(publication_date_to)
    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""SELECT id, patent_number, title, applicant, ipc_classification,
                       application_date, publication_date, abstract, technical_field
                FROM {table_name('patents')}
                WHERE {' AND '.join(conditions)}""",
            params,
        )
        return {row["patent_number"]: dict(row) for row in cur.fetchall()}


def upsert_knowledge_documents(
    document_type: str,
    documents: Sequence[str],
    ids: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    metadatas: Sequence[dict[str, Any]] | None = None,
) -> int:
    if document_type not in {"template", "rule"}:
        raise ValueError("document_type 必须是 template 或 rule")
    if not (len(documents) == len(ids) == len(embeddings)):
        raise ValueError("documents、ids 与 embeddings 数量不一致")
    _check_embeddings(embeddings)
    init_database()
    metadatas = metadatas or [{} for _ in documents]
    rows = [
        (doc_id, document_type, content, Vector(embedding), json.dumps(metadata, ensure_ascii=False))
        for doc_id, content, embedding, metadata in zip(ids, documents, embeddings, metadatas)
    ]
    with get_connection() as conn, conn.cursor() as cur:
        cur.executemany(
            f"""
            INSERT INTO {table_name('knowledge_documents')}
                (id, document_type, content, embedding, metadata, updated_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, NOW())
            ON CONFLICT (id) DO UPDATE SET
                document_type = EXCLUDED.document_type,
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
            """,
            rows,
        )
    return len(rows)


def search_knowledge_documents(
    document_type: str, query_embedding: Sequence[float], limit: int
) -> list[str]:
    init_database()
    _check_embeddings([query_embedding])
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('hnsw.ef_search', %s, true)",
                (str(PGVECTOR_EF_SEARCH),),
            )
            cur.execute(
                f"""SELECT content
                    FROM {table_name('knowledge_documents')}
                    WHERE document_type = %s
                    ORDER BY embedding <=> %s
                    LIMIT %s""",
                (document_type, Vector(query_embedding), limit),
            )
            return [row[0] for row in cur.fetchall()]


def record_retrieval(
    query_text: str,
    results: Sequence[dict[str, Any]],
    *,
    filters: dict[str, Any] | None = None,
    latency_ms: int | None = None,
) -> int:
    """在同一数据库中保存一次检索及其排序结果，供后续评估追踪。"""
    init_database()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {table_name('retrieval_runs')}
                    (query_text, filters, latency_ms)
                VALUES (%s, %s::jsonb, %s) RETURNING id""",
            (query_text, json.dumps(filters or {}, ensure_ascii=False), latency_ms),
        )
        run_id = cur.fetchone()[0]
        rows = []
        for rank, item in enumerate(results, start=1):
            rows.append(
                (
                    run_id,
                    item.get("patent_id"),
                    rank,
                    item.get("vector_sim"),
                    item.get("bm25_score"),
                    item.get("rerank_score"),
                    json.dumps(item, ensure_ascii=False),
                )
            )
        if rows:
            cur.executemany(
                f"""INSERT INTO {table_name('retrieval_results')}
                        (retrieval_run_id, patent_id, rank, vector_score,
                         bm25_score, rerank_score, result_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)""",
                rows,
            )
        return run_id


def record_evaluation(
    metric_name: str,
    metric_value: float,
    *,
    retrieval_run_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> int:
    """保存一项离线或在线检索评估指标。"""
    init_database()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {table_name('evaluation_results')}
                    (retrieval_run_id, metric_name, metric_value, details)
                VALUES (%s, %s, %s, %s::jsonb) RETURNING id""",
            (
                retrieval_run_id,
                metric_name,
                metric_value,
                json.dumps(details or {}, ensure_ascii=False),
            ),
        )
        return cur.fetchone()[0]
