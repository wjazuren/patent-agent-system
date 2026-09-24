"""初始化 PostgreSQL/pgvector 示例专利、模板和审查规范。"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.db.postgres import init_database
from app.db.repositories import upsert_knowledge_documents, upsert_patent_batch
from app.tools.rag_tool import embed_documents, init_bm25_patent_corpus


def init_patents() -> None:
    samples = [
        {
            "title": "一种基于大语言模型的智能问答方法及系统",
            "patent_number": "CN116127678A",
            "applicant": "某科技公司",
            "application_date": "2023-01-15",
            "technical_field": "人工智能",
            "abstract": "本发明公开了一种基于大语言模型的智能问答方法，包括接收用户问题，对问题进行语义理解和意图识别，从知识库中检索相关文档片段，将问题与检索结果输入大语言模型生成答案。",
        },
        {
            "title": "一种向量检索优化方法及装置",
            "patent_number": "CN115878965A",
            "applicant": "某大数据公司",
            "application_date": "2022-09-20",
            "technical_field": "大数据处理",
            "abstract": "本发明公开了一种向量检索优化方法，通过对向量索引进行分层构建，结合查询向量的动态权重调整，在保证检索精度的同时提升检索速度。",
        },
    ]
    for item in samples:
        item["chunks"] = [item["abstract"]]
        item["embeddings"] = embed_documents(item["chunks"])
    count, chunks = upsert_patent_batch(samples)
    print(f"示例专利初始化完成：{count} 篇，{chunks} 个 Chunk")


def init_knowledge() -> None:
    templates = ["""【优秀专利模板 - 人工智能领域】
发明名称：一种基于XXX的YYY方法及系统
技术领域：本发明涉及人工智能技术领域。
背景技术：现有技术存在以下问题。
发明内容：本发明要解决的技术问题是；为解决上述问题，技术方案如下。
具体实施方式：下面结合具体实施例详细说明。"""]
    rules = [
        "专利法第二十六条第三款：说明书应当对发明或者实用新型作出清楚、完整的说明，以所属技术领域的技术人员能够实现为准。",
        "权利要求书应当有独立权利要求，也可以有从属权利要求。独立权利要求应当从整体上反映技术方案，记载解决技术问题的必要技术特征。",
        "说明书公开充分，是指所属技术领域的技术人员能够实现该技术方案、解决其技术问题并产生预期技术效果。",
    ]
    upsert_knowledge_documents(
        "template", templates, ["template_0"], embed_documents(templates)
    )
    upsert_knowledge_documents(
        "rule", rules, [f"rule_{i}" for i in range(len(rules))], embed_documents(rules)
    )
    print(f"模板与规范初始化完成：{len(templates)} 个模板，{len(rules)} 条规范")


if __name__ == "__main__":
    init_database()
    init_patents()
    init_knowledge()
    init_bm25_patent_corpus(force=True)
