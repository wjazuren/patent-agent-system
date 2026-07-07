"""
文档输出 Agent
对应岗位：文档专员
核心职责：
1. 将结构化的交底书转换成标准Markdown格式文档
2. 生成摘要
3. 归档记录
4. 输出最终交付物

设计思路：
- 这是流程的最后一环，负责把各Agent的产出整合成用户可读的最终文档
- 统一文档格式，保证输出规范
- 附带检索报告和风险提示，交付物完整
"""
from __future__ import annotations

import logging
import uuid
from typing import Tuple

from app.models.schemas import (
    FinalDocument,
    PatentDocket,
    PriorArtReport,
    ComplianceReport,
    ReviewResult,
)

logger = logging.getLogger(__name__)


def _generate_markdown(
    docket: PatentDocket,
    prior_art: PriorArtReport,
    compliance: ComplianceReport | None,
    review: ReviewResult | None,
) -> str:
    """
    将结构化数据渲染成标准Markdown格式
    这是最终交付给用户的文档内容
    """
    # 风险等级显示文本
    risk_text_map = {
        "low": "🟢 低风险",
        "medium": "🟡 中风险",
        "high": "🔴 高风险",
    }
    risk_text = risk_text_map.get(prior_art.novelty_risk_level, "未知")

    # 对比专利列表
    prior_patents_md = ""
    if prior_art.prior_patents:
        prior_patents_md = "\n".join([
            f"### {i+1}. {p.title}\n"
            f"- **专利号**：{p.patent_number}\n"
            f"- **申请人**：{p.applicant}\n"
            f"- **申请日**：{p.application_date}\n"
            f"- **相似度**：{p.similarity_score:.1f}%\n"
            f"- **摘要**：{p.abstract}\n"
            for i, p in enumerate(prior_art.prior_patents)
        ])
    else:
        prior_patents_md = "未检索到相关对比专利"

    # 合规问题列表
    compliance_md = ""
    if compliance and compliance.issues:
        compliance_md = "\n".join([
            f"- [{issue.severity.upper()}] {issue.section}：{issue.description}\n  建议：{issue.suggestion}"
            for issue in compliance.issues
        ])
    else:
        compliance_md = "无合规问题"

    md = f"""# {docket.invention_name}

## 一、基本信息
- **技术领域**：{docket.technical_field}
- **新颖性风险评估**：{risk_text}
- **风险说明**：{prior_art.risk_assessment}

---

## 二、技术领域
{docket.technical_field}

---

## 三、背景技术
{docket.background_technology}

---

## 四、发明内容

### 4.1 要解决的技术问题
{docket.technical_problem}

### 4.2 技术方案
{docket.technical_solution}

### 4.3 有益效果
{docket.beneficial_effects}

---

## 五、具体实施方式
{docket.detailed_implementation}

---

## 六、附图说明
{docket.drawing_description if docket.drawing_description else '无'}

---

## 七、权利要求书（初稿）
{docket.claims_draft}

---

## 八、核心术语解释
{chr(10).join(['- ' + term for term in docket.key_terms_explanation]) if docket.key_terms_explanation else '无'}

---

## 附录A：现有技术检索报告

### 检索关键词
{', '.join(prior_art.search_keywords) if prior_art.search_keywords else '无'}

### 对比专利列表
{prior_patents_md}

---

## 附录B：合规校验摘要
- **格式得分**：{compliance.format_score if compliance else 'N/A'}/100
- **公开充分性得分**：{compliance.sufficiency_score if compliance else 'N/A'}/100

### 问题清单
{compliance_md}

---

*本文档由专利交底书多智能体系统自动生成，仅供参考，正式申请请咨询专业专利代理人*
"""
    return md


def output_document_agent(
    docket: PatentDocket,
    prior_art: PriorArtReport,
    compliance_report: ComplianceReport | None,
    review_result: ReviewResult | None,
    iteration_count: int,
) -> Tuple[FinalDocument, dict]:
    """
    生成最终交付文档

    Args:
        docket: 最终交底书
        prior_art: 检索报告
        compliance_report: 合规报告
        review_result: 评审结果
        iteration_count: 迭代次数

    Returns:
        (最终文档对象, Token用量字典)
    """
    logger.info("文档输出Agent开始工作")

    # 生成唯一文档ID
    document_id = f"patent_{uuid.uuid4().hex[:12]}"

    # 生成完整Markdown
    full_markdown = _generate_markdown(docket, prior_art, compliance_report, review_result)

    # 生成摘要（取技术方案前200字）
    abstract = docket.technical_solution[:200] + "..." if len(docket.technical_solution) > 200 else docket.technical_solution

    # 组装最终文档对象
    final_doc = FinalDocument(
        document_id=document_id,
        full_markdown=full_markdown,
        abstract=abstract,
        iteration_count=iteration_count,
        final_risk_level=prior_art.novelty_risk_level,
    )

    logger.info("文档生成完成，文档ID: %s", document_id)
    return final_doc, {"prompt_tokens": 0, "completion_tokens": 0}