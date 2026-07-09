from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .chunking import Chunk, chunk_documents
from .documents import load_documents

# 默认embadding后的维度
DEFAULT_EMBEDDING_DIMENSIONS = 128

import os

# 1. 强行把下载渠道切到阿里 ModelScope 镜像，彻底避开 HuggingFace 的网络封锁和 401 报错
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com" 

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "bge-small-zh"
_MODEL: Any | None = None
_MODEL_LOAD_FAILED = False

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

def tokenize(text: str) -> list[str]:
    """
    简单分词函数。

    当 sentence-transformers 不可用时，使用它生成可复现的 hash embedding。
    """

    return re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text.lower())


def embed_text_hash(
    text: str,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
) -> list[float]:
    """
    备用 embedding 实现。

    它不具备真正语义理解能力，但足够让 CLI 和检索链路在无外部依赖时跑通。
    """

    if dimensions <= 0:
        raise EmbeddingError("dimensions must be greater than 0.")

    tokens = tokenize(text)
    if not tokens:
        raise EmbeddingError("Cannot embed empty text.")

    vector = [0.0] * dimensions
    for token in tokens:
        digest = stable_token_hash(token)
        index = int.from_bytes(digest[:4], byteorder="big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    return l2_normalize(vector)


def get_embedding_model() -> Any | None:
    """
    延迟加载本地 BGE 模型。

    如果当前环境没有 sentence_transformers，返回 None，让调用方使用备用 hash embedding。
    """

    global _MODEL, _MODEL_LOAD_FAILED

    if _MODEL is not None:
        return _MODEL

    if _MODEL_LOAD_FAILED:
        return None

    try:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer(str(MODEL_PATH))
    except Exception:
        _MODEL_LOAD_FAILED = True
        return None

    return _MODEL


def embed_text_bge_micro(text: str) -> list[float]:
    """
    优先使用本地 BGE 模型生成向量。

    如果依赖或模型不可用，自动回退到 hash embedding，保证学习项目的 CLI 可运行。
    """

    model = get_embedding_model()

    if model is None:
        return embed_text_hash(text)

    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()

def embed_chunk(
    chunk: Chunk,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
) -> EmbeddingResult:
    """
    为单个 Chunk 生成 embedding。
    """
    vector=embed_text_bge_micro(chunk.text)
    return EmbeddingResult(
        text_id=chunk.id,
        vector=vector,
        metadata={
            "dimensions": len(vector),
            "source_name": chunk.metadata.get("source_name"),
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
