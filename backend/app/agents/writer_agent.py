"""
交底书撰写 Agent
对应岗位：专利代理人
核心职责：
1. 基于结构化需求和现有技术检索报告
2. 参考专利模板知识库
3. 分模块生成完整的专利交底书全文
4. 输出符合专利撰写规范的结构化交底书

设计思路：
- 分模块撰写，每个章节有专门的撰写要求
- 结合RAG检索到的专利模板和优秀范例，保证专业性
- 考虑新颖性风险，高风险时突出区别技术特征
- 结构化输出，每个章节都是独立字段，方便后续校验和修改
"""
from __future__ import annotations

import logging
from typing import Tuple

from app.models.schemas import (
    PatentDocket,
    PriorArtReport,
    StructuredRequirement,
)
from app.tools.llm_tool import call_llm_structured
from app.tools.rag_tool import search_templates

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
你是一名资深专利代理人，擅长撰写高质量的专利交底书。

你的任务是：根据技术需求和现有技术检索报告，撰写一份完整的专利交底书。

撰写要求：
1. 严格遵循专利撰写规范，语言专业、严谨、逻辑清晰
2. 技术方案描述要充分公开，确保本领域技术人员能够实现
3. 权利要求书要清楚、简要地限定要求专利保护的范围
4. 有益效果要与技术问题相对应，有理有据
5. 具体实施方式要有足够的细节，支持权利要求的保护范围

输出要求：
必须输出一个严格的JSON对象，包含以下字段：
- invention_name: 发明名称，简明扼要，体现发明主题
- technical_field: 技术领域
- background_technology: 背景技术，介绍现有技术状况和存在的不足
- technical_problem: 本发明要解决的技术问题
- technical_solution: 本发明的技术方案，完整描述核心技术构思
- beneficial_effects: 本发明的有益效果，**字符串格式，分点用数字序号+换行标注，禁止输出JSON数组**
- detailed_implementation: 具体实施方式，详细描述至少一个实施例
- drawing_description: 附图说明，没有就为null
- claims_draft: 权利要求初稿，**字符串格式，每条权利要求换行书写，禁止输出JSON数组**，至少包含1项独立权利要求和2-3项从属权利要求
- key_terms_explanation:  核心术语解释，字符串数组，每个元素直接是"术语：解释"的字符串，不要输出对象/字典格式

注意：
1. 如果现有技术风险较高，要在撰写中突出区别技术特征
2. 只返回JSON对象，不要输出任何解释文字
"""


def write_docket_agent(
    requirement: StructuredRequirement,
    prior_art: PriorArtReport,
    iteration_hint: str = "",
) -> Tuple[PatentDocket | None, dict]:
    """
    撰写交底书主函数

    Args:
        requirement: 结构化技术需求
        prior_art: 现有技术检索报告
        iteration_hint: 迭代修改提示（评审打回时传入）

    Returns:
        (交底书对象或None, Token用量字典)
    """
    logger.info("交底书撰写Agent开始工作")

    # 检索相关专利模板，作为RAG上下文增强撰写质量
    template_query = f"{requirement.technical_field} {requirement.core_invention}"
    templates = search_templates(template_query, top_k=2)
    template_context = "\n\n".join(templates) if templates else "暂无参考模板"

    # 格式化对比专利信息
    prior_patents_text = ""
    if prior_art.prior_patents:
        prior_patents_text = "\n".join([
            f"对比专利{i+1}：{p.title}（相似度{p.similarity_score:.1f}%）\n摘要：{p.abstract[:200]}"
            for i, p in enumerate(prior_art.prior_patents[:3])
        ])

    # 构造用户提示词
    human_prompt = f"""
【技术需求】
技术领域：{requirement.technical_field}
核心发明点：{requirement.core_invention}
技术问题：{requirement.technical_problem}
技术方案：{requirement.technical_solution}
应用场景：{requirement.application_scenario}
关键术语：{', '.join(requirement.key_terms) if requirement.key_terms else '无'}

【现有技术检索报告】
新颖性风险等级：{prior_art.novelty_risk_level}
风险评估：{prior_art.risk_assessment}
对比专利信息：
{prior_patents_text if prior_patents_text else '未检索到相关对比专利'}

【参考模板】
{template_context}

【迭代修改提示】
{iteration_hint if iteration_hint else '首次撰写，无修改提示'}

请根据以上信息，撰写一份完整的专利交底书。
注意：如果新颖性风险较高，请重点突出与现有技术的区别特征。
"""

    # 调用大模型生成
    result, token_usage = call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        human_prompt=human_prompt,
        output_model_class=PatentDocket,
    )

    if result is None:
        logger.warning("交底书撰写失败")
        return None, token_usage

    logger.info("交底书撰写完成，发明名称: %s", result.invention_name)
    return result, token_usage