"""
现有技术检索 Agent
对应岗位：专利检索员
核心职责：
1. 根据结构化需求中的创新点，生成检索关键词
2. 从本地专利向量库中做语义检索，找到最相近的现有技术
3. 评估新颖性风险等级
4. 输出对比专利列表和风险评估报告

设计思路：
- 采用分层检索架构：优先本地向量库语义检索
- 预留官方API接入位，生产环境可替换为CNIPR等真实数据源
- 结合Redis缓存，高频检索词直接返回结果
- 风险分级：low/medium/high，为后续撰写和评审提供参考
"""
from __future__ import annotations

import hashlib
import logging
from typing import List, Tuple

from app.config import REDIS_PATENT_TTL_SECONDS
from app.models.schemas import PriorArtReport, PriorPatent, StructuredRequirement
from app.tools.cache_tool import get_cached_json, set_cached_json
from app.tools.rag_tool import search_prior_art  # RAG检索工具

logger = logging.getLogger(__name__)


def _generate_cache_key(keywords: List[str]) -> str:
    """生成检索缓存key，用关键词哈希避免key过长"""
    keyword_str = "|".join(sorted(keywords))
    hash_val = hashlib.md5(keyword_str.encode()).hexdigest()
    return f"patent_search:{hash_val}"


def _assess_risk(similar_patents: List[PriorPatent]) -> Tuple[str, str, List[str]]:
    """
    根据对比专利的相似度，评估新颖性风险等级
    风险分级逻辑：
    - 有相似度>80的专利 → high 高风险
    - 有相似度>60的专利 → medium 中风险
    - 全部<60 → low 低风险
    """
    if not similar_patents:
        return "low", "未检索到高度相关的现有技术，新颖性风险较低", []

    max_similarity = max(p.similarity_score for p in similar_patents)
    high_risk_points = []

    if max_similarity >= 80:
        risk_level = "high"
        assessment = f"检测到高度相似现有技术（最高相似度{max_similarity:.1f}%），新颖性风险较高，建议重点调整权利要求保护范围"
        high_risk_points.append("核心技术方案存在高度相似现有技术")
    elif max_similarity >= 60:
        risk_level = "medium"
        assessment = f"检测到一定相似度的现有技术（最高相似度{max_similarity:.1f}%），存在一定新颖性风险，建议突出区别技术特征"
    else:
        risk_level = "low"
        assessment = f"未检测到高相似度现有技术（最高相似度{max_similarity:.1f}%），新颖性风险较低"

    return risk_level, assessment, high_risk_points


def search_prior_art_agent(
    requirement: StructuredRequirement,
) -> Tuple[PriorArtReport, dict]:
    """
    现有技术检索主函数

    Args:
        requirement: 结构化技术需求

    Returns:
        (现有技术检索报告, Token用量字典)
    """
    logger.info("现有技术检索Agent开始工作，技术领域: %s", requirement.technical_field)

    # 构造检索关键词：核心发明点 + 关键术语
    search_keywords = [requirement.core_invention] + requirement.key_terms
    search_query = " ".join(search_keywords)

    # 先查缓存
    cache_key = _generate_cache_key(search_keywords)
    cached = get_cached_json(cache_key)
    if cached:
        logger.info("检索结果命中缓存")
        # 缓存数据转回模型对象
        report = PriorArtReport(**cached)
        return report, {"prompt_tokens": 0, "completion_tokens": 0}

    # 调用RAG向量检索，从本地专利库中查找相似专利
    # search_prior_art 返回 (专利列表, embedding用量)
    similar_patents_data, embedding_usage = search_prior_art(
        query=search_query,
        top_k=5,
    )

    # 转换成PriorPatent模型列表
    prior_patents = []
    for idx, patent_data in enumerate(similar_patents_data):
        patent = PriorPatent(
            title=patent_data.get("title", f"对比专利{idx+1}"),
            patent_number=patent_data.get("patent_number", f"CN{idx+1:06d}A"),
            applicant=patent_data.get("applicant", "未知申请人"),
            application_date=patent_data.get("application_date", "未知"),
            abstract=patent_data.get("abstract", ""),
            similarity_score=float(patent_data.get("similarity", 50.0)),
            technical_field=patent_data.get("technical_field", ""),
        )
        prior_patents.append(patent)

    # 评估风险等级
    risk_level, risk_assessment, high_risk_points = _assess_risk(prior_patents)

    # 组装检索报告
    report = PriorArtReport(
        search_keywords=search_keywords,
        prior_patents=prior_patents,
        novelty_risk_level=risk_level,
        risk_assessment=risk_assessment,
        high_risk_points=high_risk_points,
        data_source="local_vector_database",
    )

    # 写入缓存
    set_cached_json(cache_key, report.model_dump(mode="json"), expire_seconds=REDIS_PATENT_TTL_SECONDS)

    logger.info("现有技术检索完成，风险等级: %s, 对比专利数: %d",
                risk_level, len(prior_patents))

    return report, embedding_usage