"""
大模型调用统一工具层
所有Agent调用大模型都走这个工具，统一处理：
- 配置读取
- 异常重试
- Token统计
- 结构化输出解析
- 降级处理
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional, Tuple

from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


def _build_chat_llm():
    """
    构建大模型客户端
    使用LangChain的ChatOpenAI兼容各类大模型接口
    不可用时返回None，实现优雅降级
    """
    if not LLM_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        logger.warning("未安装 langchain_openai，大模型功能不可用")
        return None

    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL or None,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )


def _extract_token_usage(response) -> dict[str, int]:
    """
    从LangChain返回结果中提取Token用量
    统一格式，不同模型返回结构可能不同，这里做兼容处理
    使用langchain的封装格式来实现各个模型的兼容
    input:response大模型的完整返回结果

    """
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    metadata = getattr(response, "response_metadata", None) or {}
    token_usage = metadata.get("token_usage", {})
    if token_usage:
        usage["prompt_tokens"] = token_usage.get("prompt_tokens", 0)
        usage["completion_tokens"] = token_usage.get("completion_tokens", 0)
    return usage


def _extract_json_object(raw_text: str) -> Optional[str]:
    """
    从大模型返回的原始文本中提取纯JSON字符串
    处理大模型喜欢加 ```json 代码块、多余解释文字的问题
    这是结构化输出的关键清洗步骤
    """
    text = raw_text.strip()

    # 去除markdown代码块标记
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    # 提取首尾 {} 之间的内容
    start_index = text.find("{")
    end_index = text.rfind("}")
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return None

    return text[start_index: end_index + 1]


def call_llm_structured(
    system_prompt: str,
    human_prompt: str,
    output_model_class,
) -> Tuple[Optional[Any], dict[str, int]]:
    """
    结构化大模型调用函数
    输入：系统提示词 + 用户提示词 + 期望输出的Pydantic模型类
    输出：(解析后的Pydantic对象, Token用量字典)
    失败时返回 (None, 空用量)，由上层做降级处理

    Args:
        system_prompt: 系统提示词，定义角色与输出规则
        human_prompt: 用户提示词，传入具体数据
        output_model_class: 期望输出的Pydantic模型类，用于校验解析

    Returns:
        (解析后的模型实例或None, Token用量字典)
    """
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    llm = _build_chat_llm()
    if llm is None:
        logger.warning("大模型不可用，跳过结构化生成")
        return None, empty_usage

    try:
        # 调用大模型
        response = llm.invoke([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
    except Exception as exc:
        logger.error("大模型调用失败: %s", str(exc))
        return None, empty_usage

    # 提取Token用量
    token_usage = _extract_token_usage(response)

    # 获取原始文本内容（兼容字符串和列表两种格式）
    # 如果是列表，则需要将每个元素转换为字符串并拼接
    raw_text = getattr(response, "content", "")
    if isinstance(raw_text, list):
        raw_text = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_text
        )

    # 提取并解析JSON
    json_text = _extract_json_object(str(raw_text))
    if json_text is None:
        logger.warning("未能从大模型返回中提取JSON")
        logger.debug("原始返回: %s", str(raw_text)[:500])
        return None, token_usage

    try:
        # 解析JSON
        data = json.loads(json_text)
        # 用Pydantic模型校验并实例化
        result = output_model_class(**data)
        return result, token_usage
    except Exception as exc:
        logger.error("JSON解析或模型校验失败: %s", str(exc))
        logger.debug("原始JSON: %s", json_text[:500])
        return None, token_usage


def call_llm_text(system_prompt: str, human_prompt: str) -> Tuple[Optional[str], dict[str, int]]:
    """
    纯文本大模型调用
    用于不需要结构化输出的场景，如简单的文本生成、翻译
    """
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    llm = _build_chat_llm()
    if llm is None:
        return None, empty_usage

    try:
        response = llm.invoke([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
    except Exception as exc:
        logger.error("大模型调用失败: %s", str(exc))
        return None, empty_usage

    token_usage = _extract_token_usage(response)
    raw_text = getattr(response, "content", "")
    if isinstance(raw_text, list):
        raw_text = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_text
        )

    return str(raw_text).strip(), token_usage