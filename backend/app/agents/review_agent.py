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
from typing import Tuple,Optional,List

from app.config import MAX_ITERATION_COUNT
from app.models.schemas import (
    ComplianceReport,
    PatentDocket,
    PriorArtReport,
    ReviewResult,
    ModificationItem,
)
from app.tools.llm_tool import call_llm_structured
from app.tools.rating_rules import calculate_compliance_score


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
你是一名资深专利质检经理，负责对专利交底书进行最终质量评审。
你的任务是：综合评估交底书的质量，决定是否通过，或打回修改。

评审规则（严格遵守）：
1. 若存在上一轮问题清单，必须先逐一复核上一轮问题的解决情况，标注每个问题的状态（resolved/partial/pending）
2. 上一轮已完全解决的问题，本轮不得重复扣分
3. 打分必须与上一轮保持同一尺度，不得突然收紧或放宽标准
4. 新发现的问题按严重等级正常扣分
5. 每个问题必须分配唯一的issue_id，格式如"issue_001"
6. 每个问题必须标注所有受影响的章节affected_sections，不能只写主章节

评审维度（各25分）：
1. 新颖性评估：结合现有技术检索报告，评估发明的新颖性，是否突出区别特征
2. 撰写质量：语言专业严谨，技术方案清晰完整，有益效果有理有据
3. 合规性：格式规范，公开充分，权利要求清楚简要
4. 逻辑完整性：技术问题、方案、效果对应，整体逻辑自洽

输出要求：
必须输出严格JSON对象，包含以下字段：
- conclusion: pass / reject
- overall_score: 整体评分，0-100
- novelty_score: 0-25
- writing_score: 0-25
- compliance_score: 0-25
- logic_score: 0-25
- last_round_review: 上一轮问题复核说明，字符串
- modification_items: 修改意见数组，每个元素包含：
  - issue_id: 问题唯一ID
  - section: 所属章节，取值只能是：invention_name, background_technology, technical_problem, technical_solution, beneficial_effects, detailed_implementation, claims_draft
  - affected_sections: 受影响的所有关联章节数组,取值同section，必须为英文枚举值*
  - issue_type: format / sufficiency / novelty / logic
  - severity: minor / major / critical
  - description: 问题描述
  - suggestion: 修改建议
  - status: pending
- target_agent: writer / compliance / null
- review_comment: 整体评审说明

只返回JSON对象，不要输出任何解释文字。
"""


def review_quality_agent(
    docket: PatentDocket,
    prior_art: PriorArtReport,
    compliance_report: ComplianceReport,
    iteration_count: int,
    last_modification_items: Optional[List[ModificationItem]] = None,
) -> Tuple[ReviewResult, dict]:
    """
    质量评审主函数

    Args:
        docket: 交底书
        prior_art: 检索报告
        compliance_report: 合规报告
        iteration_count: 当前迭代次数
        新增：传入上一轮修改意见，用于复查问题解决情况，校准打分尺度

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
        logger.info("合规问题：%s", issues_text)
    else:
        issues_text = "无合规问题"

    # 格式化对比专利
    prior_text = ""
    if prior_art.prior_patents:
        prior_text = "\n".join([
            f"{i+1}. {p.title}（相似度{p.similarity_score:.1f}%）"
            for i, p in enumerate(prior_art.prior_patents[:3])
        ])

    # 格式化上一轮问题清单（迭代轮次传入）
    last_round_text = ""
    if last_modification_items and iteration_count > 1:
        last_round_text = "\n".join([
            f"- [{item.issue_id}] {item.section}：{item.description}"
            for item in last_modification_items
        ])
    else:
        last_round_text = "首轮评审，无上一轮问题"

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
【上一轮问题清单（请先逐一复核）】
{last_round_text}
【当前迭代次数】
第 {iteration_count} 轮（最多 {MAX_ITERATION_COUNT} 轮）

请进行综合质量评审，给出评分和结论。
如果分数低于80分，请明确指出需要修改的方向。
请先复核上一轮问题的解决情况，再进行本轮综合评审。
打分必须与上一轮保持同一尺度，已解决的问题不得重复扣分。
"""

    result, token_usage = call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        human_prompt=human_prompt,
        output_model_class=ReviewResult,
    )

    if result is None:
        logger.warning("质量评审失败，默认通过")
        fallback_result = ReviewResult(
            conclusion="pass",
            overall_score=75.0,
            novelty_score=18.0,
            writing_score=20.0,
            compliance_score=18.0,
            logic_score=19.0,
            modification_items=[
                ModificationItem(
                    issue_id="fallback_001",
                    section="technical_solution",
                    issue_type="logic",
                    severity="minor",
                    description="评审服务异常",
                    suggestion="建议人工复核"
                )
            ],
            target_agent=None,
            review_comment="大模型评审服务异常，自动通过，请人工复核",
        )
        return fallback_result, token_usage

    # 校准合格分
    result.compliance_score = calculate_compliance_score(compliance_report.issues) / 4

    if result.conclusion == "reject":
      compliance_issue_count = sum(1 for item in result.modification_items  if item.issue_type == "format")
      total_issues = len(result.modification_items)
      if total_issues > 0 and compliance_issue_count / total_issues > 0.6:
        result.target_agent = "compliance"
      else:
        result.target_agent = "writer"


    # 超过最大迭代次数，强制通过（避免死循环）
    if iteration_count >= MAX_ITERATION_COUNT and result.conclusion == "reject":
        logger.info("已达最大迭代次数%d，强制通过", MAX_ITERATION_COUNT)
        result.conclusion = "pass"
        result.review_comment += f"（已达最大迭代次数{MAX_ITERATION_COUNT}轮，强制通过，建议人工复核）"
        result.modification_items.append(
            ModificationItem(
                issue_id="fallback_001",
                section="overall",
                issue_type="logic",
                severity="minor",
                description=f"已迭代{MAX_ITERATION_COUNT}轮，仍有优化空间",
                suggestion="建议人工复核优化"
            )
        )

    logger.info("质量评审完成，结论: %s, 总分: %.1f", result.conclusion, result.overall_score)
    return result, token_usage