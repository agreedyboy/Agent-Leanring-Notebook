# Agent Internship Roadmap — Execution-First Revision

面向对象：计算机专业大三学生。

目标：从现在开始系统学习 Agent 技术栈，到九月初具备投递 Agent / LLM 应用 / AI 工程实习的项目能力、工程表达能力和面试答辩能力。

这不是一份 Agent 生态百科，也不是框架速成清单。这是一份面向实习求职的工程路线。核心原则是：

```text
少读泛资源，多做可运行、可测试、可解释、可复现的工程项目。
```

---

## 0. Final Target Outcome

到九月初，你应该能证明自己具备以下能力：

1. 能从零实现一个最小 Agent loop。
2. 能设计和执行 tool calling / function calling。
3. 能实现 tool registry、schema validation、timeout、retry，并能说明 permission gate 的设计边界。
4. 能构建一个带引用、带 citation verifier、带失败分析的 RAG / Research Agent。
5. 能为 Agent 写固定 eval cases，并记录 success rate、failure type、latency、cost、tool calls。
6. 能用 trace 解释一次 Agent 运行过程中的 LLM call、tool call、state change 和 failure。
7. 能完成至少两个可运行项目，并在简历和面试中讲清楚工程取舍。

最终推荐产出：

| Project              | Purpose                              | Priority    | Target Quality                                                                     |
| -------------------- | ------------------------------------ | ----------- | ---------------------------------------------------------------------------------- |
| Agent Harness Mini   | 展示你理解 Agent 底层机制            | P0 必做     | 可运行、可测试、带 CLI、带 JSONL trace、带 eval runner                             |
| RAG / Research Agent | 展示检索、引用、grounding、评测能力  | P0 必做     | 支持 ingestion、retrieval、citation verifier、unanswerable cases、failure analysis |
| Coding Review Agent  | 展示工具调用、代码分析、工程落地能力 | P1 条件选做 | 只有在两个 P0 项目通过 Week 9 gate 后启动                                          |
| Web Research Agent   | 展示搜索、筛选、引用、报告生成能力   | P1 条件替代 | 可替代 Coding Review Agent，但不和它同时做                                         |
| MCP / Skill Demo     | 展示你了解现代 Agent 生态            | P2 轻量选做 | 1-2 天完成，不作为主项目                                                           |

推荐最终组合：

```text
默认交付：Agent Harness Mini + RAG / Research Agent
条件加强：Coding Review Agent 或 Web Research Agent 二选一
轻量展示：MCP / Skill Demo，只在两个 P0 项目稳定后做
```

执行口径：

```text
两个强项目 > 三个半成品项目。
```

---

## 1. Core Positioning

最终简历定位可以写成：

```text
CS undergraduate focused on LLM agent engineering. Built a minimal agent harness and a document-grounded RAG agent with structured tool calling, tracing, evaluation, citation verification, and failure analysis.
```

中文表达：

```text
我理解 Agent 的工程边界，能实现工具调用、状态管理、trace 和 eval，并能说明权限控制等安全机制应该在什么场景下引入。
```

重点不是说“我学过很多 Agent 框架”，而是证明：

```text
我能把 Agent 从 demo 做成一个可调试、可评测、可复现的小型工程系统。
```

---

## 2. What To Learn First

优先级如下：

| Priority | Learn                           | Why                                                      |
| -------- | ------------------------------- | -------------------------------------------------------- |
| 1        | Minimal Agent Loop              | 不理解 loop，就只是在调框架 API。                        |
| 2        | Tool Calling                    | Agent 的核心能力来自可控工具执行。                       |
| 3        | Tool Harness                    | 真正的工程能力在工具注册、状态、trace、eval 和错误处理。 |
| 4        | RAG With Citations              | 很多实习项目本质是企业知识库 / 搜索 / 报告生成。         |
| 5        | Evaluation                      | 没有 eval 的 Agent 只能算 demo。                         |
| 6        | Coding / Research Agent Pattern | 代码审查、搜索研究、报告生成是高价值落地方向。           |

暂时不要重押：

| Topic                            | Treatment                                       |
| -------------------------------- | ----------------------------------------------- |
| Role-play multi-agent frameworks | 了解即可，不作为主线。                          |
| Personal always-on agents        | 九月前不深挖。                                  |
| Browser / computer-use agents    | 除非明确想做该方向，否则选学。                  |
| A2A / ACP                        | 知道用途即可，不需要深入协议细节。              |
| 大量论文综述                     | 只读关键论文摘要和核心思想。                    |
| 复杂 MCP 生态                    | 只做轻量 demo，优先级低于主项目。               |
| 只会调 LangChain / LlamaIndex    | 不足以证明 Agent 工程能力，必须有手写核心组件。 |

---

## 3. How To Use This Roadmap

每个阶段都遵循同一结构：

1. 先读 1-2 个必看资料，理解概念边界。
2. 再做一个最小实现，不要先上复杂框架。
3. 每个实现都接入最小 eval 和 trace。
4. 最后对照成熟框架或开源项目，看别人如何工程化。
5. 每个阶段都必须留下一个可检查产出。

资料优先级：

| Type          | Meaning                          |
| ------------- | -------------------------------- |
| Must Read     | 必看。只看这些也能完成本阶段。   |
| Hands-on      | 动手入口。优先跟着做或参考实现。 |
| Optional      | 有余力再看，不影响主线进度。     |
| Avoid For Now | 当前阶段不建议投入时间。         |

每周结束必须回答三个问题：

```text
1. 本周新增了什么可运行能力？
2. 本周新增了哪些 eval cases？
3. 本周发现了哪些失败模式？
```

