"""基于 PostgreSQL + pgvector 的 RAG 混合检索工具。"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Tuple

import jieba
import scipy.special
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from app.config import EMBEDDING_MODEL_PATH
from app.db.repositories import (
    fetch_all_patents,
    fetch_patents_by_numbers,
    record_retrieval,
    search_knowledge_documents,
    search_patent_chunks,
)

logger = logging.getLogger(__name__)

VECTOR_WEIGHT = 0.6
BM25_WEIGHT = 0.4
RAW_TOP_K = 50
FINAL_TOP_K = 5
ENABLE_RERANK = True
RRF_K = 60

GLOBAL_BGE_M3_EMBED = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL_PATH,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

_bm25_model: BM25Okapi | None = None
_bm25_corpus: List[str] = []
_bm25_doc_ids: List[str] = []
_reranker: CrossEncoder | None = None

PATENT_STOPWORDS = {
    "本发明", "所述", "进一步", "其特征在于", "一种", "包括", "包含", "的", "地", "得"
}


def embed_documents(documents: List[str]) -> List[List[float]]:
    """统一生成入库向量，保证与查询侧使用同一模型和归一化策略。"""
    return GLOBAL_BGE_M3_EMBED.embed_documents(documents)


def embed_query(query: str) -> List[float]:
    return GLOBAL_BGE_M3_EMBED.embed_query(query)


def _jieba_tokenize(text: str) -> List[str]:
    return [
        word.strip()
        for word in jieba.lcut(text)
        if word.strip() and word.strip() not in PATENT_STOPWORDS
    ]


def get_reranker() -> CrossEncoder | None:
    global _reranker
    if _reranker is not None:
        return _reranker
    try:
        _reranker = CrossEncoder("BAAI/bge-reranker-base")
        logger.info("BAAI/bge-reranker-base 权重加载成功")
        return _reranker
    except Exception as exc:
        logger.warning("Reranker 加载失败，将跳过精排：%s", exc)
        return None


def weighted_rrf_merge(
    vec_candidates: Dict[str, dict],
    bm25_candidates: Dict[str, dict],
    vec_rank_list: List[str],
    bm25_rank_list: List[str],
    k: int = RRF_K,
    vec_w: float = VECTOR_WEIGHT,
    bm25_w: float = BM25_WEIGHT,
) -> List[dict]:
    """通过加权 Reciprocal Rank Fusion 融合两路独立召回。"""
    score_map: dict[str, float] = {}
    pool: dict[str, dict] = {}
    for rank, doc_id in enumerate(vec_rank_list, start=1):
        score_map[doc_id] = score_map.get(doc_id, 0.0) + vec_w / (rank + k)
        pool[doc_id] = vec_candidates[doc_id]
    for rank, doc_id in enumerate(bm25_rank_list, start=1):
        score_map[doc_id] = score_map.get(doc_id, 0.0) + bm25_w / (rank + k)
        pool.setdefault(doc_id, bm25_candidates[doc_id])
        if "bm25_score" in bm25_candidates[doc_id]:
            pool[doc_id]["bm25_score"] = bm25_candidates[doc_id]["bm25_score"]
    return [
        pool[doc_id]
        for doc_id in sorted(pool, key=lambda item: score_map[item], reverse=True)
    ]


def init_bm25_patent_corpus(*, force: bool = False) -> None:
    """从 PostgreSQL 父专利表构建进程内 BM25 索引。"""
    global _bm25_model, _bm25_corpus, _bm25_doc_ids
    if _bm25_model is not None and not force:
        return
    try:
        patents = fetch_all_patents()
    except Exception as exc:
        logger.warning("读取 PostgreSQL 专利数据失败，BM25 无法初始化：%s", exc)
        return
    if not patents:
        logger.warning("PostgreSQL 中没有专利数据，BM25 初始化终止")
        return
    _bm25_corpus = [item["abstract"] for item in patents]
    _bm25_doc_ids = [item["patent_number"] for item in patents]
    _bm25_model = BM25Okapi([_jieba_tokenize(text) for text in _bm25_corpus])
    logger.info("BM25 全局索引初始化完成，共加载 %d 篇专利", len(patents))


def get_bm25_scores(query: str) -> Dict[str, float]:
    global _bm25_model
    if _bm25_model is None:
        init_bm25_patent_corpus()
    if _bm25_model is None:
        return {}
    tokens = _jieba_tokenize(query)
    if not tokens:
        return {}
    raw_scores = _bm25_model.get_scores(tokens)
    max_score = max(raw_scores) if len(raw_scores) else 0.0
    if max_score <= 0:
        return {}
    return {
        _bm25_doc_ids[index]: float(score / max_score)
        for index, score in enumerate(raw_scores)
        if score > 0
    }


def _patent_item(row: dict[str, Any], vector_sim: float = 0.0) -> dict[str, Any]:
    return {
        "patent_id": row.get("patent_id", row.get("id")),
        "doc_id": row["patent_number"],
        "title": row.get("title", ""),
        "patent_number": row["patent_number"],
        "applicant": row.get("applicant", ""),
        "ipc_classification": row.get("ipc_classification"),
        "application_date": row.get("application_date", ""),
        "publication_date": row.get("publication_date"),
        "abstract": row.get("abstract", ""),
        "technical_field": row.get("technical_field", ""),
        "vector_sim": float(vector_sim),
    }


def search_prior_art_hybrid(
    query: str,
    top_k_raw: int = RAW_TOP_K,
    final_top_k: int = FINAL_TOP_K,
    *,
    applicant: str | None = None,
    ipc_classification: str | None = None,
    publication_date_from: str | None = None,
    publication_date_to: str | None = None,
) -> Tuple[List[dict], dict]:
    """父子 Chunk 向量召回 + 父专利 BM25 + RRF + CrossEncoder 精排。"""
    started = time.perf_counter()
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    filters = {
        key: value
        for key, value in {
            "applicant": applicant,
            "ipc_classification": ipc_classification,
            "publication_date_from": publication_date_from,
            "publication_date_to": publication_date_to,
        }.items()
        if value is not None
    }
    try:
        vector_rows = search_patent_chunks(
            embed_query(query),
            top_k_raw * 2,
            applicant=applicant,
            ipc_classification=ipc_classification,
            publication_date_from=publication_date_from,
            publication_date_to=publication_date_to,
        )
    except Exception as exc:
        logger.error("pgvector 专利检索失败：%s", exc)
        return [], empty_usage

    vec_candidates: Dict[str, dict] = {}
    vec_rank_list: List[str] = []
    for row in vector_rows:
        parent_id = row["patent_number"]
        if parent_id in vec_candidates:
            continue
        vec_candidates[parent_id] = _patent_item(row, row["vector_sim"])
        vec_rank_list.append(parent_id)
        if len(vec_rank_list) >= top_k_raw:
            break

    bm25_pairs = sorted(
        get_bm25_scores(query).items(), key=lambda item: item[1], reverse=True
    )[:top_k_raw]
    try:
        candidate_rows = fetch_patents_by_numbers(
            [doc_id for doc_id, _ in bm25_pairs],
            applicant=applicant,
            ipc_classification=ipc_classification,
            publication_date_from=publication_date_from,
            publication_date_to=publication_date_to,
        )
    except Exception as exc:
        logger.warning("补充 BM25 元数据失败：%s", exc)
        candidate_rows = {}
    if filters:
        allowed_ids = set(candidate_rows)
        bm25_pairs = [pair for pair in bm25_pairs if pair[0] in allowed_ids]

    bm25_candidates: Dict[str, dict] = {}
    bm25_rank_list: List[str] = []
    for doc_id, score in bm25_pairs:
        if doc_id in vec_candidates:
            item = vec_candidates[doc_id].copy()
        elif doc_id in candidate_rows:
            item = _patent_item(candidate_rows[doc_id])
        else:
            continue
        item["bm25_score"] = score
        bm25_candidates[doc_id] = item
        bm25_rank_list.append(doc_id)

    fused = weighted_rrf_merge(
        vec_candidates, bm25_candidates, vec_rank_list, bm25_rank_list
    )
    reranker = get_reranker() if ENABLE_RERANK and fused else None
    if reranker is not None:
        scores = scipy.special.expit(
            reranker.predict([(query, item["abstract"]) for item in fused])
        )
        for item, score in zip(fused, scores):
            item["rerank_score"] = float(score)
        fused.sort(key=lambda item: item["rerank_score"], reverse=True)

    selected = fused[:final_top_k]
    final_list = [
        {
            "patent_number": item["patent_number"],
            "title": item["title"],
            "applicant": item["applicant"],
            "ipc_classification": item.get("ipc_classification"),
            "application_date": item["application_date"],
            "publication_date": item.get("publication_date"),
            "abstract": item["abstract"],
            "similarity": round(
                item.get("rerank_score", item.get("vector_sim", 0.0)) * 100, 1
            ),
            "technical_field": item.get("technical_field", ""),
        }
        for item in selected
    ]
    try:
        record_retrieval(
            query,
            selected,
            filters=filters,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:
        logger.warning("检索结果记录失败，但不影响本次返回：%s", exc)

    logger.info(
        "混合检索完成：向量父级 %d，BM25 %d，融合 %d，输出 %d",
        len(vec_rank_list), len(bm25_rank_list), len(fused), len(final_list),
    )
    return final_list, empty_usage


def search_prior_art(query: str, top_k: int = 5) -> Tuple[List[dict], dict]:
    """兼容上层 Agent 的原有接口。"""
    return search_prior_art_hybrid(query, final_top_k=top_k)


def search_templates(query: str, top_k: int = 3) -> List[str]:
    try:
        return search_knowledge_documents("template", embed_query(query), top_k)
    except Exception as exc:
        logger.error("模板检索失败：%s", exc)
        return []


def search_rules(query: str, top_k: int = 5) -> List[str]:
    try:
        return search_knowledge_documents("rule", embed_query(query), top_k)
    except Exception as exc:
        logger.error("规范检索失败：%s", exc)
        return []
