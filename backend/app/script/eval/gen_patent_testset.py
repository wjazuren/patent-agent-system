import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

import pandas as pd
from app.tools.llm_tool import _build_chat_llm
from app.tools.rag_tool import GLOBAL_BGE_M3_EMBED
from export_postgres_patent_docs import export_sampled_postgres_patents
from ragas.run_config import RunConfig
# 新版 Ragas (v0.2+) 导入
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.testset import TestsetGenerator
from ragas.testset.synthesizers import SingleHopSpecificQuerySynthesizer

# 1. 抽样 30 篇底料专利
print("正在从 PostgreSQL 中抽样 30 篇专利文档...")
patent_docs = export_sampled_postgres_patents(sample_size=30)

if not patent_docs:
    print("❌ 未导出任何专利文档，请检查 PostgreSQL 专利表！")
    sys.exit(1)

# 补全 Ragas 依赖的 filename 属性，提升构建文档图谱质量
for doc in patent_docs:
    doc.metadata["filename"] = doc.metadata.get("patent_number", "patent_doc")

# 2. 构建 LLM 与 Embedding 包装对象
llm_base = _build_chat_llm()
if llm_base is None:
    print("❌ 大模型未正确配置！")
    sys.exit(1)

generator_llm = LangchainLLMWrapper(llm_base)
generator_embeddings = LangchainEmbeddingsWrapper(GLOBAL_BGE_M3_EMBED)
run_config = RunConfig(
    max_workers=1,         # 降低并发数（默认通常较高），建议设为 1 或 2
    timeout=180,           # 单次请求超时时间（秒）
    max_retries=10,        # 增加重试次数
    max_wait=60            # 两次重试之间的最大等待间隔（秒）
)
# 3. 初始化 TestsetGenerator
generator = TestsetGenerator(
    llm=generator_llm, embedding_model=generator_embeddings
)

# 4. 初始化单跳合成器并配置中文适配
single_hop_synth = SingleHopSpecificQuerySynthesizer(llm=generator_llm)

print("🌐 正在将 Synthesizer 指令适配为中文...")
try:
    prompts = single_hop_synth.get_prompts()
    for key, prompt in prompts.items():
        prompts[key] = prompt.adapt(language="chinese", llm=generator_llm)
    single_hop_synth.set_prompts(prompts)
    print("✅ 中文 Prompt 适配成功！")
except Exception as e:
    print(f"⚠️ 中文适配跳过/失败 (使用默认Prompt): {e}")

# 5. 指定并发生成 20 条测试集
query_dist = [(single_hop_synth, 1.0)]
output_path = Path(__file__).parent / "patent_retrieval_testset.csv"


print("🚀 开始并发生成 20 条中文单条专利测试题...")
try:
    dataset = generator.generate_with_langchain_docs(
        documents=patent_docs,
        testset_size=20,
        query_distribution=query_dist,
        run_config=run_config
    )

    df = dataset.to_pandas()

    if not df.empty:
        # 一次性落盘写入 (utf-8-sig 防止 Excel 打开中文乱码)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(
            f"🎉 20 条测试集生成成功！包含 {len(df)} 条测试用例，保存路径: {output_path}"
        )
    else:
        print("❌ 生成结果为空！")

except Exception as e:
    print(f"❌ 生成过程抛出异常: {e}")
