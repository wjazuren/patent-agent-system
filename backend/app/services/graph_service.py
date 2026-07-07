"""
LangGraph 全局调度服务
这是整个多Agent系统的核心调度引擎
负责：
1. 定义全局状态
2. 注册各个Agent节点
3. 定义节点间的流转边（正向边、回退边、条件边）
4. 执行流程调度

设计思路：
- 使用LangGraph的状态机模式，比简单的链式调用更灵活
- 支持条件分支：根据评审结果决定下一步
- 支持回退边：评审打回时回到对应Agent重新执行
- 支持迭代次数控制，避免死循环
- 全流程状态可追溯，每个节点的输入输出都在状态中
"""
from __future__ import annotations

import logging
import uuid
from typing import TypedDict, Annotated, Sequence

from app.agents.compliance_agent import check_compliance_agent
from app.agents.output_agent import output_document_agent
from app.agents.requirement_agent import process_requirement
from app.agents.review_agent import review_quality_agent
from app.agents.search_agent import search_prior_art_agent
from app.agents.writer_agent import write_docket_agent
from app.config import MAX_ITERATION_COUNT
from app.models.schemas import (
    ComplianceReport,
    FinalDocument,
    PatentDocket,
    PatentState,
    PriorArtReport,
    StructuredRequirement,
    TokenUsage,
    ReviewResult,
)

logger = logging.getLogger(__name__)


# ==================== 节点函数定义 ====================
# 每个Agent对应一个LangGraph节点函数
# 输入是当前状态，输出是状态更新字典（只更新自己负责的字段）

def node_requirement(state: dict) -> dict:
    """
    节点1：需求对接
    输入：user_input
    输出：structured_requirement + 更新token_usage + 日志
    """
    logger.info("=== 执行节点：需求对接 ===")
    # 直接通过属性访问
    user_input = state.user_input

    requirement, usage = process_requirement(user_input)

    # 更新Token统计
    token_usage = state.token_usage
    if isinstance(token_usage, dict):
        token_usage = TokenUsage(**token_usage)
    token_usage.requirement_prompt += usage.get("prompt_tokens", 0)
    token_usage.requirement_completion += usage.get("completion_tokens", 0)

    logs = state.process_logs
    logs.append(f"[需求对接] 完成，技术领域：{requirement.technical_field}")

    return {
        "structured_requirement": requirement,
        "token_usage": token_usage,
        "process_logs": logs,
    }


def node_search(state: dict) -> dict:
    """
    节点2：现有技术检索
    输入：structured_requirement
    输出：prior_art_report + 更新token_usage + 日志
    """
    logger.info("=== 执行节点：现有技术检索 ===")
    requirement = state.structured_requirement
    if isinstance(requirement, dict):
        requirement = StructuredRequirement(**requirement)

    report, usage = search_prior_art_agent(requirement)

    token_usage = state.token_usage
    if isinstance(token_usage, dict):
        token_usage = TokenUsage(**token_usage)
    token_usage.search_prompt += usage.get("prompt_tokens", 0)
    token_usage.search_completion += usage.get("completion_tokens", 0)

    logs = state.process_logs
    logs.append(f"[现有技术检索] 完成，风险等级：{report.novelty_risk_level}，对比专利{len(report.prior_patents)}篇")

    return {
        "prior_art_report": report,
        "token_usage": token_usage,
        "process_logs": logs,
    }


