# Citation Policy

This policy defines how the Nova Insight Systems research platform presents evidence to users. It applies to generated answers, exported reports, and internal evaluation runs.

Every factual statement in a grounded answer should be traceable to one or more retrieved document chunks. The user interface displays citations using stable chunk identifiers rather than only a file name. A source file can contain many chunks, so citing only `company_overview.md` is not sufficiently precise for audit or debugging.

The answer service accepts a citation only when its chunk identifier appears in the retrieval results for the current query. Citations from a previous query, guessed identifiers, and identifiers from documents outside the user's workspace are invalid. When validation fails, the service records a citation failure and does not present the unverified answer as grounded.

An answer that contains no supporting evidence must use the standard no-evidence response. It must not add a citation merely to make an unsupported statement appear reliable. A refusal should have an empty citation list.

Citation validity and citation faithfulness are related but different checks. Validity asks whether the cited chunk exists in the retrieved set. Faithfulness asks whether that chunk actually supports the claim near the citation. The current baseline verifier performs validity checks deterministically. A later verifier may use sentence-level similarity or a separate model to assess faithfulness.

For debugging, traces store the query, retrieved chunk identifiers, final citations, validation status, and failure type. Full document content and generated answers are stored only when a debug trace is explicitly enabled because research workspaces can contain sensitive notes.