阶段门槛：

```text
Gate A — Week 5 结束：
Agent Harness Mini 必须能通过 CLI 运行，至少有 15 条 eval cases，并能生成 JSONL trace。

Gate B — Week 9 结束：
RAG / Research Agent 必须有 citation verifier、至少 20 条 RAG eval cases、至少 5 条 unanswerable cases，并能展示 3 个失败案例。

Gate C — Week 10 开始前：
只有 Gate A 和 Gate B 都通过，才启动 Coding Review Agent 或 Web Research Agent。
否则取消第三项目，把 Week 10-12 全部用于补两个 P0 项目的 README、eval、trace、examples、复现环境。
```

---

# 4. Learning Path

## Stage 0: Understand Agent Boundaries

目标：知道什么时候应该用 Agent，什么时候不应该用。

### Checklist

- [✔] 区分 chatbot、workflow、agent、multi-agent。
- [✔] 理解基本循环：observe -> think/plan -> act -> observe。
- [✔] 明白什么时候不该用 agent：任务稳定、步骤确定、普通脚本能解决时，不要引入 agent。
- [✔] 写一页笔记：我的目标场景为什么需要 agent，而不是普通 workflow？

### Must Read

1. Anthropic: Building Effective Agents重点看：workflow 和 agent 的区别、什么时候用 simple workflow、什么时候需要 autonomous agent。
2. OpenAI: A Practical Guide to Building Agents
   重点看：agent 的定义、适合场景、tool design、guardrails。

### Optional

1. Lilian Weng: LLM Powered Autonomous Agents用途：建立 agent 架构全局视角。只看 planning、memory、tool use 三部分。
2. ReAct Paper
   用途：理解 reasoning + acting 的基本范式。只读 abstract、introduction 和图示。

### Output

```text
notes/when-to-use-agent.md
```

### Acceptance Criteria

- 能举出 3 个适合 Agent 的任务。
- 能举出 3 个不适合 Agent 的任务。
- 能解释 workflow、agent、multi-agent 的区别。
- 能解释为什么“能聊天”不等于“是 Agent”。

### Suggested Note Template

| Task                   | Workflow or Agent? | Reason                           |
| ---------------------- | ------------------ | -------------------------------- |
| 自动格式化代码         | Workflow           | 步骤确定，规则清晰。             |
| 根据多个网页写研究报告 | Agent              | 需要动态搜索、筛选、判断和迭代。 |
| 定时发日报             | Workflow           | 触发条件和输出格式固定。         |
| 修复未知 bug           | Agent              | 需要观察、尝试、执行测试、迭代。 |

---

## Stage 1: Agent Harness Mini v0 — Minimal Agent Loop

目标：不用框架，从零写一个最小 Agent loop。这个阶段开始的代码直接放进 `projects/agent-harness-mini/`，后续持续演化，不再另建零散项目。

### Checklist

- [✔] 调用一个 LLM API 完成普通对话。
- [✔] 让模型输出结构化 JSON。
- [✔] 定义至少 2 个工具，例如 `calculator`、`read_file`。

  - 为了方便实现，我此处实现的是`get_weather` 与 `get_user_profile` 两个提前写好的会返回固定结果的tools，而非调用外部api
- [✔] 解析 tool call / function call。
- [✔] 执行工具并把结果作为 observation 喂回模型。
- [✔] 加入 `max_steps`，防止死循环。
- [✔] 保存最小 trace。

  - 其作用有点类似 `日志`，相较于在终端print进行查看执行过程，trace确实能够更直观或更清晰地展示智能体的执行过程

- [ ] 写 5 个 eval cases。
  - 目前所实现的智能体还是相对较为简单的，感觉暂时没有必要专门实现eval cases，因此跳过这一步

- [✔] 记录至少一种失败类型，例如 tool error 或 max_steps exceeded。

### Must Read

1. OpenAI Function Calling重点看：tools schema、arguments、模型如何请求调用函数、如何把函数结果返回模型。
2. OpenAI Using Tools重点看：function calling 与 hosted tools 的区别。当前阶段只做自定义 function tools。
3. Claude Tool Use Overview
   重点看：Claude 的 tool use 消息格式。目的不是同时写两套实现，而是比较不同厂商的工具调用抽象。

### Hands-on

先实现最小逻辑：

```text
User query
  -> LLM decides tool
  -> execute tool
  -> return observation
  -> LLM final answer
```

禁止一开始使用 LangChain / LangGraph / Agents SDK。

### Minimal Directory

```text
projects/agent-harness-mini/
  README.md
  pyproject.toml
  agent/
    loop.py
    tools.py
  tools/
    calculator.py
    file_reader.py
  evals/
    cases.yaml
  traces/
    .gitkeep
  examples/
    run_basic.py
```

### Acceptance Criteria

- 至少支持 2 个工具。
- 工具调用失败时不会崩溃。
- 有 5 个 eval cases。
- 每次运行生成 trace。
- eval cases 覆盖 tool call 正确性、loop 停止、工具失败。
- 能解释 agent loop 中每一步的输入输出。

---

## Stage 2: Agent Harness Mini v1 — Robust Tool Use

目标：从“能调工具”升级到“可靠地调工具”。

范围说明：`Agent Harness Mini` 当前阶段是学习型 harness，重点是亲手理解 function calling、tool registry、schema validation、timeout、retry、trace 等核心模块。暂不实现 `requires_permission` / permission gate；危险工具权限、路径 allowlist、human approval 等安全机制留到后续复现 Coding Review / Web Research / Shell 工具类项目时实现。

