"""
专利附图自动生成工具
根据交底书的技术方案，自动生成标准的系统架构图、方法流程图
输出SVG矢量图，符合专利附图格式要求
优化：按文档ID隔离存储 + 图题与正文强匹配
"""
from __future__ import annotations
import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)

# 附图根目录
DIAGRAM_BASE_DIR = "./output/diagrams"
os.makedirs(DIAGRAM_BASE_DIR, exist_ok=True)


def _ensure_doc_dir(doc_id: str) -> str:
    """确保对应文档的附图目录存在，返回目录路径"""
    doc_dir = os.path.join(DIAGRAM_BASE_DIR, doc_id)
    os.makedirs(doc_dir, exist_ok=True)
    return doc_dir


def generate_system_architecture_diagram(
    doc_id: str,
    title: str,
    modules: List[str],
) -> Tuple[str, str]:
    """
    生成系统架构图（模块框图）
    Args:
        doc_id: 文档ID，用于创建独立文件夹
        title: 图的完整标题，如“图1 多智能体协同作业系统架构示意图”
        modules: 系统模块列表
    Returns:
        (图片绝对路径, 附图说明文本)
    """
    try:
        from graphviz import Digraph
    except ImportError:
        logger.warning("未安装graphviz，跳过附图生成")
        return "", f"{title}（正式申请时补充绘制）"

    try:
        doc_dir = _ensure_doc_dir(doc_id)
        file_name = "architecture"
        file_path = os.path.join(doc_dir, file_name)

        dot = Digraph(name=file_name, format="svg")
        # 全局配置：从左到右布局 + 顶部图题
        dot.attr(
            rankdir="LR",
            fontname="SimSun",
            dpi="300",
            margin="0.3"  # 缩小边距，图表更饱满
        )
        dot.attr("node", shape="box", style="rounded,filled", fillcolor="#f8f9fa", fontname="SimSun", fontsize="11")
        dot.attr("edge", fontname="SimSun", arrowsize="0.8")

        # 添加模块节点
        for i, module in enumerate(modules):
            dot.node(f"M{i}", module)

        # 添加流向连线
        for i in range(len(modules) - 1):
            dot.edge(f"M{i}", f"M{i+1}")

        # 渲染保存（cleanup=True 自动删除中间dot源文件）
        dot.render(file_path, cleanup=True)
        final_path = f"{file_path}.svg"
        logger.info("系统架构图生成完成: %s", final_path)

        # 生成与图题严格对应的说明文本
        description = f"{title}；图中示出系统的核心组成模块，各模块沿箭头方向进行数据交互与任务流转。"
        return final_path, description

    except Exception as e:
        logger.error("生成架构图失败: %s", str(e))
        return "", f"{title}（生成失败，正式申请时补充绘制）"


def generate_flow_diagram(
    doc_id: str,
    title: str,
    steps: List[str],
) -> Tuple[str, str]:
    """
    生成方法流程图
    Args:
        doc_id: 文档ID，用于创建独立文件夹
        title: 图的完整标题，如“图2 多智能体协同作业方法流程示意图”
        steps: 方法步骤列表
    Returns:
        (图片绝对路径, 附图说明文本)
    """
    try:
        from graphviz import Digraph
    except ImportError:
        logger.warning("未安装graphviz，跳过附图生成")
        return "", f"{title}（正式申请时补充绘制）"

    try:
        doc_dir = _ensure_doc_dir(doc_id)
        file_name = "flow"
        file_path = os.path.join(doc_dir, file_name)

        dot = Digraph(name=file_name, format="svg")
        # 全局配置：从上到下布局 + 顶部图题
        dot.attr(
            rankdir="TB",
            fontname="SimSun",
            dpi="300",
            margin="0.3"
        )
        dot.attr("node", shape="rectangle", style="filled", fillcolor="#f0f7ff", fontname="SimSun", fontsize="11")
        dot.attr("edge", fontname="SimSun", arrowsize="0.8")

        for i, step in enumerate(steps):
            dot.node(f"S{i}", f"S{i+1}. {step}")
            if i > 0:
                dot.edge(f"S{i-1}", f"S{i}")

        dot.render(file_path, cleanup=True)
        final_path = f"{file_path}.svg"
        logger.info("方法流程图生成完成: %s", final_path)

        description = f"{title}；图中示出方法的执行步骤S1至S{len(steps)}，各步骤按箭头方向依次执行。"
        return final_path, description

    except Exception as e:
        logger.error("生成流程图失败: %s", str(e))
        return "", f"{title}（生成失败，正式申请时补充绘制）"