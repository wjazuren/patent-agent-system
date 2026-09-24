"""从 PostgreSQL 随机抽样父专利，用于生成 Ragas 测试集。"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from langchain_core.documents import Document

BACKEND_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.db.repositories import fetch_all_patents


def export_sampled_postgres_patents(sample_size: int = 30):
    patents = fetch_all_patents()
    docs = [
        Document(
            page_content=item["abstract"],
            metadata={
                "patent_id": item["patent_number"],
                "patent_number": item["patent_number"],
                "title": item["title"],
                "applicant": item["applicant"],
                "technical_field": item["technical_field"],
            },
        )
        for item in patents
    ]
    print(f"PostgreSQL 父专利总数：{len(docs)}")
    if len(docs) > sample_size:
        random.seed(42)
        docs = random.sample(docs, sample_size)
    return docs


if __name__ == "__main__":
    patent_docs = export_sampled_postgres_patents(sample_size=30)
    with open("postgres_patent_docs.json", "w", encoding="utf-8") as file:
        json.dump(
            [{"content": doc.page_content, "meta": doc.metadata} for doc in patent_docs],
            file,
            ensure_ascii=False,
            indent=2,
        )
    print("抽样完成，已导出至 postgres_patent_docs.json")
