# 主要作用：调用向量检索器获取制度证据，再使用百炼 qwen-plus 生成带引用的回答。

from pathlib import Path
import json
import ssl
import sys
import urllib.request
import urllib.error

import certifi

from RAG.vector_search import search


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

MODEL = "qwen-plus"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def read_api_key():
    # 优先读取 Streamlit Cloud Secrets，本地开发时回退到 .env
    if "DASHSCOPE_API_KEY" in st.secrets:
        return st.secrets["DASHSCOPE_API_KEY"]

    env = {}

    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            env[key] = value.strip()

    return env["DASHSCOPE_API_KEY"]


def build_evidence(results):
    evidence = []

    for item in results:
        article = item["article"] or "附件或流程"
        pages = f"{item['page_start']}-{item['page_end']}页"

        evidence.append(
            f"[{item['chunk_id']}] "
            f"{item['source_file']}，第{article}条，{pages}\n"
            f"{item['text']}"
        )

    return "\n\n".join(evidence)


def fallback_answer(question, results):
    """返回本地切片证据，保证外部生成接口暂时不可达时仍可问答。"""
    if not results:
        return (
            "当前未从本地制度知识库检索到与问题直接匹配的条款，"
            "请换一种问法重试。"
        )

    excerpts = []
    for item in results[:3]:
        excerpts.append(
            f"[{item['chunk_id']}] {item['source_file']}，第{item['page_start']}-{item['page_end']}页\n"
            f"{item['text']}"
        )

    return (
        "当前已切换到本地制度检索模式，以下为制度知识库检索到的原文依据。\n\n"
        + "\n\n".join(excerpts)
        + "\n\n以上内容来自本地制度切片，请以标注的制度原文为准。"
    )


def ask(question):
    results = search(question, top_k=5)
    evidence = build_evidence(results)

    prompt = f"""
你是工程设计变更制度问答助手。

只能依据下面提供的制度证据回答问题。
不得补充证据之外的制度内容。
如果证据不足，请回答“现有制度切片无法确认”。
回答必须引用证据编号，例如 [02-0022]。

问题：
{question}

制度证据：
{evidence}
"""

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "你负责基于制度证据进行准确、可追溯的中文回答。",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0,
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {read_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(request, context=ssl_context, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
    ):
        return fallback_answer(question, results), results

    return result["choices"][0]["message"]["content"], results


def main():
    question = " ".join(sys.argv[1:])
    answer, evidence = ask(question)

    print("回答：")
    print(answer)

    print("\n引用证据：")
    for item in evidence:
        print(
            f"- {item['chunk_id']} | "
            f"{item['source_file']} | "
            f"第{item['page_start']}-{item['page_end']}页"
        )


if __name__ == "__main__":
    main()
