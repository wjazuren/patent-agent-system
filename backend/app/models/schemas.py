"""
全链路数据模型定义
所有Agent的输入输出均使用Pydantic模型约束，保证格式统一、可校验
每个环节的输出都是结构化的，避免大模型自由文本导致系统不稳定
"""
from __future__ import annotations

from datetime import datetime
from pydoc import classname
from typing import Optional, List
from pydantic import BaseModel, Field,field_validator  


# ==================== 需求对接阶段模型 ====================
class StructuredRequirement(BaseModel):
    """结构化技术需求：由需求对接Agent输出"""
    # 技术领域分类（如：人工智能、大数据、通信、机械）
    technical_field: str = Field(..., description="技术领域分类")
    # 核心发明点（一句话总结）
    core_invention: str = Field(..., description="核心发明点一句话总结")
    # 要解决的技术问题
    technical_problem: str = Field(..., description="要解决的技术问题")
    # 技术方案概述
    technical_solution: str = Field(..., description="技术方案概述")
    # 应用场景
    application_scenario: str = Field(..., description="应用场景")
    # 关键技术术语列表
    key_terms: List[str] = Field(default_factory=list, description="关键技术术语")
    # 申请人信息（可选）
    applicant: Optional[str] = Field(default=None, description="申请人")
    # 发明人信息（可选）
    inventor: Optional[str] = Field(default=None, description="发明人")


# ==================== 检索阶段模型 ====================
class PriorPatent(BaseModel):
    """单篇对比专利信息"""
    # 专利标题
    title: str = Field(..., description="专利标题")
    # 专利号
    patent_number: str = Field(..., description="专利号")
    # 申请人
    applicant: str = Field(..., description="申请人")
    # 申请日
    application_date: str = Field(..., description="申请日")
    # 摘要
    abstract: str = Field(..., description="专利摘要")
    # 相似度评分（0-100）
    similarity_score: float = Field(..., ge=0, le=100, description="相似度评分")
    # 技术领域
    technical_field: Optional[str] = Field(default=None, description="技术领域")


class PriorArtReport(BaseModel):
    """现有技术检索报告：由检索Agent输出"""
    # 检索关键词
    search_keywords: List[str] = Field(default_factory=list, description="检索关键词")
    # 对比专利列表
    prior_patents: List[PriorPatent] = Field(default_factory=list, description="对比专利列表")
    # 新颖性风险等级：low / medium / high
    novelty_risk_level: str = Field(..., description="新颖性风险等级：low/medium/high")
    # 风险评估说明
    risk_assessment: str = Field(..., description="风险评估说明")
    # 高风险技术点
    high_risk_points: List[str] = Field(default_factory=list, description="高风险技术点")
    # 检索数据源说明
    data_source: str = Field(default="local_vector", description="检索数据源")


# ==================== 撰写阶段模型 ====================
class PatentDocket(BaseModel):
    """专利交底书全文：由撰写Agent输出"""
    # 发明名称
    invention_name: str = Field(..., description="发明名称")
    # 技术领域
    technical_field: str = Field(..., description="技术领域")
    # 背景技术
    background_technology: str = Field(..., description="背景技术")
    # 发明内容 - 技术问题
    technical_problem: str = Field(..., description="要解决的技术问题")
    # 发明内容 - 技术方案
    technical_solution: str = Field(..., description="技术方案")
    # 发明内容 - 有益效果
    beneficial_effects: str = Field(..., description="有益效果")
    # 具体实施方式
    detailed_implementation: str = Field(..., description="具体实施方式")
    # 附图说明（可选）
    drawing_description: Optional[str] = Field(default=None, description="附图说明")
    # 权利要求初稿
    claims_draft: str = Field(..., description="权利要求初稿")
    # 核心术语解释
    key_terms_explanation: List[str] = Field(default_factory=list, description="核心术语解释")

    @field_validator("beneficial_effects","claims_draft")
    @classmethod
    def list_to_multi_str(cls,v):
      '''
      前置校验，如果大模型返回的list，则转为多行str
      '''
      if isinstance(v,list):
        return "\n".join([f"{i+1}.{item}" for i,item in enumerate(v)])
      
      return v


# ==================== 合规校验阶段模型 ====================
class ComplianceIssue(BaseModel):
    """单条合规问题"""
    # 问题所在章节
    section: str = Field(..., description="问题所在章节")
    # 问题描述
    description: str = Field(..., description="问题描述")
    # 问题等级：minor / major / critical
    severity: str = Field(..., description="问题等级：minor/major/critical")
    # 修改建议
    suggestion: str = Field(..., description="修改建议")


