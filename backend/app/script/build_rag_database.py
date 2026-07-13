import sys
from pathlib import Path
BACKEND_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))
import sqlite3
import os
from app.tools.rag_tool import _get_collection, init_bm25_patent_corpus
from app.config import CHROMA_PATENT_COLLECTION

# 与清洗脚本路径保持一致
PATENT_DB_PATH = "D:\Downloads\CN-US-EU-JP-Patent_2020-2025-main\patent_meta.db"
# 每批次插入向量库数量，防止一次性加载5万条爆内存
BATCH_SIZE = 1000

def load_all_patents_from_sqlite():
    """从sqlite读取全部清洗完成专利"""
    conn = sqlite3.connect(PATENT_DB_PATH)
    cur = conn.cursor()
    sql = """
        SELECT patent_number, title, applicant, application_date, abstract, technical_field
        FROM patent_meta
        ORDER BY patent_number
    """
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    print(f"从数据库读取到待入库专利总数：{len(rows)}")
    return rows

def batch_import_to_chroma():
    # 获取Chroma专利集合
    coll = _get_collection(CHROMA_PATENT_COLLECTION)
    if coll is None:
        print("❌ Chroma向量库初始化失败，终止入库")
        return

    all_rows = load_all_patents_from_sqlite()
    total = len(all_rows)
    batch_idx = 0
    # 分批插入，控制内存占用
    for start in range(0, total, BATCH_SIZE):
        end = start + BATCH_SIZE
        batch_rows = all_rows[start:end]
        documents = []
        metadatas = []
        ids = []
        for row in batch_rows:
            patent_num, title, applicant, app_date, abstract, tech_field = row
            # 向量使用摘要做语义检索核心文本
            documents.append(abstract)
            # 元数据完全对齐检索工具读取结构
            meta = {
                "title": title,
                "patent_number": patent_num,
                "applicant": applicant,
                "application_date": app_date,
                "technical_field": tech_field
            }
            metadatas.append(meta)
            ids.append(patent_num)
        # 当前批次入库
        coll.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        batch_idx += 1
        print(f"✅ 已完成第{batch_idx}批入库，当前累计：{min(end, total)}/{total}")

    print(f"\n🎉 Chroma向量库全部入库完成，共{total}条清洗后专利")
    print("开始初始化BM25关键词检索语料库...")
    # 初始化BM25，构建混合检索所需关键词索引
    init_bm25_patent_corpus()
    print("🎉 BM25模型加载完毕，混合检索库构建完成！")
    print("可直接运行eval_retrieval_metric.py计算召回率/精确率")

if __name__ == "__main__":
    batch_import_to_chroma()