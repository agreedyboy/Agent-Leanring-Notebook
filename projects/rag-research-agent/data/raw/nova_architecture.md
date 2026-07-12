# Nova Insight Platform Architecture

Nova Insight Systems is a fictional company used only for this local RAG corpus. Its document intelligence platform has separate ingestion and query paths.

On the ingestion path, a workspace receives Markdown files, plain text notes, PDF exports, and selected web exports. A parser normalizes text and assigns source metadata. The chunking service creates overlapping passages with stable chunk identifiers. An embedding worker converts each chunk into a dense vector and stores the vector together with source metadata in the workspace index.

On the query path, the platform embeds the user's question and performs hybrid retrieval. Dense vector similarity recalls semantic matches, while BM25-lite contributes exact keyword matches for product names, identifiers, and technical terms. The candidate set can be passed to a reranker before the answer service selects evidence for a final response.

The answer service treats retrieved text as untrusted evidence, not as executable instructions. It produces a document-grounded response and returns citations that refer to retrieved chunk identifiers. A citation verifier checks that every cited identifier belongs to the current result set. The system records retrieval scores, selected chunks, citation status, latency, and errors in a trace event.

The sample deployment does not require a specific vector database. A small local index is sufficient for development. A persistent vector database becomes useful when a workspace contains many documents, needs approximate nearest-neighbor search, or must survive process restarts without re-embedding every chunk.
