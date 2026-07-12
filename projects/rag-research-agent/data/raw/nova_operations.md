# Nova Insight Operations and Monitoring

Nova Insight Systems operates a document intelligence service for small research teams and student labs. The service monitors document load counts, chunk counts, embedding dimensions, retrieval latency, answer latency, citation validation failures, and provider errors.

An ingestion run is considered complete only after each accepted document has a stable identifier and each produced chunk has a corresponding embedding. Empty files are skipped by default and unsupported formats are reported as ingestion failures. The system does not silently claim that a document was indexed when parsing or embedding failed.

For an interactive query, the trace begins with a run identifier. It records the query configuration, document load result, index information, retrieval result summary, model response summary, and final run status. Chunk text and answer text are optional trace fields because they may contain private workspace content.

The service uses a bounded candidate count to control latency. Hybrid retrieval is fast enough for the first candidate stage. Reranking is applied only to a small candidate pool because cross-encoder models score query-chunk pairs more slowly than embedding similarity.

When an answer guard detects an invalid citation, the run status is marked as an answer guard failure. Operators should inspect the invalid citation value, the allowed chunk identifiers, the prompt format, and the provider model version before changing retrieval settings.
