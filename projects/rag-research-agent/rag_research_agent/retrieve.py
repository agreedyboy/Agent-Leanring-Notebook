from __future__ import annotations

import math
import re
from collections import Counter


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


def validate_hybrid_weights(vector_weight: float, lexical_weight: float) -> None:
    """Keep hybrid scores on the same scale as the configured min_score."""

    if vector_weight < 0 or lexical_weight < 0:
        raise RetrievalError("Hybrid retrieval weights must be non-negative.")

    if not math.isclose(vector_weight + lexical_weight, 1.0, abs_tol=1e-9):
        raise RetrievalError(
            "vector_weight and lexical_weight must add up to 1.0."
        )
    

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

def tokenize_for_retrieval(text: str) -> list[str]:
    """
    Tokenize text for lexical retrieval.

    英文按单词切分，中文按单字切分。这个 tokenizer 不追求复杂 NLP，
    只用于 BM25-lite 的关键词匹配。
    """

    return re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text.lower())


def build_bm25_stats(chunks: list[Chunk]) -> dict:
    """
    Build corpus-level statistics needed by BM25-lite.

    BM25 不只看某个词在当前 chunk 出现几次，还需要知道：
    - 这个词出现在多少个 chunks 中，也就是 document frequency / df。
    - 每个 chunk 的长度。
    - 所有 chunks 的平均长度，用于惩罚过长 chunk。
    """

    tokenized_chunks = {}
    document_frequency = Counter()
    chunk_lengths = {}

    for chunk in chunks:
        tokens = tokenize_for_retrieval(chunk.text)
        tokenized_chunks[chunk.id] = tokens
        chunk_lengths[chunk.id] = len(tokens)

        # df 统计的是“这个 token 出现于多少个 chunks”，不是总出现次数。
        # 因此同一个 chunk 内重复出现多次也只给 df 加 1。
        for token in set(tokens):
            document_frequency[token] += 1

    avg_doc_length = (
        sum(chunk_lengths.values()) / len(chunk_lengths)
        if chunk_lengths
        else 0.0
    )

    return {
        "tokenized_chunks": tokenized_chunks,
        "document_frequency": document_frequency,
        "chunk_lengths": chunk_lengths,
        "avg_doc_length": avg_doc_length,
        "document_count": len(chunks),
    }

def bm25_lite_score(
        query: str,
        chunk: Chunk,
        stats: dict,
        k1: float = 1.5,
        b: float = 0.75,
) -> float:
    """
    Compute a simplified BM25 lexical relevance score for one chunk.

    直觉：
    - query 词命中当前 chunk，分数上升。
    - 越稀有的词，idf 越高，对分数贡献越大。
    - 同一个词重复出现会提高分数，但不会无限线性增长。
    - chunk 越长，越容易碰巧命中关键词，因此会做长度归一化。

    k1:
        控制 term frequency 饱和速度，常见默认值约为 1.2-2.0。
    b:
        控制长度惩罚强度，0 表示不惩罚长度，1 表示完全按长度归一化。
    """

    query_tokens = tokenize_for_retrieval(query)
    chunk_tokens = stats["tokenized_chunks"].get(chunk.id, [])


    if not query_tokens or not chunk_tokens:
        return 0.0
    
    term_frequency = Counter(chunk_tokens)
    document_frequency = stats["document_frequency"]
    document_count = stats["document_count"]
    chunk_length = stats["chunk_lengths"].get(chunk.id, len(chunk_tokens))
    avg_doc_length = stats["avg_doc_length"] or 1.0

    score = 0.0
    
    for token in query_tokens:
        tf = term_frequency.get(token, 0)

        if tf == 0:
            continue

        df = document_frequency.get(token, 0)

        # 平滑版 idf：
        # - df 越小，说明 token 越稀有，idf 越高。
        # - df 越接近 document_count，说明 token 越常见，idf 越低。
        # - +0.5 和外层 log(1 + x) 用来避免除零和负值。
        idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))

        # BM25 的词频饱和项。
        # tf 越大，tf_weight 越大；但增长会逐渐变慢，避免重复词刷高分。
        denominator = tf + k1 * (1 - b + b * chunk_length / avg_doc_length)
        tf_weight = (tf * (k1 + 1)) / denominator

        score += idf * tf_weight

    return score

def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """
    Normalize raw BM25 scores into [0, 1] before mixing with vector scores.

    BM25 原始分数没有固定范围，而 cosine similarity 通常接近 [-1, 1] 或 [0, 1]。
    不归一化就直接相加，会让两个分数尺度不可控。
    """

    if not scores:
        return {}
    
    values = list(scores.values())
    min_score = min(values)
    max_score = max(values)

    if max_score == min_score:
        return {
            key: 0.0
            for key in scores
        }

    return {
        key: (value - min_score) / (max_score - min_score)
        for key, value in scores.items()
    }