### Checklist

- [✔] 设计 `Tool` 抽象。
- [✔] 设计 `ToolRegistry`。
- [✔] 每个工具都有 name、description、input schema、output schema。

  - output schema通过设计了一个ToolResult类来实现了一个统一输出格式
- [✔] 工具有 timeout。
- [✔] 工具有 retry policy。
- [✔] 工具有统一错误对象。
- [✔] 工具错误至少区分 invalid input、timeout、empty result、runtime error。
- [→] 暂不实现 permission gate。

  - 当前项目不引入危险工具，permission gate 留到后续复现项目中实现。
- [✔] 每次工具调用写入 JSONL trace。

  - tracing 的逻辑写在loops中

- [ ] eval cases 从 5 条扩展到 10 条。
  - 还是感觉目前系统过于简单，没必要进行eval cases，因此跳过

### Tool Abstraction

```python
class Tool:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    timeout_seconds: int
    retry_policy: dict
```

### Unified Tool Result

```json
{
  "ok": false,
  "error_type": "timeout",
  "message": "tool execution exceeded 5 seconds",
  "data": null
}
```

### Trace Event Example

```json
{
  "run_id": "2026-xx-xx-abc123",
  "step": 2,
  "event_type": "tool_call",
  "tool_name": "read_file",
  "input": {"path": "README.md"},
  "output": {"ok": true, "data": "..."},
  "latency_ms": 42
}
```

### Must Read

1. OpenAI Function Calling第二遍阅读。重点不再是“怎么调用”，而是 schema 怎么写才不容易误调用。
2. OpenAI Agents SDK: Tools重点看 function tools 的抽象方式。不要急着迁移到 SDK，先借鉴设计。
3. Anthropic Tool Use Overview
   重点看 tool result 如何回传、模型如何继续推理。

### Acceptance Criteria

- 支持 3-5 个工具。
- 每次工具调用都有 trace。
- 错误能被 agent 继续处理，而不是直接中断。
- 能解释 schema、timeout、retry 的设计取舍，并说明为什么当前项目暂缓 permission gate。

---

## Stage 3: Agent Harness Mini v2 — State, Trace, Eval Runner, CLI

目标：把前两阶段的工具调用能力整理成一个真正可运行的小型 Agent harness。

### Checklist

- [✔] Agent loop。
- [✔] Tool registry。
- [✔] Session state / memory。
  - 实现了简易的memory，即将历史上下文全部保存，下次对话时将这些上下文全部交给LLM
- [✔] Trace logger。
- [✔] Context management。
- [✔] Max steps / timeout / retry。
- [✔] Eval runner。
  - 可以通过修改evals/cases.yaml中的参数来进行建议的评估
- [✔] CLI interface。
  - 目前可以通过终端进行聊天，并支持多轮对话

### Must Read

1. LangGraph Overview重点看 stateful workflow、durable execution、human-in-the-loop、memory。目的不是立刻重写项目，而是学习 harness 应该承担哪些职责。
2. OpenAI Agents SDK: Agents重点看 agent instructions、tools、handoffs、guardrails、structured outputs。
3. OpenAI Agents SDK: Tracing
   重点看 trace 应记录 LLM generations、tool calls、handoffs、guardrails、自定义事件。

### Recommended Directory Structure

```text
agent-harness-mini/
  README.md
  pyproject.toml
  agent/
    loop.py
    tools.py
    registry.py
    tracing.py
    session.py
    context.py
    evals.py
    cli.py
  tools/
    calculator.py
    file_reader.py
    file_writer.py
    web_search.py
  evals/
    cases.yaml
    results.csv
  traces/
    .gitkeep
  examples/
    run_basic.py
    sample_tasks.md
  tests/
    test_registry.py
    test_tools.py
    test_evals.py
```

### Acceptance Criteria

- 可以通过 CLI 运行。
- 有 JSONL trace。
- 有 eval runner。
- 至少 15 条 eval cases，覆盖正常工具调用、工具失败、重复调用、max_steps。
- 有 `make test` / `make eval` 或等价命令。
- 能用一张架构图解释模块关系。
- 通过 Gate A 后才能进入 RAG 项目的深度开发。

---

## Stage 4: RAG / Research Agent v0 — Grounded QA With Citations

目标：构建一个能基于文档回答问题并给出引用的 Agent。

这个项目可以独立建 repo，也可以复用 `agent-harness-mini` 的 tool registry、trace logger 和 eval runner。推荐复用核心 harness，单独做一个 `rag-research-agent` 项目，展示“通用 agent harness 如何支撑具体应用”。

### Checklist

- [✔] 支持 PDF / Markdown / TXT ingestion。
  - PDF目前暂不支持，只支持.md与.text格式文件的解析
- [✔] 实现 chunking。

- [✔] 使用 embedding 建索引。
- [✔] 实现 retrieval。
- [✔] 回答时附带 source / citation。
- [✔] 处理检索为空的情况。
- [✔] 记录 query、retrieved chunks、final answer。
- [✔] 写 20 个 QA eval cases。

### Must Read