def node_writer(state: dict) -> dict:
    """
    节点3：交底书撰写
    输入：structured_requirement + prior_art_report + (可选)评审修改意见
    输出：draft_docket + 更新token_usage + 日志
    """
    logger.info("=== 执行节点：交底书撰写 ===")
    requirement = state.structured_requirement
    if isinstance(requirement, dict):
        requirement = StructuredRequirement(**requirement)

    prior_art = state.prior_art_report
    if isinstance(prior_art, dict):
        prior_art = PriorArtReport(**prior_art)

    # 如果是迭代修改，从评审结果中提取修改提示
    review_result = state.review_result
    iteration_hint = ""
    if review_result:
        if isinstance(review_result, dict):
            review_result = ReviewResult(**review_result)
        if review_result.modification_suggestions:
            iteration_hint = "请根据以下修改意见调整交底书：\n" + "\n".join(
                f"- {s}" for s in review_result.modification_suggestions
            )

    docket, usage = write_docket_agent(requirement, prior_art, iteration_hint)

    if docket is None:
        # 撰写失败，记录错误
        return {
            "error_message": "交底书撰写失败",
            "process_logs": state.process_logs + ["[撰写] 失败"],
        }

    token_usage = state.token_usage
    if isinstance(token_usage, dict):
        token_usage = TokenUsage(**token_usage)
    token_usage.writer_prompt += usage.get("prompt_tokens", 0)
    token_usage.writer_completion += usage.get("completion_tokens", 0)

    logs = state.process_logs
    logs.append(f"[交底书撰写] 完成，发明名称：{docket.invention_name}")

    return {
        "draft_docket": docket,
        "token_usage": token_usage,
        "process_logs": logs,
    }


def node_compliance(state: dict) -> dict:
    """
    节点4：合规校验
    输入：draft_docket
    输出：compliance_report + 更新token_usage + 日志
    """
    logger.info("=== 执行节点：合规校验 ===")
    docket = state.draft_docket
    if isinstance(docket, dict):
        docket = PatentDocket(**docket)

    report, usage = check_compliance_agent(docket)

    token_usage = state.token_usage
    if isinstance(token_usage, dict):
        token_usage = TokenUsage(**token_usage)
    token_usage.compliance_prompt += usage.get("prompt_tokens", 0)
    token_usage.compliance_completion += usage.get("completion_tokens", 0)

    logs = state.process_logs
    logs.append(f"[合规校验] 完成，是否通过：{report.is_passed}，问题{len(report.issues)}个")

    return {
        "compliance_report": report,
        "token_usage": token_usage,
        "process_logs": logs,
    }


def node_review(state: dict) -> dict:
    """
    节点5：质量评审
    输入：draft_docket + prior_art_report + compliance_report + iteration_count
    输出：review_result + iteration_count + 更新token_usage + 日志
    """
    logger.info("=== 执行节点：质量评审 ===")
    iteration_count = state.iteration_count + 1  # 迭代次数+1

    docket = state.draft_docket
    if isinstance(docket, dict):
        docket = PatentDocket(**docket)

    prior_art = state.prior_art_report
    if isinstance(prior_art, dict):
        prior_art = PriorArtReport(**prior_art)

    compliance = state.compliance_report
    if isinstance(compliance, dict):
        compliance = ComplianceReport(**compliance)

    review_result, usage = review_quality_agent(
        docket, prior_art, compliance, iteration_count
    )

    token_usage = state.token_usage
    if isinstance(token_usage, dict):
        token_usage = TokenUsage(**token_usage)
    token_usage.review_prompt += usage.get("prompt_tokens", 0)
    token_usage.review_completion += usage.get("completion_tokens", 0)

    logs = state.process_logs
    logs.append(
        f"[质量评审] 第{iteration_count}轮，结论：{review_result.conclusion}，"
        f"总分：{review_result.overall_score}"
    )

    return {
        "review_result": review_result,
        "iteration_count": iteration_count,
        "token_usage": token_usage,
        "process_logs": logs,
    }


def node_output(state: dict) -> dict:
    """
    节点6：文档输出（终节点）
    输入：所有产出
    输出：final_document + 日志
    """
    logger.info("=== 执行节点：文档输出 ===")
    docket = state.draft_docket
    if isinstance(docket, dict):
        docket = PatentDocket(**docket)

    prior_art = state.prior_art_report
    if isinstance(prior_art, dict):
        prior_art = PriorArtReport(**prior_art)

    compliance = state.compliance_report
    if isinstance(compliance, dict):
        compliance = ComplianceReport(**compliance)

    review = state.review_result
    if isinstance(review, dict):
        review = ReviewResult(**review)

    iteration_count = state.iteration_count

    final_doc, usage = output_document_agent(
        docket, prior_art, compliance, review, iteration_count
    )

    logs = state.process_logs
    logs.append(f"[文档输出] 完成，文档ID：{final_doc.document_id}")

    return {
        "final_document": final_doc,
        "process_logs": logs,
    }


# ==================== 条件路由函数 ====================

