"""
合规校验 Agent
对应岗位：专利流程专员 / 形式审查员
核心职责：
1. 格式规范校验：章节完整性、术语统一、标点规范
2. 公开充分性校验：技术方案是否可实现、是否缺少必要技术特征
3. 权利要求格式校验
4. 输出合规问题清单和修改建议

设计思路：
- 规则+大模型混合校验：简单格式问题用规则，复杂的充分性判断用大模型
- 问题分级：minor（轻微）、major（重要）、critical（严重）
- 为后续评审Agent提供量化的合规得分
- 输出的问题清单直接可以作为打回修改的依据
"""
from __future__ import annotations

import logging
from typing import Tuple

from app.models.schemas import ComplianceIssue, ComplianceReport, PatentDocket
from app.tools.llm_tool import call_llm_structured
from app.tools.rag_tool import search_rules
from app.tools.rating_rules import calculate_compliance_score, judge_compliance_pass

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
你是一名资深专利形式审查员，擅长对专利交底书进行合规性校验。

你的任务是：对提交的专利交底书进行全面的合规性检查，找出存在的问题并给出修改建议。

校验维度：
1. 格式规范性
   - 章节是否完整，是否缺少必要章节
   - 术语是否统一，同一概念是否有多种表述
   - 标点符号、格式是否规范
   - 发明名称是否清楚、简要

2. 公开充分性
   - 技术方案描述是否充分，本领域技术人员能否实现
   - 是否缺少必要的技术特征
   - 有益效果是否有技术方案支撑
   - 具体实施方式是否足够详细

3. 权利要求规范性
   - 权利要求是否清楚、简要
   - 是否缺少必要技术特征
   - 从属权利要求引用是否正确

输出要求：
必须输出一个严格的JSON对象，包含以下字段：
- is_passed: 布尔值，是否整体通过校验
- issues: 问题数组，每个问题包含：
  - section: 问题所在章节
  - description: 问题描述
  - severity: 问题等级：minor / major / critical
  - suggestion: 修改建议
- format_score: 格式合规得分，0-100
- sufficiency_score: 公开充分性得分，0-100
- overall_comment: 整体校验说明

注意：只返回JSON对象，不要输出任何解释文字。
"""


def _rule_based_check(docket: PatentDocket) -> list[ComplianceIssue]:
    """
    规则级校验：用简单规则快速检查基础格式问题
    这些问题不需要大模型判断，规则处理更快更稳定
    """
    issues = []

    # 检查必要字段是否为空
    if not docket.invention_name or len(docket.invention_name) < 5:
        issues.append(ComplianceIssue(
            section="发明名称",
            description="发明名称过短或为空，不能清楚地表明发明主题",
            severity="major",
            suggestion="请补充完整的发明名称，一般不超过25个字"
        ))

    if not docket.background_technology or len(docket.background_technology) < 100:
        issues.append(ComplianceIssue(
            section="背景技术",
            description="背景技术内容过短，未能充分介绍现有技术状况",
            severity="major",
            suggestion="请补充现有技术的详细描述，以及现有技术存在的缺陷"
        ))

    if not docket.technical_solution or len(docket.technical_solution) < 200:
        issues.append(ComplianceIssue(
            section="技术方案",
            description="技术方案描述不够详细，可能存在公开不充分的风险",
            severity="critical",
            suggestion="请补充技术方案的详细描述，确保本领域技术人员能够实现"
        ))

    if not docket.detailed_implementation or len(docket.detailed_implementation) < 300:
        issues.append(ComplianceIssue(
            section="具体实施方式",
            description="具体实施方式内容不足，无法支持权利要求的保护范围",
            severity="critical",
            suggestion="请补充至少一个详细的实施例，包含具体的参数、步骤、效果"
        ))

    if not docket.claims_draft or len(docket.claims_draft) < 100:
        issues.append(ComplianceIssue(
            section="权利要求书",
            description="权利要求书内容过短或缺失",
            severity="critical",
            suggestion="请补充完整的权利要求书，至少包含1项独立权利要求"
        ))

    return issues


def check_compliance_agent(
    docket: PatentDocket,
) -> Tuple[ComplianceReport, dict]:
    """
    合规校验主函数

    Args:
        docket: 待校验的交底书

    Returns:
        (合规报告, Token用量字典)
    """
    logger.info("合规校验Agent开始工作")

    # 第一步：规则级快速校验
    rule_issues = _rule_based_check(docket)

    # 第二步：大模型深度校验
    # 检索相关审查规范，增强校验专业性
    rules = search_rules("专利公开充分性 形式审查 撰写规范", top_k=3)
    rules_context = "\n\n".join(rules) if rules else "暂无参考规范"

    human_prompt = f"""
【待校验交底书】
发明名称：{docket.invention_name}
技术领域：{docket.technical_field}

背景技术：
{docket.background_technology}

技术问题：
{docket.technical_problem}

技术方案：
{docket.technical_solution}

有益效果：
{docket.beneficial_effects}

具体实施方式：
{docket.detailed_implementation}

权利要求书：
{docket.claims_draft}

【参考审查规范】
{rules_context}

请对以上交底书进行全面的合规性校验。
注意：重点关注公开充分性、权利要求规范性等深层次问题。
"""

    llm_result, token_usage = call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        human_prompt=human_prompt,
        output_model_class=ComplianceReport,
    )

    if llm_result is None:
        # 大模型失败，只用规则结果
        logger.warning("大模型合规校验失败，仅使用规则校验")
        rule_only_report = ComplianceReport(
            is_passed=len(rule_issues) == 0,
            issues=rule_issues,
            format_score=80.0 if len(rule_issues) < 3 else 60.0,
            sufficiency_score=70.0,
            overall_comment="仅完成规则级格式校验，建议人工复核",
        )
        return rule_only_report, token_usage

    # 合并规则问题和大模型问题（去重）
    all_issues = list(rule_issues)
    seen_descriptions = {issue.description for issue in rule_issues}
    for issue in llm_result.issues:
        if issue.description not in seen_descriptions:
            all_issues.append(issue)
            seen_descriptions.add(issue.description)

    # 判断是否通过：没有critical级问题且major级不超过2个,7.8
    is_passed = judge_compliance_pass(all_issues)
    format_score = calculate_compliance_score(all_issues)
    

    final_report = ComplianceReport(
        is_passed=is_passed,
        issues=all_issues,
        format_score=format_score,
        sufficiency_score=llm_result.sufficiency_score,
        overall_comment=llm_result.overall_comment,
    )

    logger.info("合规校验完成，是否通过: %s, 问题数: %d", is_passed, len(all_issues))
    return final_report, token_usage