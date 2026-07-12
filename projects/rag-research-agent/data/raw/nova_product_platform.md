# Nova ResearchDesk Product Platform

ResearchDesk is the fictional flagship product of Nova Insight Systems. It is a private document intelligence workspace for research assistants, technical writers, university project teams, and early-stage startups.

The product has four primary capabilities. First, Document Intake accepts Markdown, TXT, PDF exports, and web-exported notes. Second, Evidence Search uses embeddings and lexical retrieval to locate passages relevant to a question. Third, Grounded Drafting creates short answers and report sections with source citations. Fourth, Quality Review records evaluation results, traces, latency, and common failure categories.

ResearchDesk is not marketed as a general consumer chatbot. Its intended workflow starts with a trusted workspace of user-provided material. The product is designed to answer questions about that material and to refuse questions for which the workspace has no evidence.

The Evidence Search page exposes retrieval mode, candidate count, and minimum-score configuration to internal evaluators. A hybrid mode combines vector similarity with BM25-lite lexical scoring. The product team plans to add a cross-encoder reranker for larger workspaces where the initial candidate set contains many near matches.

The Quality Review page lets an evaluator inspect a run trace. It shows the retrieved source names, chunk identifiers, vector score, lexical score, final retrieval score, generated citations, and answer guard outcome. It does not display API keys or other secret configuration values.