def route_after_review(state: dict) -> str:
    """
    评审后的条件路由
    根据评审结论决定下一步走向：
    - pass → 去输出节点
    - reject + target_agent=writer → 回退到撰写节点
    - reject + target_agent=compliance → 回退到合规校验节点
    - 其他情况 → 默认去输出
    """
    review_result = state.review_result
    if isinstance(review_result, dict):
        review_result = ReviewResult(**review_result)

    if review_result is None or review_result.conclusion == "pass":
        logger.info("评审通过，进入输出环节")
        return "output"

    # 打回修改
    target = review_result.target_agent
    logger.info("评审打回，目标: %s", target)

    if target == "writer":
        return "rewrite"
    elif target == "compliance":
        return "recheck_compliance"
    else:
        # 默认回撰写
        return "rewrite"


# ==================== 构建并运行Graph ====================

def build_patent_graph():
    """
    构建专利撰写多Agent工作流图
    返回编译后的LangGraph应用
    """
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        logger.error("未安装langgraph，无法构建工作流")
        return None

    # 定义状态类型，使用PatentState的字段
    # LangGraph要求用TypedDict，这里用PatentState的结构
    builder = StateGraph(PatentState)

    # 注册所有节点
    builder.add_node("requirement", node_requirement)
    builder.add_node("search", node_search)
    builder.add_node("writer", node_writer)
    builder.add_node("compliance", node_compliance)
    builder.add_node("review", node_review)
    builder.add_node("output", node_output)

    # 设置入口节点
    builder.set_entry_point("requirement")

    # 正向边：按顺序流转
    builder.add_edge("requirement", "search")
    builder.add_edge("search", "writer")
    builder.add_edge("writer", "compliance")
    builder.add_edge("compliance", "review")

    # 条件边：评审后根据结果决定走向
    builder.add_conditional_edges(
        "review",
        route_after_review,
        {
            "output": "output",        # 通过 → 输出
            "rewrite": "writer",        # 打回撰写 → 重新写
            "recheck_compliance": "compliance",  # 打回合规 → 重新校验
        }
    )

    # 输出节点是终点
    builder.add_edge("output", END)

    # 编译图
    app = builder.compile()
    logger.info("LangGraph工作流构建成功")
    return app


def run_patent_workflow(user_input: str) -> PatentState:
    """
    运行完整的专利撰写工作流

    Args:
        user_input: 用户原始技术方案描述

    Returns:
        最终的PatentState状态对象，包含所有环节的产出
    """
    logger.info("开始运行专利撰写工作流，输入长度: %d", len(user_input))

    # 生成请求ID
    request_id = f"req_{uuid.uuid4().hex[:8]}"

    # 初始化状态
    initial_state = PatentState(
        request_id=request_id,
        user_input=user_input,
        token_usage=TokenUsage(),
        process_logs=["工作流启动"],
    )

    # 构建图
    graph = build_patent_graph()
    if graph is None:
        # LangGraph不可用，走简化的线性流程
        logger.warning("LangGraph不可用，使用简化线性流程")
        return _run_simple_workflow(initial_state)

    try:
        # 执行工作流：直接传pydantic对象
        final_state = graph.invoke(initial_state)
        logger.info("工作流执行完成，最终状态: %s", type(final_state))

        # 转回PatentState对象
        if isinstance(final_state, dict):
            final_state = PatentState(**final_state)

        return final_state

    except Exception as exc:
        logger.error("工作流执行异常: %s", str(exc), exc_info=True)
        initial_state.error_message = str(exc)
        initial_state.process_logs.append(f"错误: {str(exc)}")
        return initial_state


def _run_simple_workflow(state: PatentState) -> PatentState:
    """
    简化版线性流程（LangGraph不可用时的降级方案）
    按顺序执行各个节点，不支持评审回退
    """
    logger.info("执行简化版线性流程")

    state_dict = state.model_dump()

    # 按顺序执行
    state_dict.update(node_requirement(state_dict))
    state_dict.update(node_search(state_dict))
    state_dict.update(node_writer(state_dict))
    state_dict.update(node_compliance(state_dict))
    state_dict.update(node_review(state_dict))
    state_dict.update(node_output(state_dict))

    return PatentState(**state_dict)