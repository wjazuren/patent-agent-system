import sys
from pathlib import Path
BACKEND_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))
import numpy as np
from app.tools.rag_tool import search_prior_art_hybrid
import json

def calculate_recall_precision(
    pred_patents: list[dict],
    gt_patent_nums: list[str]
) -> tuple[float, float]:
    """
    单条Query计算 Recall@K / Precision@K
    :param pred_patents: 混合检索+Reranker输出Top-K专利列表
    :param gt_patent_nums: 人工标注真实相关专利号集合(Ground Truth)
    :return: 单条召回率, 单条精确率
    """
    # 1. 提取检索结果里所有专利号
    pred_ids = {item["patent_number"] for item in pred_patents}
    # 2. 真实相关专利集合
    gt_ids = set(gt_patent_nums)
    # 3. 交集：检索出来且真实相关的专利数量 TP
    tp = len(pred_ids & gt_ids)
    total_gt = len(gt_ids)
    total_pred = len(pred_ids)

    # 防除0，避免无GT时报错
    recall = tp / total_gt if total_gt > 0 else 0.0
    precision = tp / total_pred if total_pred > 0 else 0.0

    return round(recall, 4), round(precision, 4)


def batch_evaluate_retrieval(test_queries: list[dict]) -> tuple[float, float]:
    """
    批量评测整个测试集，输出全局平均Recall、平均Precision
    :param test_queries: 测试集格式示例
        [
            {
                "query": "用户技术方案描述",
                "gt_patents": ["CN119472657", "CN116127678A"]
            }
        ]
    :return: 全局平均召回率、全局平均精确率
    """
    all_recall = []
    all_precision = []

    for sample in test_queries:
        query_text = sample["query"]
        gt_list = sample["gt_patents"]
        # 执行完整混合检索：BM25+Chroma粗召回 + Reranker精排
        pred_result, _ = search_prior_art_hybrid(query_text)
        # 计算单条指标
        r, p = calculate_recall_precision(pred_result, gt_list)
        all_recall.append(r)
        all_precision.append(p)
        print(f"【Query】{query_text[:40]}... | Recall={r:.2%}, Precision={p:.2%}")

    # 全部样本取算术平均，得到整体指标
    avg_recall = float(np.mean(all_recall))
    avg_precision = float(np.mean(all_precision))
    print("\n==================== 批量评测汇总 ====================")
    print(f"测试样本总量：{len(test_queries)}")
    print(f"全局平均召回率Recall@5 = {avg_recall * 100:.1f}%")
    print(f"全局平均精确率Precision@5 = {avg_precision * 100:.1f}")
    return avg_recall, avg_precision


def load_test_json(file_path: str = "data/auto_test_dataset.json") -> list[dict]:
    """从自动生成的json文件加载测试数据集"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"成功读取测试集文件：{file_path}，共{len(data)}条样本")
        return data
    except FileNotFoundError:
        print(f"警告：未找到文件 {file_path}，将使用代码内置少量测试样例")
        return []


if __name__ == "__main__":
    # 方式1：优先读取自动生成的伪GT测试集json文件
    test_dataset = load_test_json("data/llm_auto_test_dataset.json")

    

    # 执行评测
    mean_recall, mean_prec = batch_evaluate_retrieval(test_dataset)