1. What's RAG
   【RAG 工作机制详解——一个高质量知识库背后的技术全流程】 [https://www.bilibili.com/video/BV1JLN2z4EZQ/?share_source=copy_web&vd_source=802d6bdcc1614352e3c83dd88e3c2b25]
2. LlamaIndex: Introduction to RAG重点看：为什么需要 RAG、ingestion、index、retrieval、response synthesis。
3. LlamaIndex Starter Tutorial重点看：如何从文档构建 index 并 query。
4. LangChain RAG Concepts
   重点看：retriever、document loader、text splitter、vector store 的职责边界。

### Hands-on

先实现最小版本：

```text
documents
  -> chunks
  -> embeddings
  -> vector store
  -> retrieve top-k chunks
  -> answer with citations
```

然后补可靠性机制：

1. 如果 top-k chunks 分数过低，回答“没有在资料中找到依据”。
2. final answer 只能引用 retrieved chunks 中真实存在的 source id。
3. trace 中保存 query、retrieved chunk ids、answer、citations。

### Directory Structure

```text
rag-research-agent/
  README.md
  pyproject.toml
  rag/
    ingest.py
    chunking.py
    embeddings.py
    index.py
    retrieve.py
    rerank.py
    answer.py
    citations.py
    evals.py
  data/
    raw/
    processed/
  evals/
    cases.yaml
    results.csv
  traces/
    .gitkeep
  examples/
    sample_docs/
    run_qa.py
  docs/
    failure-analysis.md
```

### Citation Format

```text
Answer sentence. [source: doc_a.md#chunk_003]
```

### Empty Retrieval Policy

```text
没有在资料中找到依据。
```

不要让模型在无证据时补全答案。

### Acceptance Criteria

- 至少支持上传 5 个文档。
- 至少有 20 个 QA eval cases，覆盖 answerable、unanswerable、ambiguous、multi-hop。
- 至少 5 个 unanswerable cases。
- 每个回答必须包含引用，或者明确回答“没有在资料中找到依据”。
- final answer 不能引用未检索到的 chunk。
- README 中包含失败样例。
- 能解释 chunk size、top-k、embedding model、rerank 的取舍。

---

## Stage 5: RAG / Research Agent v1 — Hybrid Retrieval, Rerank, Citation Verification

目标：避免 RAG 项目停留在框架 demo，补上能体现工程能力的关键机制。

### Checklist

- [ ] 实现 BM25 或 keyword retrieval。
- [ ] 实现 embedding retrieval。
- [ ] 实现简单 hybrid retrieval。
- [ ] 实现 rerank。
- [ ] 实现 citation verifier。
- [ ] 实现 failed retrieval analysis。
- [ ] eval cases 覆盖 answerable、unanswerable、ambiguous、multi-hop 四类问题。

### Hybrid Retrieval

最低要求：

```text
hybrid_score = alpha * normalized_embedding_score + (1 - alpha) * normalized_bm25_score
```

不需要过早追求复杂系统，先让自己能解释：

```text
什么时候 keyword search 更可靠？
什么时候 embedding retrieval 更可靠？
为什么 hybrid retrieval 能减少漏检？
```

### Rerank

可选实现方式：

| Method               | Difficulty | Use                                                   |
| -------------------- | ---------- | ----------------------------------------------------- |
| LLM rerank           | 低         | 让模型判断 chunk relevance，成本较高。                |
| Cross-encoder rerank | 中         | 更工程化，适合展示 retrieval pipeline。               |
| Heuristic rerank     | 低         | 根据 title match、keyword overlap、recency 简单排序。 |

### Citation Verifier

核心规则：

```text
final answer 中出现的每个 citation id 必须满足：
1. citation id 存在于 retrieved chunks；
2. citation id 对应 chunk 与该句答案有语义相关性；
3. citation id 不能由模型自由生成。
```

最低实现：

```python
def verify_citations(answer, retrieved_chunk_ids):
    cited_ids = extract_citation_ids(answer)
    invalid = [cid for cid in cited_ids if cid not in retrieved_chunk_ids]
    return {
        "ok": len(invalid) == 0,
        "invalid_citations": invalid,
    }
```

### Failure Analysis Categories

| Failure Type | Meaning                                    |
| ------------ | ------------------------------------------ |
| ingestion    | 文档解析失败、PDF 表格丢失、编码错误。     |
| chunking     | chunk 太短或太长，答案证据被切碎。         |
| retrieval    | 没有检索到相关 chunk。                     |
| rerank       | reranker 把相关 chunk 排低。               |
| citation     | 引用了不存在或无关的 source。              |
| synthesis    | 检索正确但回答总结错误。                   |
| abstention   | 应该回答但错误拒答，或应该拒答但编造答案。 |

### Acceptance Criteria

- 支持 embedding + keyword hybrid retrieval。
- 有 citation verifier。
- 至少 20 个 RAG eval cases，其中包含 5 个 unanswerable cases。
- eval 结果记录 success rate、failure type、latency、cost、retrieved chunk ids。
- README 中展示至少 3 个失败案例和修复思路。
- 能解释为什么你的 RAG 方案不是简单框架 demo。
- 通过 Gate B 后才允许启动第三项目。

---

## Stage 6: Conditional Third Project — Coding Review Agent 或 Web Research Agent（二选一）

目标：在两个 P0 项目已经稳定的前提下，做一个更贴近实习岗位的应用型 Agent 项目。

启动条件：

```text
只有同时满足以下条件才做 Stage 6：
1. Agent Harness Mini 已有 CLI、trace、eval runner，并能说明 permission gate 为什么留到应用型项目实现。
2. RAG / Research Agent 已有 citation verifier、20+ eval cases、5+ unanswerable cases。
3. 两个 P0 项目的 README 都能让别人独立跑通。
```

如果不满足，直接跳过 Stage 6，把时间投入两个 P0 项目的复现环境、README、失败分析和面试表达。

你不需要两个都做。根据个人背景选择一个：

```text
如果你更想投 AI 工程 / 软件工程 Agent：选 Coding Review Agent。
如果你更想投 LLM 应用 / 知识工作流 / research assistant：选 Web Research Agent。
```

---

### Option A: Coding Review Agent

#### Feature Scope

- 读取 Git diff。
- 识别潜在 bug、security risk、test gap、maintainability issue。
- 可选：调用 linter / unit tests。
- 输出结构化 review。
- 支持 CLI 或 GitHub Action。
- 记录 trace。
- 评估误报和漏报。

#### Checklist

- [ ] 解析 diff。
- [ ] 按文件和风险类型分类。
- [ ] 调用静态检查工具或测试命令。
- [ ] 输出 JSON + Markdown review。
- [ ] 记录 trace。
- [ ] 对误报和漏报做失败分析。

#### Must Read

1. GitHub Actions Documentation重点看：workflow、event、job、step。目标是让 review agent 能跑在 PR 流程里。
2. SWE-bench Paper重点看：真实 GitHub issue 修复任务为什么难。只读 abstract、introduction、benchmark setup。
3. SWE-agent Paper
   重点看：agent-computer interface、shell/file interaction、feedback loop。

#### Output Schema

```json
{
  "severity": "high | medium | low",
  "file": "path/to/file.py",
  "line": 42,
  "risk_type": "bug | security | test_gap | maintainability",
  "reason": "...",
  "suggested_fix": "..."
}
```

#### Acceptance Criteria

- 能在至少 3 个小型开源项目 diff 上运行。
- 输出包含 severity、location、reason、suggested_fix。
- 至少 20 个 review eval cases。
- README 中解释设计权衡：为什么需要 Agent，而不是普通 linter。
- 能解释误报和漏报如何评估。

---

### Option B: Web Research Agent

#### Feature Scope

- 根据用户问题拆分 search queries。
- 搜索多个来源。
- 过滤低质量来源。
- 提取证据。
- 生成带引用的 research brief。
- 支持 unanswerable / conflicting evidence。
- 记录 trace。
- 评估 source quality 和 citation accuracy。

#### Checklist

- [ ] Query decomposition。
- [ ] Search tool integration。
- [ ] Source selection。
- [ ] Evidence extraction。
- [ ] Citation formatting。
- [ ] Conflicting evidence handling。
- [ ] Research report synthesis。
- [ ] Eval cases。

#### Output Format

```text
# Research Brief

## Question
...

## Answer
...

## Evidence
1. Claim A — Source 1
2. Claim B — Source 2

## Uncertainty
...

## Sources Used
...
```

#### Acceptance Criteria

- 至少 20 个 research eval cases。
- 每个结论必须有来源。
- 能处理冲突来源。
- 能在证据不足时拒答。
- README 中展示 source selection 规则。
- 能解释 search agent 和普通 RAG 的区别。

### Fallback If Stage 6 Is Cancelled

如果第三项目被取消，Week 10-12 改为：

```text
1. 补齐 Agent Harness Mini 的 tests、trace viewer、README、examples。
2. 补齐 RAG / Research Agent 的 eval result、failure-analysis.md、citation verifier demo。
3. 做一个 5 分钟项目演示脚本：输入、工具调用、trace、eval failure、设计取舍。
4. 不新开项目，不写泛博客，不补复杂 MCP。
```

这个 fallback 不是失败，而是求职信号优化：两个完整项目的可信度高于三个未闭环项目。

---

## Stage 7: Lightweight Skills / MCP

目标：了解现代 Agent 生态，但不深挖。

启动条件：只有两个 P0 项目稳定，且 Stage 6 已完成或明确取消后，才投入 1-2 天做这个轻量展示。

### Checklist

- [ ] 理解 Skill 和 Tool 的区别。
- [ ] 理解 MCP 解决什么问题。
- [ ] 写一个简单 `SKILL.md`。
- [ ] 写一个最小 MCP-style tool adapter。

### Must Read

1. Model Context Protocol: Introduction重点看：MCP 为什么被称为 AI application 的 “USB-C”，它解决的是模型与外部工具/数据源连接标准化问题。
2. Anthropic: Introducing the Model Context Protocol重点看：MCP client、MCP server、data sources、tools 的关系。
3. Claude Code Skills
   重点看：skill 文件结构、description、触发机制、脚本和资源如何组织。

### Minimal SKILL.md

```text
name: code-review
when_to_use: when reviewing a Git diff for bugs, risks, and missing tests
steps:
  1. parse diff
  2. identify risky changes
  3. run available checks
  4. produce structured review
validation:
  - output includes severity, file, line, reason, suggested_fix
```

### Minimal MCP-style Adapter

```text
agent -> tool adapter -> local function / file / database -> result -> agent
```

不要求完整实现 MCP 协议；九月前知道它解决什么问题即可。

### Acceptance Criteria

- 一个 `SKILL.md` 包含 description、when to use、steps、validation。
- 一个脚本或模板能被 skill 使用。
- 有 smoke test 证明 skill 有用。
- 能解释 Tool、Skill、MCP 三者区别。

---

# 5. Evaluation And Safety

目标：让项目看起来像工程系统，而不是 demo。

本路线中 eval 不是最后一周补材料，而是从 Stage 1 开始持续维护。

eval 的优先级不是单纯追数量，而是先覆盖失败类型。数量是下限，覆盖面才是质量。

## Eval Requirements By Stage

| Stage   | Minimum Eval Cases | Focus                                                   |
| ------- | -----------------: | ------------------------------------------------------- |
| Stage 1 |                  5 | tool call 是否正确，loop 是否停止。                     |
| Stage 2 |                 10 | 工具错误、timeout、retry。                              |
| Stage 3 |                 15 | harness regression、trace、CLI。                        |
| Stage 4 |                 20 | RAG answerability、citation。                           |
| Stage 5 |                20+ | hybrid retrieval、citation verifier、failure analysis。 |
| Stage 6 |                 20 | coding review 或 web research 的应用评测。              |

最低覆盖要求：

```text
Harness eval:
- 正常工具调用
- 工具参数错误
- 工具 timeout
- max_steps exceeded

RAG eval:
- answerable
- unanswerable
- ambiguous
- multi-hop
- citation mismatch
- retrieved evidence insufficient
- document prompt injection
```

安全要求按阶段前移：

| Stage   | Minimum Safety Requirement                            |
| ------- | ----------------------------------------------------- |
| Stage 1 | max_steps、工具异常不会崩溃                           |
| Stage 2 | timeout、retry、工具错误归一化                        |
| Stage 3 | trace 记录 tool failure / max_steps / retry           |
| Stage 4 | retrieved content 不得覆盖系统指令                    |
| Stage 5 | citation verifier、abstention policy                  |
| Stage 6 | shell / linter / web search 需要 sandbox 或 allowlist |

## Eval Case Template

```yaml
- id: rag_001
  task: "What does doc A say about tool calling?"
  expected_behavior: "answer with citation from doc A"
  expected_tools: ["retrieve"]
  disallowed_tools: []
  success_criteria:
    - "contains citation"
    - "does not cite non-retrieved source"
    - "does not invent unsupported claim"
```

## Eval Result Template

```csv
id,success,failure_type,tool_calls,latency_ms,cost_usd,notes
rag_001,true,none,1,2300,0.01,passed
```

## Failure Taxonomy

| Failure Type | Meaning                                      |
| ------------ | -------------------------------------------- |
| prompt       | 指令不清或格式失控。                         |
| tool         | 工具异常、超时或输出错误。                   |
| retrieval    | 没检索到相关信息。                           |
| citation     | 引用了不存在或无关的来源。                   |
| model        | 推理错误或不稳定。                           |
| state        | session / memory 污染。                      |
| permission   | 后续应用型项目中的权限拒绝或危险操作未确认。 |
| context      | 上下文过长、截断、错误压缩。                 |
| cost         | 成本过高，不适合实际运行。                   |
| latency      | 响应太慢，不适合交互式使用。                 |

## Trace Requirements

每次 Agent 运行至少记录：

- run_id
- timestamp
- user task
- model name
- system / developer instruction hash
- step number
- LLM request metadata
- tool call name
- tool call arguments
- tool result
- error type
- latency
- cost estimate
- final answer
- eval result if applicable

## Safety Boundary Template

| Risky Action     | Required Control                        |
| ---------------- | --------------------------------------- |
| 删除文件         | dry-run + path allowlist + confirmation |
| 写文件           | workspace allowlist + diff preview      |
| 发邮件 / 发帖    | human approval + recipient allowlist    |
| shell 执行       | sandbox + timeout + command denylist    |
| 外部网页操作     | 不登录敏感账号，不绕过平台规则          |
| RAG 文档指令注入 | 不执行 retrieved content 中的指令       |
| 读取私密文件     | explicit permission + path allowlist    |
| 网络请求         | domain allowlist + rate limit           |

---

# 6. Revised 14-Week Schedule

假设从 5 月下旬开始，到 9 月初投递实习。

| Week    | Focus                                                                   | Output                                                           | Main Resources                                              |
| ------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------- |
| Week 1  | Agent 边界、workflow vs agent、minimal loop skeleton                    | `notes/when-to-use-agent.md` + `agent-harness-mini` skeleton | Anthropic Building Effective Agents; OpenAI Practical Guide |
| Week 2  | Function calling、structured output、2-3 个工具、5 条 eval              | Agent Harness Mini v0                                            | OpenAI Function Calling; Claude Tool Use                    |
| Week 3  | Tool registry、schema、timeout、retry、error handling                   | Agent Harness Mini v1                                            | OpenAI Tools; OpenAI Agents SDK Tools                       |
| Week 4  | JSONL trace、tool failure eval、10 条 eval cases                        | Harness trace + eval v0                                          | OpenAI Tracing; LangSmith Evaluation concepts               |
| Week 5  | CLI、session state、context management、eval runner、15 条 eval         | Agent Harness Mini v2；通过 Gate A                               | LangGraph Overview; OpenAI Agents SDK                       |
| Week 6  | RAG ingestion、chunking、embedding retrieval、basic trace               | RAG pipeline v0                                                  | LlamaIndex RAG; LangChain RAG concepts                      |
| Week 7  | Citation formatting、empty retrieval、20 条 RAG eval、5 条 unanswerable | RAG Agent v0                                                     | LlamaIndex Starter; RAG evaluation notes                    |
| Week 8  | Hybrid retrieval、rerank、citation verifier                             | RAG Agent v1                                                     | RAGFlow / Onyx optional                                     |
| Week 9  | RAG failure analysis、README、examples、eval result；通过 Gate B        | RAG project polished                                             | Project README, eval results                                |
| Week 10 | 只有通过 Gate C 才启动第三项目；否则 polish 两个 P0 项目                | Third project skeleton 或 core project hardening                 | GitHub Actions / SWE-bench 或 README/eval/trace             |
| Week 11 | 第三项目 v1；或继续补 P0 项目的测试、examples、复现环境                 | Third project v1 或 stronger P0 repos                            | SWE-agent / OpenHands 或 Docker/pytest                      |
| Week 12 | 项目工程化、Docker/uv、examples、smoke tests、演示脚本                  | Two strong runnable projects                                     | Docker, pytest, README                                      |
| Week 13 | 简历、项目文章、面试准备                                                | Resume + project writeup                                         | 本文档 Interview Questions                                  |
| Week 14 | 模拟面试、投递、查漏补缺                                                | Application package                                              | 项目复盘、失败分析                                          |

执行约束：

```text
如果 Week 5 结束时 Agent Harness Mini 没有 CLI / trace / eval runner，不进入 RAG 深度开发，先补 Harness。
如果 Week 9 结束时 RAG 没有 citation verifier / 20+ eval / 5+ unanswerable cases，不做第三个项目。
如果 Week 10 开始时两个 P0 项目的 README 不能独立跑通，不做第三个项目。
如果 Week 12 时两个主项目 README 不完整，不写博客，先补 README、examples、eval result、failure analysis。
MCP / Skill Demo 永远不能挤占两个 P0 项目的时间。
```

---

# 7. Minimal Resource List

只保留少量高价值资源。不要横向刷太多。

## Must Read

| Resource                                     | Use                                         |
| -------------------------------------------- | ------------------------------------------- |
| Anthropic: Building Effective Agents         | 理解 workflow / agent 边界。                |
| OpenAI: A Practical Guide to Building Agents | 理解 Agent 产品和工程落地。                 |
| OpenAI Function Calling                      | 学工具调用。                                |
| OpenAI Using Tools                           | 学工具体系。                                |
| Claude Tool Use                              | 对比工具调用设计。                          |
| LlamaIndex RAG                               | 学 RAG 主线。                               |
| LangChain RAG Concepts                       | 理解 RAG 组件边界。                         |
| LangGraph Overview                           | 学 stateful orchestration 和 harness 设计。 |
| OpenAI Agents SDK Tracing                    | 学 trace 和 observability。                 |
| OpenAI Evals / Agent Evals                   | 学 eval case、grader、regression tracking。 |
| Model Context Protocol Intro                 | 理解 MCP 的问题域。                         |

## Optional Frameworks

| Framework         | When To Use                                                   |
| ----------------- | ------------------------------------------------------------- |
| LangGraph         | 学 stateful orchestration、human-in-the-loop、可恢复执行。    |
| LlamaIndex        | 快速做 RAG / document QA。                                    |
| OpenAI Agents SDK | 学现代 agent SDK 的抽象、handoff、guardrails、tracing。       |
| smolagents        | 学轻量 code-agent 风格。                                      |
| LangSmith         | 学 eval dataset、experiment、evaluator、regression tracking。 |

## Papers: Read Abstract + Key Idea Only

| Paper      | Why                           |
| ---------- | ----------------------------- |
| ReAct      | reasoning + acting 基础范式。 |
| Toolformer | 工具使用思想。                |
| AgentBench | Agent eval 思路。             |
| SWE-bench  | Coding agent 评测方向。       |
| SWE-agent  | 软件工程 agent interface。    |

## Projects To Study Selectively

| Project            | What To Learn                                              |
| ------------------ | ---------------------------------------------------------- |
| GPT Researcher     | research agent、搜索、引用、报告生成。                     |
| Open Deep Research | 多轮搜索、状态、引用。                                     |
| OpenHands          | coding agent、shell、测试、软件工程任务。                  |
| SWE-agent          | agent-computer interface。                                 |
| LangGraph Examples | state graph、可控编排。                                    |
| smolagents         | code-agent 风格和轻量实现。                                |
| Onyx               | 企业级 search assistant、connectors、权限、hybrid search。 |
| RAGFlow            | 文档理解型 RAG 的 ingestion、chunking、retrieval。         |

---

# 8. Resume-Oriented Deliverables

到九月初，至少应有以下材料：

```text
projects/
  agent-harness-mini/          # P0 required
  rag-research-agent/          # P0 required
  coding-review-agent/         # P1 optional only if Gate C passed
  web-research-agent/          # P1 optional alternative
  skills-demo/                 # P2 optional light demo only after P0 stabilized

docs/
  when-to-use-agent.md
  failure-analysis.md
  safety-boundaries.md
  architecture-notes.md
  project-retrospective.md

evals/
  cases.yaml
  results.csv
```

每个核心项目 README 必须包含：

- 项目目标。
- 为什么需要 Agent。
- 架构图或模块图。
- 如何运行。
- 示例输入输出。
- eval 结果。
- trace 示例。
- 已知失败案例。
- 安全边界。
- 后续改进。

---

# 9. README Template For Each Project

每个项目都应使用类似结构：

```markdown
# Project Name

## 1. Problem

这个项目解决什么问题？为什么普通 workflow / script 不够？

## 2. Agent Boundary

哪些部分由 Agent 决策？哪些部分是确定性 workflow？

## 3. Architecture

模块图：LLM、tools、state、trace、eval、retrieval，以及后续可扩展的 permission / sandbox 模块。

## 4. Features

- Feature A
- Feature B
- Feature C

## 5. Quick Start

```bash
pip install -e .
agent run "..."
agent eval evals/cases.yaml
```

## 6. Example

输入、工具调用、输出、trace 片段。

## 7. Evaluation

eval cases、results、failure types、known failures。

## 8. Safety

权限控制、危险动作、限制。

## 9. Design Tradeoffs

为什么这样设计？替代方案是什么？

## 10. Limitations

不能做什么？什么情况下会失败？

## 11. Future Work

下一步如何改进？

```

---

# 10. Resume Bullet Templates

必须根据真实项目改写，不能虚构。

## Agent Harness Mini

```text
Built a minimal Python agent harness with structured tool calling, tool registry, timeout/retry handling, JSONL tracing, CLI execution, and regression eval runner.
```

## RAG / Research Agent

```text
Developed a document-grounded research agent supporting ingestion, chunking, hybrid retrieval, citation-based answers, citation verification, abstention on insufficient evidence, and 20+ evaluation cases.
```

## Coding Review Agent

只有真实完成该项目时才使用：

```text
Implemented a coding review agent that analyzes Git diffs, ranks bug/security/test risks, invokes static checks, and generates structured review reports with trace logs and failure analysis.
```

## Web Research Agent

只有真实完成该项目时才使用：

```text
Built a web research agent that decomposes research questions, selects sources, extracts evidence, resolves conflicting claims, and generates citation-grounded research briefs with evaluation traces.
```

## Evaluation

```text
Designed an agent evaluation suite tracking success rate, failure type, tool-call count, latency, and cost across fixed regression tasks.
```

---

# 11. Interview Questions You Should Be Able To Answer

## Agent Basics

- 什么是 Agent？它和 workflow / chatbot 的区别是什么？
- 什么时候不应该用 Agent？
- ReAct 的核心思想是什么？
- 为什么“能聊天”不等于“是 Agent”？

## Tool Calling

- tool schema 怎么设计？
- 工具调用失败怎么办？
- 如何避免重复调用和死循环？
- 什么时候需要给危险工具加权限控制？
- tool registry 的职责是什么？
- retry 和 timeout 应该放在哪里？

## Harness

- agent loop 的核心状态有哪些？
- trace 应该记录什么？
- session 和 memory 有什么区别？
- context 太长怎么办？
- permission gate 适合留在哪类工具或项目中实现？
- 为什么需要 CLI 和 eval runner？

## RAG

- chunk size 怎么选？
- embedding retrieval 和 keyword retrieval 的区别是什么？
- hybrid retrieval 为什么有用？
- rerank 解决什么问题？
- 如何防止 hallucinated citations？
- 检索为空时应该怎么回答？
- citation verifier 怎么实现？

## Evaluation

- 怎么评估一个 Agent？
- 你的 eval cases 怎么设计？
- 失败类型如何分类？
- prompt 改动后如何防止能力退化？
- 如何衡量 false positive 和 false negative？
- 如何记录 latency 和 cost？

## Coding Agent

- coding agent 为什么需要 shell / file tools？
- 如何防止危险命令？
- coding review agent 和普通 linter 的区别是什么？
- 如何衡量 review agent 的误报和漏报？

## Research Agent

- research agent 和普通搜索有什么区别？
- 如何判断 source quality？
- 冲突来源怎么处理？
- 什么情况下应该拒答？

---

# 12. What Not To Do

九月前不要做这些：

- 不要把时间花在收集大量 awesome-list 上。
- 不要同时学太多框架。
- 不要只做 prompt demo。
- 不要做没有 eval 的 Agent。
- 不要过早做复杂 multi-agent。
- 不要把 role-play crew 当成主线。
- 不要只会调 LangChain，而不会手写 Agent loop。
- 不要忽视 README、测试、日志、Docker、失败分析。
- 不要为了追热点深挖 MCP、A2A、ACP，而主项目跑不起来。
- 不要用模型自由生成 citations。
- 不要把安全边界留到最后再补。

---

# 13. Final Checklist Before Applying

投递前检查：

- [ ] 至少 2 个核心项目可以运行。
- [ ] 每个项目有清晰 README。
- [ ] 每个项目有 examples。
- [ ] 至少一个项目有 eval runner。
- [ ] 至少一个项目有 trace log。
- [ ] 至少一个应用型项目能说明或实现 permission gate / sandbox / allowlist 等安全边界。
- [ ] RAG 项目有 citation verifier。
- [ ] RAG 项目有 unanswerable eval cases。
- [ ] 简历中没有虚构能力。
- [ ] 能讲清楚每个项目失败在哪里。
- [ ] 能讲清楚为什么你的方案需要 Agent。
- [ ] 能讲清楚哪些部分其实不需要 Agent。
- [ ] 能讲清楚如果继续做，会如何改进。
- [ ] 能现场解释一次 trace。
- [ ] 能解释一次 eval failure。

---

# 14. Suggested Final Positioning

九月初你的求职定位可以是：

```text
CS undergraduate focused on LLM agent engineering. Built a minimal agent harness and a document-grounded RAG agent with structured tool calling, tracing, evaluation, citation verification, and failure analysis.
```

更短版本：

```text
LLM agent engineering candidate with hands-on experience in tool calling, RAG, tracing, evals, and failure analysis.
```

中文口径：

```text
我不是只会调框架 API，而是能实现一个最小 Agent harness，包括工具注册、状态管理、trace、eval 和失败分析；同时能把这套机制应用到 RAG 或代码审查等具体场景里，并说明安全边界应如何扩展。
```

---

# 15. Execution Rule

整个路线的执行标准只有一个：

```text
每周必须留下可以运行、可以测试、可以解释的产出。
```

优先级规则：

```text
P0 项目闭环 > P1 第三项目 > P2 MCP / Skill 展示 > 博客和泛资源阅读
```

如果某个学习任务不能转化为代码、eval、trace、README、failure analysis 或面试表达，就降低优先级。

最终目标不是“学完 Agent”，而是：

```text
拿出两个能证明工程能力的 Agent 项目，并能清楚解释它们为什么这样设计、在哪里会失败、如何评估和改进。
```
