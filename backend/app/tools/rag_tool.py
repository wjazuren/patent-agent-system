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
from typing import List, Tuple, Any

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


def search_prior_art(query: str, top_k: int = 5) -> Tuple[List[dict], dict]:
    """
    检索现有技术专利
    从专利向量库中查找与查询最相似的专利

    Args:
        query: 检索查询文本
        top_k: 返回条数

    Returns:
        (专利数据列表, Token用量字典)
    """
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    collection = _get_collection(CHROMA_PATENT_COLLECTION)
    if collection is None:
        logger.warning("专利集合不可用，返回空结果")
        return [], empty_usage

    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        patents = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for i, doc in enumerate(docs):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0
                # 距离转相似度（0-100），距离越小相似度越高
                similarity = max(0, min(100, (1 - distance) * 100))

                patents.append({
                    "title": metadata.get("title", f"专利{i+1}"),
                    "patent_number": metadata.get("patent_number", ""),
                    "applicant": metadata.get("applicant", ""),
                    "application_date": metadata.get("application_date", ""),
                    "abstract": doc,
                    "similarity": similarity,
                    "technical_field": metadata.get("technical_field", ""),
                })

        logger.info("现有技术检索完成，返回 %d 条结果", len(patents))
        return patents, empty_usage

    except Exception as exc:
        logger.error("现有技术检索失败: %s", exc)
        return [], empty_usage


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