"""
统一评分规则工具
合规校验与质量评审复用同一套扣分标准
保证判定口径一致，避免标准偏差导致的无效迭代
"""
from __future__ import annotations
from typing import List
from app.models.schemas import ComplianceIssue

# 不同严重等级对应扣分值
SEVERITY_DEDUCTION = {
    "critical": 10.0,
    "major": 3.0,
    "minor": 0.5,
}

def calculate_compliance_score(issues: List[ComplianceIssue]) -> float:
    """
    根据合规问题列表计算合规得分（满分100）
    合规Agent和评审Agent都使用此函数，保证标准统一
    """
    total_deduction = 0.0
    for issue in issues:
        total_deduction += SEVERITY_DEDUCTION.get(issue.severity, 1.0)
    return max(0.0, 100.0 - total_deduction)

def judge_compliance_pass(issues: List[ComplianceIssue]) -> bool:
    """
    统一判定合规是否通过
    规则：无critical级问题，且major级不超过2个
    """
    critical_count = sum(1 for i in issues if i.severity == "critical")
    major_count = sum(1 for i in issues if i.severity == "major")
    return critical_count == 0 and major_count <= 2