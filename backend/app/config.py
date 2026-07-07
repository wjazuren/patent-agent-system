"""
全局配置模块
所有配置项统一从环境变量读取，支持 .env 文件加载
生产环境与开发环境通过环境变量切换
"""
from __future__ import annotations

import os
from typing import Optional
from dotenv import load_dotenv
import logging

# 加载 .env 文件（开发环境用）
load_dotenv()


# ==================== 大模型配置 ====================
# 大模型 API 密钥
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
# 大模型接口地址（兼容OpenAI格式）
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
# 使用的模型名称
LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen3.6-plus")
# 请求超时时间（秒）
LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
# 最大重试次数
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
# 生成温度，越低越稳定（专利撰写需要稳定输出）
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))


# ==================== Redis 缓存配置 ====================
# 是否启用Redis缓存
REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "True").lower() == "true"
# Redis连接地址
REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
# 缓存key前缀，避免多项目冲突
REDIS_KEY_PREFIX: str = os.getenv("REDIS_KEY_PREFIX", "patent_agent")
# 默认缓存过期时间（秒）
REDIS_DEFAULT_TTL_SECONDS: int = int(os.getenv("REDIS_DEFAULT_TTL_SECONDS", "86400"))
# 专利检索结果缓存时间（7天）
REDIS_PATENT_TTL_SECONDS: int = int(os.getenv("REDIS_PATENT_TTL_SECONDS", "604800"))


# ==================== 向量库配置 ====================
# Chroma向量库持久化路径
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
# 专利知识库集合名称
CHROMA_PATENT_COLLECTION: str = os.getenv("CHROMA_PATENT_COLLECTION", "patent_prior_art")
# 模板知识库集合名称
CHROMA_TEMPLATE_COLLECTION: str = os.getenv("CHROMA_TEMPLATE_COLLECTION", "patent_templates")
# 审查规范集合名称
CHROMA_RULES_COLLECTION: str = os.getenv("CHROMA_RULES_COLLECTION", "patent_rules")


# ==================== 系统配置 ====================
# 最大迭代次数（评审打回最多几轮）
MAX_ITERATION_COUNT: int = int(os.getenv("MAX_ITERATION_COUNT", "3"))
# 日志级别
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
# SQLite数据库路径
SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./data/patent_system.db")

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
def validate_config() -> None:
    """
    配置校验函数
    启动时调用，检查关键配置是否完整
    """
    if not LLM_API_KEY:
        print("⚠️  警告：未配置 LLM_API_KEY，大模型功能将不可用")