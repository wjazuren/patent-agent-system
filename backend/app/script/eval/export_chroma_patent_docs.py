"""兼容旧脚本名；数据源已经迁移为 PostgreSQL。"""
try:
    from .export_postgres_patent_docs import export_sampled_postgres_patents
except ImportError:  # 兼容直接运行该文件
    from export_postgres_patent_docs import export_sampled_postgres_patents


def export_sampled_chroma_patents(sample_size: int = 30):
    """兼容旧调用方，实际从 PostgreSQL 抽样。"""
    return export_sampled_postgres_patents(sample_size)


if __name__ == "__main__":
    docs = export_sampled_postgres_patents(sample_size=30)
    print(f"已从 PostgreSQL 抽样 {len(docs)} 篇专利")