def retrieve_hybrid(
        query: str,
        query_vector: list[float],
        index: VectorIndex,
        top_k: int = DEFAULT_TOP_K,
        min_score: float = DEFAULT_MIN_SCORE,
        vector_weight: float = 0.5,
        lexical_weight: float = 0.5,
)-> list[RetrievalResult]:
    """
    Retrieve chunks with hybrid scoring.

    hybrid score = vector_weight * vector_score + lexical_weight * bm25_score

    vector_score:
        由 embedding cosine similarity 提供，擅长语义相似。
    bm25_score:
        由 BM25-lite 提供，擅长精确关键词命中。
    final_score:
        两者加权后的最终排序分数。
    """

    validate_retrieval_args(top_k=top_k, min_score=min_score)
    validate_hybrid_weights(
        vector_weight=vector_weight,
        lexical_weight=lexical_weight,
    )


    chunks = [
        index.get_chunk(chunk_id)
        for chunk_id in index.chunk_ids()
    ]

    chunks = [chunk for chunk in chunks if chunk is not None]

    bm25_stats = build_bm25_stats(chunks)

    # 先分别计算两套分数，再统一归一化和融合。
    # 不要边遍历边排序，否则中间状态会影响最终排名。
    vector_scores: dict[str, float] = {}
    bm25_scores: dict[str, float] = {}

    for chunk in chunks:
        chunk_vector = index.get_vector(chunk.id)

        if chunk_vector is None:
            continue

        vector_scores[chunk.id] = cosine_similarity(query_vector, chunk_vector)

        bm25_scores[chunk.id] = bm25_lite_score(
            query=query,
            chunk=chunk,
            stats=bm25_stats,
        )

    normalized_bm25_scores = normalize_scores(bm25_scores)

    scored_items: list[tuple[str, float, float, float]] = []

    for chunk_id, vector_score in vector_scores.items():
        bm25_score = normalized_bm25_scores.get(chunk_id, 0.0)

        final_score = (
            vector_score * vector_weight + bm25_score * lexical_weight
        )

        if final_score >= min_score:
            scored_items.append(
                (chunk_id, final_score, vector_score, bm25_score)
            )

    # 按 final_score 排序；chunk_id 作为稳定 tie-breaker，保证结果可复现。
    scored_items.sort(key=lambda item: (-item[1], item[0]))

    results: list[RetrievalResult] = []

    for rank, (chunk_id, final_score, vector_score, bm25_score) in enumerate(scored_items[:top_k], start=1):
        chunk = index.get_chunk(chunk_id=chunk_id)

        if chunk is None:
            continue

        results.append(
            RetrievalResult(
                rank = rank,
                chunk = chunk,
                score=final_score,
                metadata={
                    "chunk_id": chunk_id,
                    "source_name": chunk.metadata.get("source_name"),
                    "document_id": chunk.document_id,
                    "retrieval_mode": "hybrid",
                    "vector_score": vector_score,
                    "bm25_score": bm25_score,
                    "final_score": final_score,
                }

            )
        )

    return results

