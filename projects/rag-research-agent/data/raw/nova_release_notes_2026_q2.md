# ResearchDesk Release Notes: 2026 Q2

These fictional release notes describe changes in the second quarter of 2026 for the sample Nova Insight Systems corpus.

Version 0.8 added JSONL tracing for document load, index construction, retrieval, and answer-generation events. Trace payloads redact fields whose names indicate API keys, authorization values, passwords, secrets, or tokens.

Version 0.9 introduced a hybrid retrieval experiment. The experiment combines normalized BM25-lite lexical scores with embedding cosine similarity. Internal evaluators can adjust the vector and lexical weights, but the two weights must be non-negative and add up to one so final scores remain interpretable.

Version 0.10 added answer-evaluation cases. Supported questions must return a grounded answer with valid citations. Unsupported questions must return the standard no-evidence answer. A model response that is replaced by an answer guard because of an invalid citation is counted as an evaluation failure rather than a successful refusal.

The release does not introduce a public API, mobile application, stock market listing, pricing change, or financial performance disclosure.
