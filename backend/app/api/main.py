"""
FastAPI 接口层
提供RESTful API供前端或其他服务调用
接口列表：
- POST /patent/generate：生成专利交底书
- GET /patent/{document_id}：查询已生成的文档
- GET /patent/list：获取历史生成列表
- GET /health：健康检查
- GET /stats：系统统计信息

设计思路：
- 接口设计遵循RESTful规范
- 统一响应格式，成功失败都有固定结构
- 异步处理，支持长时任务
- 自动生成API文档（/docs）
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field,field_validator

from app.models.schemas import PatentState, TokenUsage
from app.services.graph_service import run_patent_workflow
from app.services.storage_service import (
    get_document,
    list_documents,
    save_document,
)

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="专利交底书多智能体撰写系统",
    description="基于多Agent协同的专利交底书智能撰写与预审系统",
    version="1.0.0",
)


# ==================== 请求响应模型 ====================

class GenerateRequest(BaseModel):
    """生成交底书请求体"""
    user_input: str = Field(..., description="技术方案描述", min_length=10)
    user_id: Optional[str] = Field(default=None, description="用户ID")


class GenerateResponse(BaseModel):
    """生成响应"""
    request_id: str = Field(..., description="请求ID")
    document_id: Optional[str] = Field(default=None, description="文档ID")
    status: str = Field(..., description="状态：success/failed")
    message: str = Field(default="", description="消息")
    risk_level: Optional[str] = Field(default=None, description="风险等级")
    iteration_count: int = Field(default=0, description="迭代次数")
    token_usage: Optional[TokenUsage] = Field(default=None, description="Token用量")
    process_logs: List[str] = Field(default_factory=list, description="流程日志")


class DocumentItem(BaseModel):
    """文档摘要项"""
    document_id: str = Field(..., description="文档ID")
    title: str = Field(..., description="发明名称")
    risk_level: str = Field(..., description="风险等级")
    created_at: datetime = Field(..., description="创建时间")
    iteration_count: int = Field(default=0, description="迭代次数")


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int = Field(..., description="总数")
    items: List[DocumentItem] = Field(default_factory=list, description="文档列表")


class DocumentDetailResponse(BaseModel):
    """文档详情响应"""
    document_id: str = Field(..., description="文档ID")
    title: str = Field(..., description="发明名称")
    content: str = Field(..., description="完整Markdown内容")
    abstract: str = Field(..., description="摘要")
    risk_level: str = Field(..., description="风险等级")
    created_at: datetime = Field(..., description="创建时间")
    iteration_count: int = Field(default=0, description="迭代次数")
    token_usage: Optional[dict] = Field(default=None, description="Token用量")

     # 新增：自动把JSON字符串转成字典
    @field_validator('token_usage', mode='before')
    @classmethod
    def parse_token_usage(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"


# ==================== 接口实现 ====================

@app.post("/patent/generate", response_model=GenerateResponse, summary="生成专利交底书")
async def generate_patent(request: GenerateRequest):
    """
    提交技术方案，生成完整的专利交底书

    - **user_input**: 技术方案的详细描述，越详细效果越好
    - **user_id**: 可选，用户标识，用于历史记录关联
    """
    logger.info("收到生成请求，输入长度: %d", len(request.user_input))

    try:
        # 运行多Agent工作流
        final_state = run_patent_workflow(request.user_input)

        # 检查是否成功
        if final_state.final_document is None:
            logger.warning("生成失败，无最终文档")
            return GenerateResponse(
                request_id=final_state.request_id,
                status="failed",
                message=final_state.error_message or "生成失败",
                process_logs=final_state.process_logs,
            )

        # 保存到数据库
        save_document(final_state, user_id=request.user_id)

        # 构造响应
        return GenerateResponse(
            request_id=final_state.request_id,
            document_id=final_state.final_document.document_id,
            status="success",
            message="生成成功",
            risk_level=final_state.final_document.final_risk_level,
            iteration_count=final_state.final_document.iteration_count,
            token_usage=final_state.token_usage,
            process_logs=final_state.process_logs,
        )

    except Exception as exc:
        logger.error("生成接口异常: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(exc)}")

@app.get("/patent/list", response_model=DocumentListResponse, summary="获取文档列表")
async def list_patent_documents(
    user_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """获取历史生成的文档列表"""
    total, items = list_documents(user_id=user_id, limit=limit, offset=offset)

    doc_items = [
        DocumentItem(
            document_id=item["document_id"],
            title=item["title"],
            risk_level=item["risk_level"],
            created_at=item["created_at"],
            iteration_count=item.get("iteration_count", 0),
        )
        for item in items
    ]

    return DocumentListResponse(total=total, items=doc_items)

@app.get("/patent/{document_id}", response_model=DocumentDetailResponse, summary="查询文档详情")
async def get_patent_document(document_id: str):
    """根据文档ID获取完整的交底书内容"""
    doc_data = get_document(document_id)
    if doc_data is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    return DocumentDetailResponse(
        document_id=doc_data["document_id"],
        title=doc_data["title"],
        content=doc_data["content"],
        abstract=doc_data["abstract"],
        risk_level=doc_data["risk_level"],
        created_at=doc_data["created_at"],
        iteration_count=doc_data.get("iteration_count", 0),
        token_usage=doc_data.get("token_usage"),
    )




@app.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """系统健康检查接口"""
    return HealthResponse()


@app.get("/stats", summary="系统统计")
async def get_stats():
    """获取系统真实统计数据"""
    from app.services.storage_service import get_stats_summary
    return get_stats_summary()