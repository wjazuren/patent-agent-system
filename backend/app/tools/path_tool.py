"""
路径转换工具
本地文件路径 <-> 前端可访问的静态资源URL
"""
from __future__ import annotations
import os


def local_path_to_static_url(local_path: str, static_prefix: str = "/static") -> str:
    """
    将服务器本地相对路径，转换为前端可访问的静态资源相对URL
    Args:
        local_path: 本地路径，如 ./output/diagrams/xxx/architecture.svg
        static_prefix: 静态资源挂载前缀，和main.py中mount的路径一致
    Returns:
        前端可直接拼接baseURL的相对路径，如 /static/diagrams/xxx/architecture.svg
    """
    if not local_path:
        return ""
    
    # 统一替换Windows反斜杠为正斜杠
    path = local_path.replace("\\", "/")
    
    # 移除本地前缀 ./output 或 output/，统一加上静态前缀
    if path.startswith("./output/"):
        path = path[len("./output/"):]
    elif path.startswith("output/"):
        path = path[len("output/"):]
    
    # 拼接静态资源前缀
    return f"{static_prefix}/{path}"


def batch_convert_diagram_paths(diagram_dict: dict | None) -> dict | None:
    """批量转换附图路径字典"""
    if not diagram_dict:
        return None
    return {
        key: local_path_to_static_url(value)
        for key, value in diagram_dict.items()
    }