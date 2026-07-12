# RAG Evaluation Playbook

Evaluation cases for a document-grounded assistant should be fixed, repeatable, and small enough to run during normal development. A passing demo question is not enough because retrieval quality often changes after a chunking, embedding, or ranking adjustment.

Nova Insight Systems groups evaluation cases into four classes. Answerable cases have direct evidence in one or more documents. Unanswerable cases mention known entities but ask for information absent from the collection. Ambiguous cases contain terms with more than one plausible meaning. Multi-hop cases require combining evidence from two sources before answering.

Retrieval-only evaluation checks whether expected source documents or chunks appear in the candidate set. It is useful for finding retrieval regressions, but it cannot prove that the final answer is grounded. Answer evaluation additionally checks that supported answers contain valid citations and unsupported questions produce the exact no-evidence response.

Useful measurements include retrieval recall at k, answer pass rate, citation validity rate, refusal accuracy, latency, and failure type. Scores from different retrievers should not be compared without considering their scale. For example, raw BM25 scores are not directly comparable to cosine similarity scores.

Each failure should be classified before it is fixed. Common labels are ingestion, chunking, retrieval, rerank, citation, synthesis, abstention, latency, and cost. A failed case should preserve its query, expected behavior, observed result, and a short explanation of the repair. This turns the evaluation suite into a regression baseline rather than a one-time report.

For this sample corpus, a stock-price question about Nova Insight Systems is intentionally unanswerable. The collection describes the fictional company's product and operations, but it contains no market listing, share price, revenue, or investment advice.
