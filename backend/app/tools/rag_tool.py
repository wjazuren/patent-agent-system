"""
RAG 检索工具
提供向量检索能力，支撑：
1. 现有技术专利语义检索
2. 专利模板检索
3. 审查规范检索

设计思路：
- 使用Chroma作为向量数据库，轻量易部署
- 统一的检索接口，不同集合通过参数区分
- 支持缓存，减少重复向量化计算
"""
from __future__ import annotations

import logging
from typing import List, Tuple, Any,Dict
from rank_bm25 import BM25Okapi
import jieba
from sentence_transformers import CrossEncoder

from app.config import (
    CHROMA_PATENT_COLLECTION,
    CHROMA_PERSIST_DIR,
    CHROMA_RULES_COLLECTION,
    CHROMA_TEMPLATE_COLLECTION,
)

logger = logging.getLogger(__name__)

# 全局单例
_chroma_client = None
_collections = {}
# 全局缓存
_bm25_model: BM25Okapi | None = None
_bm25_corpus: List[str] = []
_bm25_doc_ids: List[str] = []

# ================= 全局配置（混合权重、输出条数） =================
VECTOR_WEIGHT = 0.6
BM25_WEIGHT = 0.4
RAW_TOP_K = 50    # 粗召回候选数量
FINAL_TOP_K = 10   # 最终输出Top5（评测用）
# _reranker: CrossEncoder | None = None
_reranker: CrossEncoder | None = None
logger = logging.getLogger(__name__)

# ================= Reranker加载函数 =================
def get_reranker() -> CrossEncoder | None:
    global _reranker
    if _reranker is not None:
        return _reranker
    try:
        # 轻量中文交叉重排模型，可替换自研专利reranker
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        logger.info("Reranker交叉编码器加载成功")
        return _reranker
    except Exception as e:
        logger.warning(f"Reranker加载失败：{e}，跳过重排，直接返回混合粗召回")
        return None

# ================= 混合检索核心函数（你缺失的search_prior_art_hybrid） =================
def search_prior_art_hybrid(query: str, top_k_raw: int = RAW_TOP_K) -> Tuple[List[dict], dict]:
    """
    混合检索：Chroma向量相似度 + BM25关键词融合打分 + CrossEncoder精排
    返回格式完全适配eval_retrieval_metric评测脚本
    """
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    coll = _get_collection(CHROMA_PATENT_COLLECTION)
    if coll is None:
        logger.warning("Chroma向量库初始化失败，无检索结果")
        return [], empty_usage

    # Step1：向量检索，获取文档、id、距离
    vec_res = coll.query(query_texts=[query], n_results=top_k_raw)
    vec_ids = vec_res["ids"][0]
    vec_docs = vec_res["documents"][0]
    vec_metas = vec_res["metadatas"][0]
    vec_distances = vec_res["distances"][0]

    # 构造向量分数映射 距离→0~1相似度
    vec_score_map = {}
    raw_candidates = []
    for idx, doc_id in enumerate(vec_ids):
        dist = vec_distances[idx]
        sim = max(0.0, min(1.0, 1 - dist))
        vec_score_map[doc_id] = sim
        meta = vec_metas[idx] if idx < len(vec_metas) else {}
        raw_candidates.append({
            "doc_id": doc_id,
            "title": meta.get("title", ""),
            "patent_number": meta.get("patent_number", ""),
            "applicant": meta.get("applicant", ""),
            "application_date": meta.get("application_date", ""),
            "abstract": vec_docs[idx],
            "vector_sim": sim,
            "bm25_score": 0.0,
            "fusion_score": 0.0
        })

    # Step2：获取BM25归一化关键词分数
    bm25_score_map = get_bm25_scores(query)

    # Step3：加权融合总分 = 向量分*0.6 + BM25分*0.4
    for item in raw_candidates:
        bid = item["doc_id"]
        bm25_s = bm25_score_map.get(bid, 0.0)
        item["bm25_score"] = bm25_s
        item["fusion_score"] = item["vector_sim"] * VECTOR_WEIGHT + bm25_s * BM25_WEIGHT

    # 按融合分数降序粗排序
    raw_candidates.sort(key=lambda x: x["fusion_score"], reverse=True)

    # Step4：Reranker交叉语义重排
    # reranker = get_reranker()
    reranker = None
    if reranker is not None and len(raw_candidates) > 0:
        query_doc_pairs = [(query, item["abstract"]) for item in raw_candidates]
        rerank_scores = reranker.predict(query_doc_pairs)
        # 绑定重排分数
        for i, item in enumerate(raw_candidates):
            item["rerank_score"] = float(rerank_scores[i])
        # 按重排分数重新排序
        raw_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

    # Step5：截取最终Top5，转换对外统一输出格式（评测脚本专用）
    final_list = []
    for item in raw_candidates[:FINAL_TOP_K]:
        final_list.append({
            "patent_number": item["patent_number"],
            "title": item["title"],
            "applicant": item["applicant"],
            "application_date": item["application_date"],
            "abstract": item["abstract"],
            "similarity": round(item.get("rerank_score", item["fusion_score"]) * 100, 1),
            "technical_field": item.get("technical_field", "")
        })

    logger.info(f"混合检索完成，粗召回{len(raw_candidates)}条，最终输出Top{FINAL_TOP_K}")
    return final_list, empty_usage

# ================= 向下兼容原有search_prior_art接口 =================
def search_prior_art(query: str, top_k: int = 5) -> Tuple[List[dict], dict]:
    """旧接口兼容层，上层Agent无需修改"""
    return search_prior_art_hybrid(query)

