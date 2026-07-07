"""
知识库初始化脚本 init_knowledge_base.py
运行一次即可，将示例专利和模板导入向量库
"""
import os
import sys
from pathlib import Path
BACKEND_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.tools.rag_tool import _get_collection
from app.config import (
    CHROMA_PATENT_COLLECTION,
    CHROMA_TEMPLATE_COLLECTION,
    CHROMA_RULES_COLLECTION,
)


def init_patent_collection():
    """初始化专利示例库"""
    collection = _get_collection(CHROMA_PATENT_COLLECTION)
    if collection is None:
        print("❌ 向量库不可用")
        return

    # 示例专利数据（实际项目中可替换为真实专利数据）
    sample_patents = [
        {
            "title": "一种基于大语言模型的智能问答方法及系统",
            "patent_number": "CN116127678A",
            "applicant": "某科技公司",
            "application_date": "2023-01-15",
            "technical_field": "人工智能",
            "abstract": """本发明公开了一种基于大语言模型的智能问答方法，包括：接收用户问题，对问题进行语义理解和意图识别，
            从知识库中检索相关文档片段，将问题与检索结果输入大语言模型生成答案，对答案进行事实校验和安全过滤后返回给用户。
            本发明提高了问答系统的准确性和安全性。""",
        },
        {
            "title": "一种向量检索优化方法及装置",
            "patent_number": "CN115878965A",
            "applicant": "某大数据公司",
            "application_date": "2022-09-20",
            "technical_field": "大数据处理",
            "abstract": """本发明公开了一种向量检索优化方法，通过对向量索引进行分层构建，结合查询向量的动态权重调整，
            在保证检索精度的同时大幅提升检索速度。本发明适用于大规模向量数据库的快速检索场景。""",
        },
        # 可以继续添加更多示例专利...
    ]

    documents = [p["abstract"] for p in sample_patents]
    metadatas = [{k: v for k, v in p.items() if k != "abstract"} for p in sample_patents]
    ids = [p["patent_number"] for p in sample_patents]

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"✅ 专利库初始化完成，共 {len(sample_patents)} 篇示例专利")


def init_template_collection():
    """初始化专利模板库"""
    collection = _get_collection(CHROMA_TEMPLATE_COLLECTION)
    if collection is None:
        return

    templates = [
        """【优秀专利模板 - 人工智能领域】
发明名称：一种基于XXX的YYY方法及系统

技术领域
本发明涉及人工智能技术领域，尤其涉及...

背景技术
随着人工智能技术的发展，...现有技术存在以下问题：1.... 2.... 因此，亟需一种新的技术方案来解决上述问题。

发明内容
本发明要解决的技术问题是...
为解决上述技术问题，本发明的技术方案如下...
本发明的有益效果包括：1.... 2.... 3....

具体实施方式
下面结合具体实施例对本发明的技术方案进行详细说明...
""",
        # 更多模板...
    ]

    collection.add(
        documents=templates,
        ids=[f"template_{i}" for i in range(len(templates))],
    )
    print(f"✅ 模板库初始化完成，共 {len(templates)} 个模板")


def init_rules_collection():
    """初始化审查规范库"""
    collection = _get_collection(CHROMA_RULES_COLLECTION)
    if collection is None:
        return

    rules = [
        "专利法第二十六条第三款：说明书应当对发明或者实用新型作出清楚、完整的说明，以所属技术领域的技术人员能够实现为准。",
        "专利法实施细则第二十条：权利要求书应当有独立权利要求，也可以有从属权利要求。独立权利要求应当从整体上反映发明或者实用新型的技术方案，记载解决技术问题的必要技术特征。",
        "专利审查指南：说明书公开充分，是指所属技术领域的技术人员能够实现该发明或者实用新型的技术方案，解决其技术问题，并且产生预期的技术效果。",
        # 更多规范...
    ]

    collection.add(
        documents=rules,
        ids=[f"rule_{i}" for i in range(len(rules))],
    )
    print(f"✅ 规范库初始化完成，共 {len(rules)} 条规范")


if __name__ == "__main__":
    print("开始初始化知识库...")
    init_patent_collection()
    init_template_collection()
    init_rules_collection()
    print("知识库初始化完成！")