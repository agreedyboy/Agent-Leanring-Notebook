from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .chunking import Chunk
from .embeddings import EmbeddingResult


class IndexError(ValueError):
    pass

@dataclass(frozen=True, slots=True)
class VectorIndex:
    """
    一个最小内存向量索引。

    chunks:
        保存 chunk_id -> Chunk。
    vectors:
        保存 chunk_id -> embedding vector。
    metadata:
        保存索引构建时的辅助信息，例如 chunk 数量、向量维度等。
    """

    chunks: dict[str, Chunk]
    vectors: dict[str, list[float]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def chunk_ids(self) -> list[str]:
        """
        返回索引中所有 chunk id。

        排序后返回，方便调试和测试时结果稳定。
        """

        return sorted(self.chunks)
    
    def get_chunk(self, chunk_id: str) -> Chunk | None:
        """
        根据 chunk id 获取 Chunk原数据。
        """
        return self.chunks.get(chunk_id)
    
    def get_vector(self, chunk_id: str) -> list[float] | None:
        """
        根据 chunk id 获取对应向量。
        """
        return self.vectors.get(chunk_id)
    
    def __len__(self) -> int:
        """
        返回索引中的 chunk 数量。
        """
        return len(self.chunks)
    

def validate_unique_chunk_ids(chunks: list[Chunk]) -> None:
    """
    确认 chunk id 没有重复。

    如果重复，后续 dict 会发生覆盖，导致 citation 和 retrieval 都不可靠。
    """

    seen: set[str] = set()

    for chunk in chunks:
        if chunk.id in seen:
            raise IndexError(f"Duplicate chunk id: {chunk.id}")
        seen.add(chunk.id)

def validate_embedding_ids(
    chunks: list[Chunk],
    embeddings: list[EmbeddingResult],
) -> None:
    """
    确认 embedding 的 text_id 与 chunk.id 完全匹配。

    Stage 4 的索引要求：
    - 每个 chunk 必须有一个 embedding
    - 不能存在没有对应 chunk 的 embedding
    """

    chunk_ids = {chunk.id for chunk in chunks}
    embedding_ids = {item.text_id for item in embeddings}

    missing_embeddings = chunk_ids - embedding_ids
    extra_embeddings = embedding_ids - chunk_ids

    if missing_embeddings:
        raise IndexError(
            "Missing embeddings for chunk ids: "
            + ", ".join(sorted(missing_embeddings))
        )

    if extra_embeddings:
        raise IndexError(
            "Embeddings exist for unknown chunk ids: "
            + ", ".join(sorted(extra_embeddings))
        )
    
def validate_vector_dimensions(embeddings: list[EmbeddingResult]) -> int:
    """
    确认所有向量维度一致。

    返回公共维度，方便写入 metadata。
    """

    if not embeddings:
        raise IndexError("Cannot build index from empty embeddings.")

    dimensions = len(embeddings[0].vector)

    if dimensions == 0:
        raise IndexError("Embedding vector must not be empty.")

    for item in embeddings:
        if len(item.vector) != dimensions:
            raise IndexError(
                f"Inconsistent vector dimensions for {item.text_id}: "
                f"expected {dimensions}, got {len(item.vector)}"
            )

    return dimensions

def build_index(
        chunks: list[Chunk],
        embeddings: list[EmbeddingResult],
) -> VectorIndex:
    """
    从 chunks 和 embeddings 构建内存索引。

    输入：
        chunks: chunk_document / chunk_documents 的输出
        embeddings: embed_chunks 的输出

    输出：
        VectorIndex
    """

    if not chunks:
        raise IndexError("Cannot build index from empty chunks.")
    
    # 验证输入有效
    validate_unique_chunk_ids(chunks)
    validate_embedding_ids(chunks, embeddings)
    dimensions = validate_vector_dimensions(embeddings)

    chunk_map = {chunk.id: chunk for chunk in chunks}
    vector_map = {item.text_id: item.vector for item in embeddings}

    return VectorIndex(
        chunks=chunk_map,
        vectors=vector_map,
        metadata={
            "chunk_count": len(chunks),
            "embedding_count": len(embeddings),
            "dimensions": dimensions,
        },
    )

def build_index_from_documents(
    documents,
    chunk_size: int = 300,
    chunk_overlap : int = 50,
    strategy: str = "fixed",
)->VectorIndex:
    """
    一个便捷函数：从 Document 列表直接构建 VectorIndex。

    注意：
    这里为了方便调试，把 chunking 和 embedding 串起来。
    但长期来看，CLI 或 pipeline 层负责串流程会更清晰。
    """

    from .chunking import chunk_documents
    from .embeddings import embed_chunks

    chunks = chunk_documents(
        documents=documents,
        chunk_size=chunk_size,
        chunk_overlap = chunk_overlap,
        strategy=strategy
    )
    embeddings = embed_chunks(chunks=chunks)

    return build_index(chunks=chunks, embeddings=embeddings)

if __name__ == "__main__":
    from .documents import load_documents

    documents = load_documents(r"D:\xjbx\Agent-Leanring-Notebook\projects\rag-research-agent\data\raw")

    index = build_index_from_documents(documents=documents, chunk_size=300, chunk_overlap=50)

    print(len(index))
    print(index.metadata)
    print(index.chunk_ids()[:3])
