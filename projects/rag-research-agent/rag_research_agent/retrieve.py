from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .chunking import Chunk
from .embeddings import embed_text_bge_micro
from .index import VectorIndex


DEFAULT_TOP_K = 3
DEFAULT_MIN_SCORE = 0.25


class RetrievalError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """
    表示一次检索命中的结果。

    rank:
        当前结果在 top-k 中的排名，从 1 开始。
    chunk:
        被检索命中的 Chunk。
    score:
        query vector 与 chunk vector 的相似度分数。
    metadata:
        记录调试信息，后续 trace 可以直接使用。
    """

    rank: int
    chunk: Chunk
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

def dot_product(left: list[float], right: list[float]) -> float:
    """
    计算两个向量的点积
    """

    return sum(a * b for a, b in zip(left, right))


def l2_norm(vector: list[float]) -> float:
    """
    计算向量的 L2 范数。
    """

    return math.sqrt(sum(value * value for value in vector))

def cosine_similarity(left: list[float], right: list[float]) -> float:
    """
    计算 cosine similarity。

    如果 embedding 已经 normalize_embeddings=True，
    理论上 dot product 就等于 cosine similarity。
    这里仍然写完整 cosine，方便兼容未来没有归一化的 embedding。
    """
    if len(left) != len(right):
        raise RetrievalError(
            f"Vector dimensions do not match: {len(left)} != {len(right)}"
        )

    left_norm = l2_norm(left)
    right_norm = l2_norm(right)

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot_product(left, right) / (left_norm * right_norm)

def validate_retrieval_args(top_k: int, min_score: float) -> None:
    """
    校验检索参数。
    """

    if top_k <= 0:
        raise RetrievalError("top_k must be greater than 0.")

    if min_score < -1.0 or min_score > 1.0:
        raise RetrievalError("min_score must be between -1.0 and 1.0.")
    

def retrieve_by_vector(
    query_vector: list[float],
    index: VectorIndex,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_SCORE,
) -> list[RetrievalResult]:
    """
    使用 query vector 在 VectorIndex 中检索 top-k chunks。

    这个函数不负责生成 query embedding，只负责相似度搜索。
    """

    validate_retrieval_args(top_k=top_k, min_score=min_score)

    scored_items: list[tuple[str, float]] = []

    for chunk_id in index.chunk_ids():
        chunk_vector = index.get_vector(chunk_id=chunk_id)

        if chunk_vector is None:
            continue

        score = cosine_similarity(query_vector, chunk_vector)

        if score >= min_score:
            scored_items.append((chunk_id, score))

    
    # 分数从高到低排序；分数相同时按 chunk_id 排序，保证结果稳定。
    scored_items.sort(key=lambda item: (-item[1], item[0]))

    results: list[RetrievalResult] = []

    for rank, (chunk_id, score) in enumerate(scored_items[:top_k], start=1):
        chunk = index.get_chunk(chunk_id=chunk_id)

        if chunk is None:
            continue

        results.append(
            RetrievalResult(
                rank=rank,
                chunk=chunk,
                score=score,
                metadata={
                    "chunk_id": chunk_id,
                    "source_name": chunk.metadata.get("source_name"),
                    "document_id": chunk.document_id,
                },
            )
        )

    return results


def retrieve(
        query: str, 
        index: VectorIndex,
        top_k: int = DEFAULT_TOP_K,
        min_score: float = DEFAULT_MIN_SCORE,
) -> list[RetrievalResult]:
    
    """
    用户查询入口。

    输入自然语言 query，内部先生成 query embedding，
    再调用 retrieve_by_vector() 返回 top-k chunks。
    """

    query = query.strip()

    if not query:
        raise RetrievalError("query must not be empty.")
    
    query_vector = embed_text_bge_micro(query)

    return retrieve_by_vector(
        query_vector=query_vector,
        index=index,
        top_k=top_k,
        min_score=min_score,
    )


if __name__ == "__main__":
    from .documents import load_documents
    from .index import build_index_from_documents

    documents = load_documents(r"D:\xjbx\Agent-Leanring-Notebook\projects\rag-research-agent\data\raw")

    index = build_index_from_documents(documents=documents, chunk_size=300, chunk_overlap=50)

    results = retrieve("What is Retrieval Augmented Generation?", index, top_k=3, min_score=0.1)

    for result in results:
        print(f"rank> {result.rank}  score> {result.score}  chunk_id> {result.chunk.id}")
        print(f"text> {result.chunk.text}")
        print()
