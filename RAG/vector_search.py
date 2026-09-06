# 主要作用：将用户问题向量化，并从制度向量索引中检索最相关的制度切片。

from pathlib import Path
import json
import math
import re
import ssl
import sys
import urllib.request
import urllib.error

import certifi
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
VECTOR_INDEX_PATH = ROOT_DIR / "RAG/vector_index.json"

MODEL = "text-embedding-v3"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"


def read_api_key():
    try:
        return st.secrets["DASHSCOPE_API_KEY"]
    except (FileNotFoundError, KeyError):
        pass

    env = {}

    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            env[key] = value.strip()

    return env["DASHSCOPE_API_KEY"]


def embed_query(query):
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "input": [query],
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {read_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, context=ssl_context, timeout=12) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["data"][0]["embedding"]


def cosine_similarity(vector_a, vector_b):
    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    norm_a = math.sqrt(
        sum(value * value for value in vector_a)
    )

    norm_b = math.sqrt(
        sum(value * value for value in vector_b)
    )

    return dot_product / (norm_a * norm_b)


def _result_from_chunk(chunk, rank, score):
    return {
        "rank": rank,
        "score": round(score, 6),
        "chunk_id": chunk["chunk_id"],
        "source_file": chunk["source_file"],
        "article": chunk["article"],
        "article_title": chunk["article_title"],
        "page_start": chunk["page_start"],
        "page_end": chunk["page_end"],
        "text": chunk["text"],
    }


def keyword_search(query, top_k=5):
    """在向量接口不可达时，使用本地制度切片提供可追溯的降级检索。"""
    vector_index = json.loads(
        VECTOR_INDEX_PATH.read_text(encoding="utf-8")
    )
    raw_terms = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]+", query)
    terms = []
    for term in raw_terms:
        term = term.lower()
        if term in {"制度", "请问", "哪些", "什么"}:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", term):
            terms.extend(term[index:index + 2] for index in range(len(term) - 1))
        else:
            terms.append(term)

    ranked = []
    for chunk in vector_index["chunks"]:
        text = chunk["text"].lower()
        score = sum(text.count(term) for term in terms)
        if score:
            ranked.append((score, chunk))

    ranked.sort(key=lambda item: (-item[0], item[1]["source_file"], item[1]["chunk_id"]))
    return [
        _result_from_chunk(chunk, index, score)
        for index, (score, chunk) in enumerate(ranked[:top_k], start=1)
    ]


def search(query, top_k=5):
    vector_index = json.loads(
        VECTOR_INDEX_PATH.read_text(encoding="utf-8")
    )

    try:
        query_vector = embed_query(query)
    except (urllib.error.URLError, TimeoutError, OSError):
        return keyword_search(query, top_k=top_k)
    ranked = []

    for chunk in vector_index["chunks"]:
        score = cosine_similarity(
            query_vector,
            chunk["embedding"],
        )
        ranked.append((score, chunk))

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1]["source_file"],
            item[1]["chunk_id"],
        )
    )

    return [
        _result_from_chunk(chunk, index, score)
        for index, (score, chunk) in enumerate(ranked[:top_k], start=1)
    ]


def main():
    query = " ".join(sys.argv[1:])
    results = search(query)

    print(json.dumps(
        results,
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
