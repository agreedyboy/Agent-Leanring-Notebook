# Vector Database Notes

A vector database stores embeddings together with identifiers and metadata, then searches for nearby vectors. It is useful when a RAG corpus is too large for a process-local list scan or when the index must persist across program restarts.

For a small learning corpus, an in-memory VectorIndex is easier to inspect and is sufficient for understanding cosine similarity. The application embeds each chunk, stores the vector under a stable chunk id, and scans all vectors for a query. This is exact search but becomes slower as the number of chunks grows.

At a larger scale, systems commonly use approximate nearest-neighbor indexes such as HNSW. Approximate search trades a small amount of recall for lower latency. A production vector store also commonly supports metadata filtering, namespaces or collections, persistence, backup, and access-control integration.

Moving to a vector database should not change the RAG contracts. Retrieval should still return chunk identifiers, source metadata, scores, and text. Citation validation should still check generated citations against the retrieved identifiers. Evaluation should compare retrieval quality before and after the storage change rather than assuming the new database is automatically better.

BM25 and vector search solve different retrieval problems. A vector database may provide dense search, while a separate lexical engine or built-in hybrid feature can provide keyword search. Hybrid ranking and reranking remain application-level design choices even after vectors are persisted.