def _jieba_tokenize(text: str) -> List[str]:
    """专利中文分词，去除无意义虚词"""
    stop_words = {"本发明","所述","进一步","其特征在于","一种","包括","包含"}
    raw_words = jieba.lcut(text)
    return [w for w in raw_words if w not in stop_words and len(w.strip())>1]

def init_bm25_patent_corpus():
    """
    从已入库Chroma专利库读取全部摘要，构建全局BM25检索索引
    调用时机：build_rag_database.py 全部专利入库完成后执行一次
    """
    global _bm25_model, _bm25_corpus, _bm25_doc_ids
    coll = _get_collection(CHROMA_PATENT_COLLECTION)
    if coll is None:
        logger.warning("Chroma向量库不存在，无法初始化BM25")
        return
    
    # 取出全部专利id+摘要文本
    # 默认返回ids+documents+metadatas
    all_data = coll.get()
    docs = all_data["documents"]
    doc_ids = all_data["ids"]
    if not docs or len(docs) == 0:
        logger.warning("Chroma内无专利数据，BM25初始化终止")
        return
    
    # 分词构建BM25语料
    tokenized_corpus = [_jieba_tokenize(doc) for doc in docs]
    _bm25_corpus = docs
    _bm25_doc_ids = doc_ids
    _bm25_model = BM25Okapi(tokenized_corpus)
    logger.info(f"BM25初始化完成，共加载{len(docs)}条专利摘要")

def get_bm25_scores(query: str) -> Dict[str, float]:
    """输入查询，返回标准化BM25分数 {专利号:0~1分值}"""
    if _bm25_model is None:
        return {}
    tokenized_query = _jieba_tokenize(query)
    raw_scores = _bm25_model.get_scores(tokenized_query)
    score_map = dict(zip(_bm25_doc_ids, raw_scores))
    
    # min-max归一化到0~1，方便和向量相似度加权融合
    values = list(score_map.values())
    if max(values) - min(values) < 1e-6:
        return {k:0.0 for k in score_map}
    return {k:(v-min(values))/(max(values)-min(values)) for k,v in score_map.items()}

def _get_chroma_client():
    """懒加载Chroma客户端"""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    try:
        import chromadb
        from chromadb.config import Settings
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        logger.info("Chroma向量库初始化成功，路径: %s", CHROMA_PERSIST_DIR)
        return _chroma_client
    except Exception as exc:
        logger.warning("Chroma初始化失败: %s", exc)
        return None


def _get_collection(collection_name: str):
    """获取或创建集合"""
    if collection_name in _collections:
        return _collections[collection_name]

    client = _get_chroma_client()
    if client is None:
        return None

    try:
        collection = client.get_or_create_collection(name=collection_name)
        _collections[collection_name] = collection
        return collection
    except Exception as exc:
        logger.warning("获取集合失败 %s: %s", collection_name, exc)
        return None


# def search_prior_art(query: str, top_k: int = 5) -> Tuple[List[dict], dict]:
#     """
#     检索现有技术专利
#     从专利向量库中查找与查询最相似的专利

#     Args:
#         query: 检索查询文本
#         top_k: 返回条数

#     Returns:
#         (专利数据列表, Token用量字典)
#     """
#     empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
#     collection = _get_collection(CHROMA_PATENT_COLLECTION)
#     if collection is None:
#         logger.warning("专利集合不可用，返回空结果")
#         return [], empty_usage

#     try:
#         results = collection.query(
#             query_texts=[query],
#             n_results=top_k,
#         )

#         patents = []
#         if results and results.get("documents"):
#             docs = results["documents"][0]
#             metadatas = results.get("metadatas", [[]])[0]
#             distances = results.get("distances", [[]])[0]

#             for i, doc in enumerate(docs):
#                 metadata = metadatas[i] if i < len(metadatas) else {}
#                 distance = distances[i] if i < len(distances) else 1.0
#                 # 距离转相似度（0-100），距离越小相似度越高
#                 similarity = max(0, min(100, (1 - distance) * 100))

#                 patents.append({
#                     "title": metadata.get("title", f"专利{i+1}"),
#                     "patent_number": metadata.get("patent_number", ""),
#                     "applicant": metadata.get("applicant", ""),
#                     "application_date": metadata.get("application_date", ""),
#                     "abstract": doc,
#                     "similarity": similarity,
#                     "technical_field": metadata.get("technical_field", ""),
#                 })

#         logger.info("现有技术检索完成，返回 %d 条结果", len(patents))
#         return patents, empty_usage

#     except Exception as exc:
#         logger.error("现有技术检索失败: %s", exc)
#         return [], empty_usage


def search_templates(query: str, top_k: int = 3) -> List[str]:
    """检索专利模板，返回模板文本列表"""
    collection = _get_collection(CHROMA_TEMPLATE_COLLECTION)
    if collection is None:
        return []

    try:
        results = collection.query(query_texts=[query], n_results=top_k)
        if results and results.get("documents"):
            return results["documents"][0]
        return []
    except Exception as exc:
        logger.error("模板检索失败: %s", exc)
        return []


def search_rules(query: str, top_k: int = 5) -> List[str]:
    """检索审查规范，返回规范条文列表"""
    collection = _get_collection(CHROMA_RULES_COLLECTION)
    if collection is None:
        return []

    try:
        results = collection.query(query_texts=[query], n_results=top_k)
        if results and results.get("documents"):
            return results["documents"][0]
        return []
    except Exception as exc:
        logger.error("规范检索失败: %s", exc)
        return []