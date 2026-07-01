from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# 支持的文档的文件格式
SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown"}


class DocumentLoadError(RuntimeError):
    pass


class UnsupportedDocumentType(DocumentLoadError):
    pass


class EmptyDocumentError(DocumentLoadError):
    pass

@dataclass(frozen=True, slots=True)
class Document:
    """
    表示经过简单预处理后的原始文档
    供后续的chunk进行切分
    """
    id: str
    source_path: str
    source_name: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


# 对文本数据进行统一化处理,去除\r
def normalize_text(text: str)->str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()

# 构建文档id编号
def build_document_id(path: Path, root: Path | None = None) -> str:
    if root is not None:
        try:
            key = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            key = path.resolve().as_posix()
    else:
        key = path.resolve().as_posix()

    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    stem = path.stem.lower().replace(" ", "-")
    return f"{stem}-{digest}"

# 读取文件内容
def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentLoadError(f"Failed to decode file as UTF-8: {path}") from exc
    
# 加载路径的文件的内容
def load_document(path: str | Path, root: str | Path | None = None) -> Document:
    path = Path(path)

    if not path.exists():
        raise DocumentLoadError(f"Document does not exist: {path}")

    if not path.is_file():
        raise DocumentLoadError(f"Document path is not a file: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedDocumentType(f"Unsupported document type: {suffix}")

    root_path = Path(root) if root is not None else None
    raw_text = read_text_file(path)
    text = normalize_text(raw_text)

    if not text:
        raise EmptyDocumentError(f"Document is empty: {path}")

    return Document(
        id=build_document_id(path, root=root_path),
        source_path=str(path),
        source_name=path.name,
        text=text,
        metadata={
            "suffix": suffix,
            "size_bytes": path.stat().st_size,
        },
    )

# 递归遍历指定目录及其子目录，筛选出所有符合支持格式的文件，并以迭代器的形式逐个返回它们的路径对象
def iter_document_paths(root: str | Path) -> Iterable[Path]:
    root = Path(root)

    if not root.exists():
        raise DocumentLoadError(f"Document directory does not exist: {root}")

    if not root.is_dir():
        raise DocumentLoadError(f"Document root is not a directory: {root}")

    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path

# 迭代加载并返回根目录中所有符合支持格式的文件
def load_documents(root: str | Path, skip_empty: bool = True) -> list[Document]:
    root = Path(root)
    documents: list[Document] = []

    for path in iter_document_paths(root):
        try:
            document = load_document(path, root=root)
        except EmptyDocumentError:
            if skip_empty:
                continue
            raise

        documents.append(document)

    return documents

if __name__ == "__main__":
    documents = load_documents(r"D:\xjbx\Agent-Leanring-Notebook\projects\rag-research-agent\data\raw")

    for doc in documents:
        print(doc.id)
        print(doc.source_path)
        print(doc.source_name)
        print(doc.text[:20])
