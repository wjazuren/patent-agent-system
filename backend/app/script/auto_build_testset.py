import sys
import json
import sqlite3
from pathlib import Path

BACKEND_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# 复用你交底书系统中已有的纯文本大模型调用工具
from app.tools.llm_tool import call_llm_text

# 你的数据库路径
PATENT_DB_PATH = r"D:\Downloads\CN-US-EU-JP-Patent_2020-2025-main\patent_meta.db"

# 设定大模型的系统提示词，让它扮演研发工程师
SYSTEM_PROMPT = """
你现在扮演一名企业的研发工程师。你有一个技术灵感准备申请专利，但你不太懂专业的专利术语。
现在我会给你一段正式的【专利摘要】，请你“反向”将其改写成一段【口语化的技术方案描述】。

改写要求：
1. 语言要非常自然、口语化，就像你口头向专利代理人陈述你的需求一样。
2. 描述你要解决的痛点/问题，以及你的核心解决思路。
3. 绝对不要直接照抄原摘要，请用通俗的大白话重新组织。
4. 字数控制在 100 - 300 字之间。
5. 直接输出你的口语化描述，不要包含任何前缀（如“好的”、“这是描述”等）或多余的话。
"""

def generate_llm_test_set(sample_count=100, output_path="data/llm_auto_test_dataset.json"):
    """使用大模型反向生成真实的测试集"""
    # 1. 随机从数据库抽取专利
    conn = sqlite3.connect(PATENT_DB_PATH)
    cur = conn.cursor()
    # 随机抽取样本
    cur.execute("SELECT patent_number, title, abstract FROM patent_meta ORDER BY RANDOM() LIMIT ?", (sample_count,))
    rows = cur.fetchall()
    conn.close()

    test_data = []
    print(f"开始使用大模型反向生成 {sample_count} 条测试集，请耐心等待...")

    # 2. 遍历调用大模型
    for i, (pat_num, title, abstract) in enumerate(rows):
        human_prompt = f"原专利名称：{title}\n原专利摘要：{abstract}\n\n请输出口语化的技术描述："
        
        # 调用大模型 (传入系统提示词和用户提示词)
        result_text, _ = call_llm_text(system_prompt=SYSTEM_PROMPT, human_prompt=human_prompt)
        
        if result_text:
            test_data.append({
                "query": result_text.strip(),
                "gt_patents": [pat_num], # 唯一客观的 Ground Truth 就是这篇专利本身
                "origin_title": title    # 存下来方便人眼抽查核对
            })
            print(f"[{i+1}/{sample_count}] 成功生成: {pat_num} - {title}")
        else:
            print(f"[{i+1}/{sample_count}] ❌ 生成失败: {pat_num}")

    # 3. 写入 JSON 文件
    output_file = Path(BACKEND_ROOT) / output_path
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ 测试集生成完毕！成功生成 {len(test_data)} 条样本，已保存至 {output_path}")

if __name__ == "__main__":
    # 建议先跑 50 条测试一下，因为调大模型需要一些时间
    generate_llm_test_set(sample_count=5)