"""
质量评审 Agent
对应岗位：质检经理 / 资深专利代理人
核心职责：
1. 综合评估交底书的整体质量
2. 从新颖性、撰写质量、合规性、逻辑完整性四个维度打分
3. 决定是否通过或打回修改
4. 如果打回，指定需要修改的Agent和修改意见

设计思路：
- 这是多Agent协同系统的核心亮点，形成了「生成-校验-评审-修改」的反馈闭环
- 评审Agent站在全局视角，做最终质量把关
- 支持多轮迭代，每轮迭代都有明确的修改方向
- 超过最大迭代次数则终止，标记为需人工复核
"""
from __future__ import annotations

import logging
from typing import Tuple

from app.config import MAX_ITERATION_COUNT
from app.models.schemas import (
    ComplianceReport,
    PatentDocket,
    PriorArtReport,
    ReviewResult,
)
from app.tools.llm_tool import call_llm_structured

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
你是一名资深专利质检经理，负责对专利交底书进行最终质量评审。

你的任务是：综合评估交底书的质量，决定是否通过，或打回修改。

评审维度：
1. 新颖性评估（25分）：
   - 结合现有技术检索报告，评估发明的新颖性
   - 是否突出了与现有技术的区别特征
   - 高风险专利是否有针对性的规避设计

2. 撰写质量（25分）：
   - 语言是否专业、严谨、符合专利撰写规范
   - 技术方案描述是否清晰、完整
   - 有益效果是否有理有据

3. 合规性（25分）：
   - 格式是否规范，章节是否完整
   - 公开是否充分
   - 权利要求是否清楚、简要

4. 逻辑完整性（25分）：
   - 技术问题、技术方案、有益效果是否对应
   - 整体逻辑是否自洽
   - 具体实施方式是否支持权利要求

输出要求：
必须输出一个严格的JSON对象，包含以下字段：
- conclusion: 评审结论，pass（通过）或 reject（打回修改）
- overall_score: 整体评分，0-100
- novelty_score: 新颖性得分，0-25
- writing_score: 撰写质量得分，0-25
- compliance_score: 合规性得分，0-25
- logic_score: 逻辑完整性得分，0-25
- modification_suggestions: 修改意见数组，列出具体需要修改的地方
- target_agent: 需要打回修改的Agent，writer（撰写Agent）或 compliance（合规Agent），通过则为null
- review_comment: 整体评审说明

评审规则：
- 总分>=80分 → 通过（pass）
- 总分<80分 → 打回修改（reject）
- 如果主要是撰写质量问题 → 打回writer
- 如果主要是合规格式问题 → 打回compliance
- 只返回JSON对象，不要输出任何解释文字
"""


def review_quality_agent(
    docket: PatentDocket,
    prior_art: PriorArtReport,
    compliance_report: ComplianceReport,
    iteration_count: int,
) -> Tuple[ReviewResult, dict]:
    """
    质量评审主函数

    Args:
        docket: 交底书
        prior_art: 检索报告
        compliance_report: 合规报告
        iteration_count: 当前迭代次数

    Returns:
        (评审结果, Token用量字典)
    """
    logger.info("质量评审Agent开始工作，当前第%d轮", iteration_count)

    # 格式化合规问题
    issues_text = ""
    if compliance_report.issues:
        issues_text = "\n".join([
            f"[{i.severity}] {i.section}：{i.description} → 建议：{i.suggestion}"
            for i in compliance_report.issues
        ])
    else:
        issues_text = "无合规问题"

    # 格式化对比专利
    prior_text = ""
    if prior_art.prior_patents:
        prior_text = "\n".join([
            f"{i+1}. {p.title}（相似度{p.similarity_score:.1f}%）"
            for i, p in enumerate(prior_art.prior_patents[:3])
        ])

    human_prompt = f"""
【交底书摘要】
发明名称：{docket.invention_name}
技术领域：{docket.technical_field}
核心方案：{docket.technical_solution[:300]}...

【现有技术检索报告】
风险等级：{prior_art.novelty_risk_level}
风险评估：{prior_art.risk_assessment}
主要对比专利：
{prior_text if prior_text else '无'}

【合规校验报告】
格式得分：{compliance_report.format_score}/100
充分性得分：{compliance_report.sufficiency_score}/100
问题清单：
{issues_text}

【当前迭代次数】
第 {iteration_count} 轮（最多 {MAX_ITERATION_COUNT} 轮）

请进行综合质量评审，给出评分和结论。
如果分数低于80分，请明确指出需要修改的方向。
"""

    result, token_usage = call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        human_prompt=human_prompt,
        output_model_class=ReviewResult,
    )

    if result is None:
        # 大模型失败，默认通过（保证流程不中断）
        logger.warning("质量评审失败，默认通过")
        fallback_result = ReviewResult(
            conclusion="pass",
            overall_score=75.0,
            novelty_score=18.0,
            writing_score=20.0,
            compliance_score=18.0,
            logic_score=19.0,
            modification_suggestions=["评审服务异常，建议人工复核"],
            target_agent=None,
            review_comment="大模型评审服务异常，自动通过，请人工复核",
        )
        return fallback_result, token_usage

    # 超过最大迭代次数，强制通过（避免死循环）
    if iteration_count >= MAX_ITERATION_COUNT and result.conclusion == "reject":
        logger.info("已达最大迭代次数%d，强制通过", MAX_ITERATION_COUNT)
        result.conclusion = "pass"
        result.review_comment += f"（已达最大迭代次数{MAX_ITERATION_COUNT}轮，强制通过，建议人工复核）"
        result.modification_suggestions.append(f"已迭代{MAX_ITERATION_COUNT}轮，仍有优化空间，建议人工复核")

    logger.info("质量评审完成，结论: %s, 总分: %.1f", result.conclusion, result.overall_score)
    return result, token_usage