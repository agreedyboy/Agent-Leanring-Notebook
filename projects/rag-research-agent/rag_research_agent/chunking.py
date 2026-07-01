from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .documents import Document, load_documents


DEFAULT_CHUNK_SIZE = 300
DEFAULT_CHUNK_OVERLAP = 50

class ChunkingError(ValueError):
    pass

@dataclass(frozen=True, slots=True)
class Chunk:
    """
    表示一个被切分后的文档片段。

    后续 retrieval 返回的不是完整 Document，而是 Chunk。
    citation 也应该引用 Chunk.id，而不是 Document.id。
    """

    id: str
    document_id: str
    source_path: str
    source_name: str
    text: str
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)

def validate_chunk_settings(chunk_size: int, chunk_overlap: int) -> None:
    """
    校验 chunk 参数，避免出现无限循环或无意义切分。
    """

    if chunk_size <= 0:
        raise ChunkingError("chunk_size must be greater than 0.")

    if chunk_overlap < 0:
        raise ChunkingError("chunk_overlap must be greater than or equal to 0.")

    if chunk_overlap >= chunk_size:
        raise ChunkingError("chunk_overlap must be smaller than chunk_size.")
    
def build_chunk_id(document_id: str, chunk_index: int)->str:
    """
    构造稳定的 chunk id。

    示例：
    agent_basics-e5e1d84256#chunk_001
    """
    return f"{document_id}#chunk_{chunk_index:03d}"

def split_text_spans(
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[tuple[int, int]]:
    """
    把文本切成多个字符区间。

    返回值是 [(start_char, end_char), ...]。
    这里只返回位置，不直接返回文本，是为了让 Chunk 能记录原文位置。
    """

    validate_chunk_settings(chunk_size, chunk_overlap)

    if not text:
        return []
    
    spans: list[tuple[int, int]] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start+chunk_size, text_length)

        spans.append((start, end))

        if end == text_length:
            break
        
        # 下一段从当前 end 往前回退 overlap 个字符，保留上下文连续性。
        start = end - chunk_overlap

    return spans

def chunk_document(
    document: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    将一个 Document 切成多个 Chunk。
    """

    spans = split_text_spans(
        document.text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks: list[Chunk] = []

    for index, (start_char, end_char) in enumerate(spans, start=1):
        chunk_text = document.text[start_char:end_char].strip()

        # 理论上 Document 已经过空文本检查，这里是防御性处理。
        if not chunk_text:
            continue

        chunks.append(
            Chunk(
                id=build_chunk_id(document.id, index),
                document_id=document.id,
                source_path=document.source_path,
                source_name=document.source_name,
                text=chunk_text,
                start_char=start_char,
                end_char=end_char,
                metadata={
                    "chunk_index": index,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "document_metadata": document.metadata,
                },
            )
        )

    return chunks


def chunk_documents(
    documents: list[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    批量切分多个 Document。

    输入：
        list[Document]

    输出：
        list[Chunk]
    """

    chunks: list[Chunk] = []

    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )

    return chunks

if __name__ == "__main__":
    documents = load_documents(r"D:\xjbx\Agent-Leanring-Notebook\projects\rag-research-agent\data\raw")
    chunks = chunk_documents(documents=documents)

    for chunk in chunks:
        print(chunk.id, chunk.source_name, chunk.start_char, chunk.end_char)
        print(chunk.text[:80])
        print()