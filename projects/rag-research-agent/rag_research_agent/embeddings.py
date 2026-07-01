from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any

from sentence_transformers import SentenceTransformer


from .chunking import Chunk, chunk_documents
from .documents import load_documents

# 默认embadding后的维度
DEFAULT_EMBEDDING_DIMENSIONS = 128

import os
from sentence_transformers import SentenceTransformer

# 1. 强行把下载渠道切到阿里 ModelScope 镜像，彻底避开 HuggingFace 的网络封锁和 401 报错
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com" 

# 2. 传入一个真正的、体积仅约 100MB、且检索能力极强的工业级中文嵌入模型
model = SentenceTransformer(r"D:\xjbx\Agent-Leanring-Notebook\projects\rag-research-agent\models\bge-small-zh")

class EmbeddingError(ValueError):
    pass

@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """
    表示一段文本的 embedding 结果。

    text_id:
        对于 chunk embedding，这里通常就是 chunk.id。
    vector:
        固定维度的浮点数向量。
    metadata:
        记录 embedding 参数，方便后续 trace / debug。
    """
    text_id: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


def l2_normalize(vector: list[float])->list[float]:
    """
    对向量做 L2 归一化。

    归一化后，后续 cosine similarity 可以直接用 dot product 计算。
    """
    norm = math.sqrt(sum(value * value for value in vector))

    if norm == 0:
        return vector
    
    return [value / norm for value in vector]

def stable_token_hash(token: str) -> bytes:
    """
    为 token 生成稳定 hash。

    不能用 Python 内置 hash()，因为它在不同进程中可能不稳定。
    """

    return hashlib.sha256(token.encode("utf-8")).digest()


def embed_text_bge_micro(text: str) -> list[float]:
    # 内部自动生成生产级 BERT 语义向量并进行 L2 归一化
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()

def embed_chunk(
    chunk: Chunk,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
) -> EmbeddingResult:
    """
    为单个 Chunk 生成 embedding。
    """

    return EmbeddingResult(
        text_id=chunk.id,
        vector=embed_text_bge_micro(chunk.text),
        metadata={
            "dimensions": dimensions,
            "source_name": chunk.metadata["source_name"],
            "document_id": chunk.document_id,
        },
    )

def embed_chunks(
    chunks: list[Chunk],
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
) -> list[EmbeddingResult]:
    """
    批量为 Chunk 生成 embedding。
    """

    return [
        embed_chunk(chunk, dimensions=dimensions)
        for chunk in chunks
    ]

if __name__ == "__main__":
    documents = load_documents(r"D:\xjbx\Agent-Leanring-Notebook\projects\rag-research-agent\data\raw")
    chunks = chunk_documents(documents=documents)

    embeddings = embed_chunks(chunks=chunks)

    for item in embeddings:
        print(item.text_id, len(item.vector), item.vector[:5])