def retrieve_hybrid_RRF(
    query: str,
    query_vector: list[float],
    index: VectorIndex,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = 20,
    rrf_k: int = 60,
    min_rrf_score: float = 0.0,
) -> list[RetrievalResult]:
    """
    Retrieve chunks with hybrid scoring.

    hybrid score = vector_weight * vector_score + lexical_weight * bm25_score

    vector_score:
        由 embedding cosine similarity 提供，擅长语义相似。
    bm25_score:
        由 BM25-lite 提供，擅长精确关键词命中。
    final_score:
        两者加权后的最终排序分数。
    """
    chunks = [
        index.get_chunk(chunk_id)
        for chunk_id in index.chunk_ids()
    ]

    chunks = [chunk for chunk in chunks if chunk is not None]

    bm25_stats = build_bm25_stats(chunks)

    # 先分别计算两套分数，再统一归一化和融合。
    # 不要边遍历边排序，否则中间状态会影响最终排名。
    vector_scores: dict[str, float] = {}
    bm25_scores: dict[str, float] = {}

    for chunk in chunks:
        chunk_vector = index.get_vector(chunk.id)

        if chunk_vector is None:
            continue

        vector_scores[chunk.id] = cosine_similarity(query_vector, chunk_vector)

        bm25_scores[chunk.id] = bm25_lite_score(
            query=query,
            chunk=chunk,
            stats=bm25_stats,
        )

    if candidate_k <= 0:
        raise RetrievalError("candidate_k must be greater than 0.")

    if candidate_k < top_k:
        raise RetrievalError("candidate_k must be greater than or equal to top_k.")

    if rrf_k <= 0:
        raise RetrievalError("rrf_k must be greater than 0.")

    if min_rrf_score < 0:
        raise RetrievalError("min_rrf_score must be greater than or equal to 0.")
    
    # 两路检索各自独立排序。
    vector_candidates = sorted(
        vector_scores.items(),
        key=lambda item: (-item[1], item[0]),
    )[:candidate_k]

    # BM25 为 0 代表没有任何词法命中，不让它进入 lexical candidate pool。
    bm25_candidates = sorted(
        (
            (chunk_id, score)
            for chunk_id, score in bm25_scores.items()
            if score > 0
        ),
        key=lambda item: (-item[1], item[0]),
    )[:candidate_k]


    # rank 从 1 开始，供 RRF 计算使用。
    vector_ranks = {
        chunk_id: rank
        for rank, (chunk_id, _) in enumerate(vector_candidates, start=1)
    }
    bm25_ranks = {
        chunk_id: rank
        for rank, (chunk_id, _) in enumerate(bm25_candidates, start=1)
    }

    # 只融合任一路召回的候选 chunk。
    candidate_ids = set(vector_ranks) | set(bm25_ranks)


    scored_items: list[tuple[str, float]] = []

    for chunk_id in candidate_ids:
        vector_rank = vector_ranks.get(chunk_id)
        bm25_rank = bm25_ranks.get(chunk_id)

        rrf_score = 0.0

        if vector_rank is not None:
            rrf_score += 1/(rrf_k + vector_rank)
        
        if bm25_rank is not None:
            rrf_score += 1/(rrf_k + bm25_rank)

        if rrf_score >= min_rrf_score:
            scored_items.append((chunk_id, rrf_score))
     
    # RRF 最终排序；chunk_id 是稳定的 tie-breaker。
    scored_items.sort(key=lambda item: (-item[1], item[0]))

    results: list[RetrievalResult] = []

    for final_rank, (chunk_id, rrf_score) in enumerate(scored_items[:top_k], start=1):
        chunk = index.get_chunk(chunk_id=chunk_id)

        if chunk is None:
            continue

        results.append(
            RetrievalResult(
                rank = final_rank,
                chunk = chunk,
                score = rrf_score,
                metadata={
                    "chunk_id": chunk_id,
                    "source_name": chunk.metadata.get("source_name"),
                    "document_id": chunk.document_id,
                    "retrieval_mode": "hybrid_rrf",
                    "candidate_k": candidate_k,
                    "rrf_k": rrf_k,
                    "vector_rank": vector_ranks.get(chunk_id),
                    "bm25_rank": bm25_ranks.get(chunk_id),
                    "vector_score": vector_scores.get(chunk_id),
                    "bm25_score": bm25_scores.get(chunk_id),
                    "rrf_score": rrf_score,
                }
            )
        )

    return results

def retrieve(
        query: str, 
        index: VectorIndex,
        top_k: int = DEFAULT_TOP_K,
        min_score: float = DEFAULT_MIN_SCORE,
        retrieval_mode: str = "hybrid_rrf",
        vector_weight: float = 0.5,
        lexical_weight: float = 0.5,
) -> list[RetrievalResult]:
    
    """
    用户查询入口。

    输入自然语言 query，内部先生成 query embedding，然后按 retrieval_mode
    选择纯向量检索或 hybrid 检索。

    retrieval_mode:
        "vector" 只使用 embedding cosine similarity。
        "hybrid" 同时使用 vector score 和 BM25-lite lexical score。
    """

    query = query.strip()

    if not query:
        raise RetrievalError("query must not be empty.")
    
    query_vector = embed_text_bge_micro(query)

    if retrieval_mode == "vector":
        return  retrieve_by_vector(
            query_vector=query_vector,
            index=index,
            top_k=top_k,
            min_score=min_score,
        )

    if retrieval_mode == "hybrid":
        return retrieve_hybrid(
            query=query,
            query_vector=query_vector,
            index=index,
            top_k=top_k,
            min_score=min_score,
            vector_weight=vector_weight,
            lexical_weight=lexical_weight,
        )
    
    if retrieval_mode == "hybrid_rrf":
        return retrieve_hybrid_RRF(
        query=query,
        query_vector=query_vector,
        index=index,
        top_k=top_k,
        candidate_k=20,
        rrf_k=60,
        min_rrf_score=0.0,
    )

    raise RetrievalError(f"Unsupported retrieval_mode: {retrieval_mode}")


if __name__ == "__main__":
    from .documents import load_documents
    from .index import build_index_from_documents

    documents = load_documents(r"D:\xjbx\Agent-Leanring-Notebook\projects\rag-research-agent\data\raw")

    index = build_index_from_documents(documents=documents, chunk_size=200, chunk_overlap=40, strategy="recursive")

    # results = retrieve("What is Retrieval Augmented Generation?", index, top_k=3, min_score=0.1)

    results = retrieve("What is RedMi stock price?", index, top_k=3, min_score=0.1)

    for result in results:
        print(f"rank> {result.rank}  score> {result.score}  chunk_id> {result.chunk.id}")
        print(f"text> {result.chunk.text}")
        print()
