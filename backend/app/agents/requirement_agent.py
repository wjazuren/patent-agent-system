"""
需求对接 Agent
对应岗位：专利客户经理 / 技术对接工程师
核心职责：
1. 接收用户口语化的技术方案描述
2. 提取核心创新点、技术问题、技术方案等结构化信息
3. 识别关键技术术语
4. 输出标准化的技术需求结构体，供下游Agent使用

设计思路：
- 这是整个流程的入口，负责把非结构化的用户输入转换成结构化数据
- 下游所有Agent都基于这个结构化数据工作，避免每个Agent重复做语义理解
"""
from __future__ import annotations

import logging
from typing import Tuple

from app.models.schemas import StructuredRequirement, TokenUsage
from app.tools.llm_tool import call_llm_structured

logger = logging.getLogger(__name__)

# 系统提示词：定义角色身份、输出格式、提取规则
SYSTEM_PROMPT = """
你是一名资深专利技术对接工程师，擅长从研发人员的口语化描述中提炼结构化的专利需求。

你的任务是：根据用户提供的技术方案描述，提取并整理成标准化的专利交底书需求结构。

输出要求：
1. 必须输出一个严格的JSON对象，不要输出Markdown、不要输出解释文字
2. 必须包含以下字段：
   - technical_field: 技术领域分类，如"人工智能"、"大数据处理"、"通信技术"、"机械制造"等
   - core_invention: 用一句话高度概括核心发明点
   - technical_problem: 该方案要解决的具体技术问题是什么
   - technical_solution: 技术方案的整体思路概述，200字左右
   - application_scenario: 该技术的主要应用场景
   - key_terms: 数组形式，列出3-8个关键技术术语
   - applicant: 申请人名称，如果用户没提就为null
   - inventor: 发明人名称，如果用户没提就为null

3. 提取原则：
   - 准确：忠实于用户原文描述，不要自行编造技术细节
   - 专业：用专利领域的标准术语表述
   - 完整：确保技术问题、方案、效果三要素齐全
4. 只返回JSON对象
"""


def process_requirement(user_input: str) -> Tuple[StructuredRequirement | None, dict]:
    """
    处理用户输入，输出结构化需求

    Args:
        user_input: 用户原始的技术方案描述

    Returns:
        (结构化需求对象或None, Token用量字典)
        失败时返回None，由上层做降级处理
    """
    logger.info("需求对接Agent开始处理，输入长度: %d", len(user_input))

    # 构造用户提示词，传入原始输入
    human_prompt = f"""
用户提供的技术方案描述：
{user_input}

请按照要求提取结构化的专利需求信息。
"""

    # 调用大模型，指定输出模型为StructuredRequirement
    result, token_usage = call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        human_prompt=human_prompt,
        output_model_class=StructuredRequirement,
    )

    if result is None:
        logger.warning("需求对接Agent生成失败，将使用降级方案")
        # 降级方案：用简单规则生成基础结构，保证流程不中断
        fallback_result = StructuredRequirement(
            technical_field="未分类技术",
            core_invention=user_input[:50] + "..." if len(user_input) > 50 else user_input,
            technical_problem="待进一步明确的技术问题",
            technical_solution=user_input,
            application_scenario="通用应用场景",
            key_terms=[],
        )
        return fallback_result, token_usage

    logger.info("需求对接Agent处理完成，技术领域: %s", result.technical_field)
    return result, token_usage