class ComplianceReport(BaseModel):
    """合规校验报告：由合规校验Agent输出"""
    # 是否通过
    is_passed: bool = Field(..., description="是否通过校验")
    # 问题列表
    issues: List[ComplianceIssue] = Field(default_factory=list, description="问题列表")
    # 格式合规得分（0-100）
    format_score: float = Field(default=0, description="格式合规得分")
    # 公开充分性得分
    sufficiency_score: float = Field(default=0, description="公开充分性得分")
    # 整体校验说明
    overall_comment: str = Field(default="", description="整体校验说明")


# ==================== 评审阶段模型 ====================
class ReviewResult(BaseModel):
    """质量评审结果：由评审Agent输出"""
    # 评审结论：pass / reject
    conclusion: str = Field(..., description="评审结论：pass/reject")
    # 整体评分（0-100）
    overall_score: float = Field(..., ge=0, le=100, description="整体评分")
    # 各维度评分
    novelty_score: float = Field(default=0, description="新颖性评估得分")
    writing_score: float = Field(default=0, description="撰写质量得分")
    compliance_score: float = Field(default=0, description="合规性得分")
    logic_score: float = Field(default=0, description="逻辑完整性得分")
    # 修改意见列表
    modification_suggestions: List[str] = Field(default_factory=list, description="修改意见列表")
    # 需要打回修改的Agent：writer / compliance / search
    target_agent: Optional[str] = Field(default=None, description="需要打回修改的Agent")
    # 评审说明
    review_comment: str = Field(default="", description="评审说明")


# ==================== 最终输出模型 ====================
class FinalDocument(BaseModel):
    """最终交付文档：由输出Agent生成"""
    # 文档ID
    document_id: str = Field(..., description="文档ID")
    # 完整Markdown格式交底书
    full_markdown: str = Field(..., description="完整Markdown格式交底书")
    # 摘要
    abstract: str = Field(..., description="摘要")
    # 生成时间
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")
    # 迭代次数
    iteration_count: int = Field(default=0, description="迭代次数")
    # 风险等级
    final_risk_level: str = Field(default="low", description="最终风险等级")


# ==================== Token用量统计 ====================
class TokenUsage(BaseModel):
    """全链路Token消耗统计"""
    requirement_prompt: int = Field(default=0, description="需求对接输入Token")
    requirement_completion: int = Field(default=0, description="需求对接输出Token")
    search_prompt: int = Field(default=0, description="检索输入Token")
    search_completion: int = Field(default=0, description="检索输出Token")
    writer_prompt: int = Field(default=0, description="撰写输入Token")
    writer_completion: int = Field(default=0, description="撰写输出Token")
    compliance_prompt: int = Field(default=0, description="合规校验输入Token")
    compliance_completion: int = Field(default=0, description="合规校验输出Token")
    review_prompt: int = Field(default=0, description="评审输入Token")
    review_completion: int = Field(default=0, description="评审输出Token")

    @property
    def total_prompt(self) -> int:
        return (self.requirement_prompt + self.search_prompt +
                self.writer_prompt + self.compliance_prompt + self.review_prompt)

    @property
    def total_completion(self) -> int:
        return (self.requirement_completion + self.search_completion +
                self.writer_completion + self.compliance_completion + self.review_completion)

    @property
    def total_tokens(self) -> int:
        return self.total_prompt + self.total_completion


# ==================== 全局状态（LangGraph State） ====================
class PatentState(BaseModel):
    """
    LangGraph 全局状态对象
    所有Agent共享这一个状态，每个Agent只修改自己负责的字段
    这是多Agent协同的数据流转核心
    """
    # 唯一请求ID
    request_id: str = Field(..., description="请求唯一标识")
    # 用户原始输入
    user_input: str = Field(..., description="用户原始技术方案描述")

    # ---------- 各阶段产出 ----------
    # 需求对接产出
    structured_requirement: Optional[StructuredRequirement] = Field(default=None)
    # 检索产出
    prior_art_report: Optional[PriorArtReport] = Field(default=None)
    # 撰写产出
    draft_docket: Optional[PatentDocket] = Field(default=None)
    # 合规校验产出
    compliance_report: Optional[ComplianceReport] = Field(default=None)
    # 评审产出
    review_result: Optional[ReviewResult] = Field(default=None)
    # 最终文档
    final_document: Optional[FinalDocument] = Field(default=None)

    # ---------- 系统控制字段 ----------
    # 当前迭代次数
    iteration_count: int = Field(default=0, description="当前迭代次数")
    # Token用量统计
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    # 流程日志
    process_logs: List[str] = Field(default_factory=list, description="流程日志")
    # 错误信息
    error_message: Optional[str] = Field(default=None, description="错误信息")