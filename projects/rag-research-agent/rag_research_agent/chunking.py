from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .documents import Document, load_documents


DEFAULT_CHUNK_SIZE = 300
DEFAULT_CHUNK_OVERLAP = 50

DEFAULT_RECURSIVE_SEPARATORS = (
    "\n## ",
    "\n# ",
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    ". ",
    "! ",
    "? ",
    " ",
    "",
)

class ChunkingError(ValueError):
    pass

@dataclass(frozen=True, slots=True)
class Chunk:
    """
    表示一个被切分后的文档片段。

    后续 retrieval 返回的不是完整 Document，而是 Chunk。
    citation 也应该引用 Chunk.id，而不是 Document.id。
    """

    id: str                  # 格式如 doc_hash#chunk_001
    document_id: str         # 所属文档的唯一标示
    text: str                # 喂给模型的核心文本
    
    start_char: int          # 字符流起点
    end_char: int            # 字符流终点

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



def split_span_on_separator(
        text: str,
        start: int,
        end: int,
        separator: str,
) -> list[tuple[int, int]]:
    """
    用指定分隔符切一个字符区间。

    分隔符被保留在后一个片段中。例如 Markdown 标题会继续和
    它后面的正文处于同一候选片段内。
    """

    spans: list[tuple[int, int]] = []
    span_start = start
    search_start = start

    while True:
        separator_start = text.find(separator, search_start, end)

        if separator_start == -1:
            break

        # separator 之前的文本形成一个片段。
        if separator_start > span_start:
            spans.append((span_start, separator_start))

        # 下一个片段从 separator 开始，保留标题或句子边界。
        span_start = separator_start
        search_start = separator_start + len(separator)

    if span_start < end:
        spans.append((span_start, end))

    return spans

def split_span_recursively(
        text: str,
        start: int,
        end: int,
        separators: tuple[str, ...],
        chunk_size: int,
) -> list[tuple[int, int]]:
    """
    递归地把一个区间切成不超过 chunk_size 的语义单元。

    separators 按优先级排列：先尝试段落，失败后再尝试句子、
    单词，最后才按字符强制切分。
    """

    if end - start <= chunk_size:
        return [(start, end)]

    if not separators:
        # 理论上不会进入；作为最后的防御性兜底。
        return [(start, end)]
    
    separator = separators[0]

    # 空字符串代表已没有更细的自然边界，只能固定长度切分。
    if separator == "":
        spans: list[tuple[int, int]] = []
        current_start = start

        while current_start < end:
            current_end = min(current_start + chunk_size, end)
            spans.append((current_start, current_end))
            current_start = current_end

        return spans
    
    candidate_spans = split_span_on_separator(
        text=text,
        start=start,
        end=end,
        separator=separator,
    )

    # 当前分隔符没有真正切开文本，改用下一层分隔符。
    if len(candidate_spans) <= 1:
        return split_span_recursively(
            text=text,
            start=start,
            end=end,
            separators=separators[1:],
            chunk_size=chunk_size
        )
    
    result: list[tuple[int, int]] = []

    for candidate_start, candidate_end in candidate_spans:
        if candidate_end - candidate_start <= chunk_size:
            result.append((candidate_start, candidate_end))
        else:
            result.extend(
                split_span_recursively(
                    text=text,
                    start = candidate_start,
                    end = candidate_end,
                    separators = separators[1:],
                    chunk_size=chunk_size,
                )
            )

    return result


def merge_spans_with_overlap(
        spans: list[tuple[int, int]],
        chunk_size: int,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[tuple[int, int]]:
    """
    将较小的语义单元合并为最终 chunks。

    overlap 按完整单元保留，不强行从句子中间截取字符。
    """

    if not spans:
        return []
    
    merged: list[tuple[int, int]] = []
    current: list[tuple[int, int]] = []
    current_length = 0

    for span in spans:
        span_length = span[1] - span[0]

        # 当前 chunk 放不下下一个语义单元时，先提交当前 chunk。
        if current and current_length + span_length > chunk_size:
            merged.append((current[0][0], current[-1][1]))

            # 从当前 chunk 的尾部保留若干完整单元，作为下一 chunk 的 overlap。
            retained: list[tuple[int, int]] = []
            retained_length = 0

            for previous_span in reversed(current):
                retained.insert(0, previous_span)
                
                retained_length += previous_span[1] - previous_span[0]

                if retained_length >= chunk_overlap:
                    break

            current = retained
            current_length = current[-1][1] - current[0][0]

            # 保证加入新单元后仍不超过 chunk_size
            while current and current_length + span_length > chunk_size:
                remove_start, remove_end = current.pop(0)
                current_length -= remove_end - remove_start

        current.append(span)
        current_length += span_length

    if current:
        merged.append((current[0][0], current[-1][1]))

    return merged

def split_text_spans_recursive(
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        separators: tuple[str, ...] = DEFAULT_RECURSIVE_SEPARATORS,
) -> list[tuple[int, int]]:
    """递归分块的公开入口，返回原文字符区间。"""

    validate_chunk_settings(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if not text:
        return []
    
    atomic_spans = split_span_recursively(
        text=text,
        start = 0,
        end = len(text),
        separators=separators,
        chunk_size=chunk_size,
    )

    return merge_spans_with_overlap(
        atomic_spans,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )



def chunk_document(
    document: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    strategy: str = "fixed",
) -> list[Chunk]:
    """
    将一个 Document 切成多个 Chunk。
    """
    if strategy == "fixed":
        spans = split_text_spans(
            document.text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    elif strategy == "recursive":
        spans = split_text_spans_recursive(
            text = document.text,
            chunk_size = chunk_size,
            chunk_overlap = chunk_overlap,
        )
    else:
        raise ChunkingError(
            f"Unsupported chunking strategy: {strategy!r}. "
            "Use 'fixed' or 'recursive'."
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
                text=chunk_text,
                start_char=start_char,
                end_char=end_char,
                metadata={
                    "source_path":document.source_path,
                    "source_name": document.source_name,
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
    strategy: str = "fixed",
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
                document=document,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                strategy=strategy,
            )
        )

    return chunks

if __name__ == "__main__":
    documents = load_documents(r"D:\xjbx\Agent-Leanring-Notebook\projects\rag-research-agent\data\raw")
    chunks = chunk_documents(documents=documents, chunk_size=180, chunk_overlap=20,strategy="recursive")

    for chunk in chunks[:5]:
        print(chunk.id, chunk.metadata.get("source_name", None), chunk.start_char, chunk.end_char)
        print(chunk.text)
        print()