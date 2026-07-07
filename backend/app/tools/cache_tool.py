"""
Redis 缓存工具层
统一的缓存读写接口，支持优雅降级
所有需要缓存的模块都走这个工具，不直接操作redis
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.config import (
    REDIS_DEFAULT_TTL_SECONDS,
    REDIS_ENABLED,
    REDIS_KEY_PREFIX,
    REDIS_URL,
)

logger = logging.getLogger(__name__)

# 全局单例客户端
_redis_client: Any | None = None
_redis_unavailable_logged = False


def _build_key(key: str) -> str:
    """为缓存key添加统一前缀，避免多项目冲突"""
    return f"{REDIS_KEY_PREFIX}:{key}"


def _get_redis_client():
    """
    懒加载Redis客户端
    不可用时返回None，实现优雅降级
    只在第一次调用时创建连接，后续复用单例
    """
    global _redis_client
    global _redis_unavailable_logged

    if not REDIS_ENABLED:
        return None

    # 尝试导入redis库
    try:
        import redis
    except ImportError:
        if not _redis_unavailable_logged:
            logger.warning("未安装redis依赖，缓存功能将被跳过")
            _redis_unavailable_logged = True
        return None

    # 已创建过客户端直接复用
    if _redis_client is not None:
        return _redis_client

    # 首次创建连接并测试连通性
    try:
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        _redis_client = client
        logger.info("成功连接Redis服务")
        return _redis_client
    except Exception as exc:
        if not _redis_unavailable_logged:
            logger.warning("Redis连接失败，缓存功能将被跳过：%s", exc)
            _redis_unavailable_logged = True
        return None


def get_cached_json(key: str) -> Optional[Any]:
    """
    读取JSON缓存
    命中返回解析后的数据，未命中或失败返回None
    """
    client = _get_redis_client()
    if client is None:
        return None

    try:
        raw_value = client.get(_build_key(key))
        if raw_value is None:
            return None
        logger.info("Redis缓存命中：%s", key)
        return json.loads(raw_value)
    except Exception as exc:
        logger.debug("读取Redis缓存失败：%s", exc)
        return None


def set_cached_json(key: str, value: Any, expire_seconds: Optional[int] = None) -> None:
    """
    写入JSON缓存
    Redis不可用或写入失败时静默跳过，不影响主流程
    """
    client = _get_redis_client()
    if client is None:
        return

    ttl = expire_seconds or REDIS_DEFAULT_TTL_SECONDS
    try:
        client.set(
            _build_key(key),
            json.dumps(value, ensure_ascii=False),
            ex=ttl
        )
        logger.info("写入Redis缓存：%s，过期时间%ds", key, ttl)
    except Exception as exc:
        logger.debug("写入Redis缓存失败：%s", exc)