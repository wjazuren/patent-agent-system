from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import context_precision, context_recall
from tqdm import tqdm

# 从 app.llm_tool 和 rag_tool 引入 LLM 和混合检索接口
from app.tools.llm_tool import _build_chat_llm
from app.tools.rag_tool import search_prior_art
from ragas.run_config import RunConfig

def run_retrieval_eval():
    csv_path = (
        Path(__file__).parent / "patent_retrieval_testset.csv"
    )  # 推荐使用相对路径避免路径报错
    df = pd.read_csv(csv_path)

    eval_samples = []

    for _, row in tqdm(df.iterrows(), total=len(df)):
        # 字段映射（适应 Ragas v0.2+ 导出的列名）
        query = row["user_input"]
        gt_answer = row["reference"]

        # 解析标准上下文列表 reference_contexts
        gold_raw = row["reference_contexts"]
        if isinstance(gold_raw, str):
            try:
                gold_contexts = eval(gold_raw)
            except Exception:
                gold_contexts = [gold_raw]
        else:
            gold_contexts = gold_raw

        # 调用你的混合检索：向量 + BM25 + 重排
        retrieval_res, _ = search_prior_art(query)

        # 提取检索结果中的摘要
        pred_contexts = [item["abstract"] for item in retrieval_res]

        eval_samples.append({
            "user_input": query,
            "reference": gt_answer,
            "reference_contexts": gold_contexts,
            "retrieved_contexts": pred_contexts,
        })

    eval_ds = Dataset.from_list(eval_samples)

    # 评估 LLM 准备
    eval_llm = _build_chat_llm()
    run_config = RunConfig(
        max_workers=1,       # 👈 限制并发线程数为 2（可设为 1 纯单线程）
        max_retries=10,      # 👈 遇到 API 限流时自动重试 10 次
        max_wait=60,         # 👈 重试最大等待间隔（秒）
    )

    # 计算 Context Recall 和 Context Precision 指标
    result = evaluate(
        eval_ds,
        metrics=[context_recall, context_precision],
        llm=eval_llm,  # 传入你的 LLM 进行语义判定
        run_config=run_config,
    )

    print("=" * 50)
    print("🎉 专利混合检索评测结果：")
    print(result)
    print("=" * 50)


if __name__ == "__main__":
    run_retrieval_eval()