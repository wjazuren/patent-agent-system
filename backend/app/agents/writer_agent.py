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
from typing import Tuple,List,Optional

from app.models.schemas import (
    ModificationItem,
    PatentDocket,
    PriorArtReport,
    StructuredRequirement,
)
from app.tools.llm_tool import call_llm_structured,call_llm_text
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
    existing_docket:Optional[PatentDocket] = None,
    modification_items:Optional[List[ModificationItem]] = None,
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

    if existing_docket is None or not modification_items:
      logger.info("初次撰写，全量撰写")

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
    # 第二种场景，单章节修改
    logger.info("运行模型，增量定向修改")
    updated_docket = existing_docket.model_copy(deep=True)
    total_usage = {"prompt_tokens":0,"completion_tokens":0}

    # 按章节分组修改意见
    section_groups:dict[str,List[ModificationItem]] = {}
    for item in modification_items:
      if not hasattr(updated_docket,item.section):
        continue
      if item.section not in section_groups:
        section_groups[item.section] = []
      section_groups[item.section].append(item)
      # 所有关联章节同步加入
      for sec in item.affected_sections:
          if hasattr(updated_docket, sec) and sec != item.section:
              if sec not in section_groups:
                  section_groups[sec] = []
              section_groups[sec].append(item)
    
    logger.info("待修改章节:%s",list(section_groups.keys()))
    # 构建全局一致性约束（从项目共性规则提取）
    global_constraints = """
    
    1. 核心机制表述统一：所有阈值相关表述统一为"动态阈值"，禁止出现"预设阈值""固定阈值"
    2. 核心技术特征"消息交互总线"必须在权利要求、技术方案、实施例中保持对应
    3. 不得新增原文未提及的技术组件和算法
    """
    # 逐章节修改
    for section,issue in section_groups.items():
      original_content = getattr(updated_docket,section,"")
      if not original_content:
        continue

      new_content,usage = write_sigle_section(
        section_name=section,
        original_content=original_content,
        issues=issue,
        requirement=requirement,
        prior_art=prior_art,
        global_constraints=global_constraints,
      )

      total_usage["prompt_tokens"] += usage.get("prompt_tokens",0)
      total_usage["completion_tokens"] += usage.get("completion_tokens",0)

      if new_content:
        setattr(updated_docket,section,new_content)
        logger.info("修改了%s章节",section)
    logger.info("增量修改完成，发明名称:%s",updated_docket.invention_name)
    return updated_docket,total_usage







def write_sigle_section(
  section_name:str,
  original_content:str,
  issues:List[ModificationItem],
  requirement:StructuredRequirement,
  prior_art:PriorArtReport,
  global_constraints: str = "",
) -> Tuple[str | None,dict]:
  """
  单章节修改
  Args:
    section_name: 修改的章节名称
    original_content: 原始内容
    issues: 修改建议
    requirements: 结构化需求
    prior_art: 检索报告
  Returns:
    (修改后的内容或None, Token用量字典)
  """
  logger.info("单章节修改开始工作")
  issue_text = "\n".join([f"- {item.description} 建议:{item.suggestion}" for item in issues])
  system_prompt = """
你是一名资深专利代理人，擅长针对性修改专利交底书的指定章节。
你的任务是：根据给出的问题和修改建议，只修改对应章节的内容，保持章节的专业性和严谨性。
要求：
1. 只输出修改后的章节正文，不要输出解释、不要输出标题
2. 忠实于原文的核心内容，只针对问题点修改，不要随意增删核心技术信息
3. 语言符合专利撰写规范，严谨、专业、清晰
"""
  human_prompt = f"""
【全局一致性约束（必须严格遵守，违反则修改无效）】
{global_constraints if global_constraints else '无特殊约束，保持全文术语与逻辑一致'}
【章节名称】{section_name}
【原始内容】
{original_content}
【需要修改的问题】
{issue_text}
【技术背景参考】
核心发明点：{requirement.core_invention}
技术领域：{requirement.technical_field}
新颖性风险等级：{prior_art.novelty_risk_level}
请针对问题修改该章节内容，只输出修改后的正文。
"""
  return call_llm_text(system_prompt, human_prompt)
