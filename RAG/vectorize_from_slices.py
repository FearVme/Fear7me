# 主要作用：读取 RAG/切片 下的制度切片，调用百炼 text-embedding-v3 生成向量索引。

from pathlib import Path
import json
import urllib.request


ROOT_DIR = Path(__file__).resolve().parent.parent
SLICE_DIR = ROOT_DIR / "RAG/切片"
OUTPUT_PATH = ROOT_DIR / "RAG/vector_index.json"
ENV_PATH = ROOT_DIR / ".env"

MODEL = "text-embedding-v3"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
BATCH_SIZE = 8


def read_api_key():
    env = {}

    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            env[key] = value.strip()

    return env["DASHSCOPE_API_KEY"]


def read_chunks():
    chunks = []

    for path in sorted(SLICE_DIR.glob("*.json")):
        records = json.loads(path.read_text(encoding="utf-8"))

        for record in records:
            chunks.append(
                {
                    "chunk_id": record["chunk_id"],
                    "source_file": record["source_file"],
                    "source_path": str(path.relative_to(ROOT_DIR)),
                    "title": record["title"],
                    "version": record["version"],
                    "chapter": record.get("chapter"),
                    "chapter_title": record.get("chapter_title"),
                    "article": record.get("article"),
                    "article_title": record.get("article_title"),
                    "section_type": record["section_type"],
                    "text": record["text"],
                    "page_start": record["page_start"],
                    "page_end": record["page_end"],
                    "page_source": record["page_source"],
                    "chunk_order": record["chunk_order"],
                    "chunk_total": record["chunk_total"],
                }
            )

    chunks.sort(
        key=lambda item: (
            item["source_file"],
            item["chunk_order"],
        )
    )

    return chunks


def embed_batch(texts, api_key):
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "input": texts,
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    data = sorted(
        result["data"],
        key=lambda item: item["index"],
    )

    return [
        item["embedding"]
        for item in data
    ]


def main():
    chunks = read_chunks()
    api_key = read_api_key()
    vector_chunks = []

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        texts = [chunk["text"] for chunk in batch]
        vectors = embed_batch(texts, api_key)

        for chunk, vector in zip(batch, vectors):
            vector_chunks.append(
                {
                    **chunk,
                    "embedding": vector,
                }
            )

        print(f"embedded={len(vector_chunks)}/{len(chunks)}")

    vector_index = {
        "schema_version": "1.0",
        "model": MODEL,
        "source": "RAG/切片",
        "chunk_count": len(vector_chunks),
        "chunks": vector_chunks,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            vector_index,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"source_files={len(set(item['source_file'] for item in chunks))}")
    print(f"chunks={len(vector_chunks)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()