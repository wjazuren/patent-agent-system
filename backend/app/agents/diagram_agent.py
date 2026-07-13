"""
附图生成Agent
对应岗位：专利制图专员
核心职责：从交底书中提取系统模块和流程步骤，自动生成标准专利附图
优化：图题与发明名称强绑定，保证图文一致
"""
from __future__ import annotations
import logging
from typing import Tuple
from app.models.schemas import PatentDocket
from app.tools.graph_tool import generate_system_architecture_diagram, generate_flow_diagram
from app.tools.llm_tool import call_llm_structured
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DiagramExtractResult(BaseModel):
    """附图提取结果"""
    system_modules: list[str] = Field(description="系统核心模块列表，3-6个，简短中文名称")
    method_steps: list[str] = Field(description="方法核心步骤列表，4-8个，简短动宾短语")


EXTRACT_PROMPT = """
你是专利附图专员，请从交底书中提取系统模块和方法步骤，用于生成标准专利附图。
输出严格JSON：
- system_modules: 系统核心模块列表，3-6个，每个模块用简短中文名称
- method_steps: 方法核心步骤列表，4-8个，每个步骤用简短动宾短语
只返回JSON，不要解释。
"""


def generate_patent_diagrams(docket: PatentDocket, doc_id: str) -> Tuple[PatentDocket, dict]:
    """
    生成专利附图并回填交底书
    图题与发明名称绑定，保证图文内容匹配
    """
    logger.info("附图生成Agent开始工作，文档ID: %s", doc_id)

    # 1. 大模型提取模块和步骤
    human_prompt = f"""
    发明名称：{docket.invention_name}
    技术方案：
    {docket.technical_solution}
    具体实施方式：
    {docket.detailed_implementation[:600]}
    请提取系统核心模块和方法核心步骤。
    """
    extract_result, usage = call_llm_structured(
        system_prompt=EXTRACT_PROMPT,
        human_prompt=human_prompt,
        output_model_class=DiagramExtractResult,
    )

    # 降级：提取失败则用通用模块和步骤
    if extract_result is None:
        logger.warning("附图信息提取失败，使用通用模板")
        modules = ["任务输入模块", "调度控制模块", "智能体执行模块", "质量评审模块", "结果输出模块"]
        steps = ["任务解析与拆解", "智能体角色分配", "并行执行子任务", "质量校验评审", "迭代优化修正", "结果聚合输出"]
    else:
        modules = extract_result.system_modules
        steps = extract_result.method_steps

    # 2. 生成与发明名称绑定的图题（保证与正文内容匹配）
    arch_title = f"图1 {docket.invention_name}系统架构示意图"
    flow_title = f"图2 {docket.invention_name}方法流程示意图"

    # 3. 生成两张附图
    arch_path, arch_desc = generate_system_architecture_diagram(
        doc_id=doc_id,
        title=arch_title,
        modules=modules,
    )
    flow_path, flow_desc = generate_flow_diagram(
        doc_id=doc_id,
        title=flow_title,
        steps=steps,
    )

    # 4. 生成规范的附图说明文本，与图题严格一一对应
    drawing_desc = f"""附图说明：
{arch_desc}

{flow_desc}

附图标记说明：
S1-S{len(steps)}：方法步骤编号；
M0-M{len(modules)-1}：系统模块编号。
"""
    docket.drawing_description = drawing_desc

    # 记录附图路径到状态（可选，便于前端展示）
    docket = docket.model_copy(update={
        "diagram_paths": {
            "architecture": arch_path,
            "flow": flow_path
        }
    })
    logger.info("附图生成完成，共2张附图，存储路径: ./output/diagrams/%s/", doc_id)
    return docket, usage