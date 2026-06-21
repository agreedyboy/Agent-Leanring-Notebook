# Agent Harness Mini

This is a small learning project for building an agent harness from scratch.
The goal is not to replace a production agent framework. The goal is to make
the core pieces visible and easy to reason about:

- an agent loop
- OpenAI-compatible function calling
- tool abstraction and tool registry
- session state
- context window trimming
- JSONL tracing
- fixed eval cases
- a small CLI for run, chat, and eval

## Current Scope

The project currently supports three built-in tools:

- `get_weather`: checks current weather through Open-Meteo.
- `get_user_profile`: returns a mock user profile.
- `calculate`: multiplies two numbers.

Permission gates, sandboxing, durable storage, token-based context management,
and production timeout isolation are intentionally deferred. This project is a
learning harness, so the current focus is module boundaries and observable
behavior.

## Project Layout

```text
agent_harness_mini/
  cli.py       # command line entry points
  config.py    # provider config from .env / environment variables
  context.py   # context window selection for model calls
  evals.py     # eval case loader, runner, and result writer
  loop.py      # agent loop
  session.py   # session state and run result objects
  tools.py     # Tool, ToolRegistry, ToolResult, built-in tools
  tracing.py   # JSONL and in-memory tracing

evals/
  cases.yaml   # fixed eval cases

examples/
  run_basic.py

tests/
```

## Setup

Install the package in editable mode:

```powershell
pip install -e .
```

Install test dependencies if needed:

```powershell
pip install -e ".[dev]"
```

Create `projects/agent-harness-mini/.env` with one supported provider. Example:

```text
MODEL_PROVIDER=DEEPSEEK
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_MODEL_ID=your_model_id
DEEPSEEK_BASE_URL=https://api.deepseek.com

KIMI_API_KEY=your_api_key
KIMI_MODEL_ID=your_model_id
KIMI_BASE_URL=your_base_url
```

The supported provider names are currently `DEEPSEEK` and `KIMI`.

## Run

Run one task:

```powershell
python -m agent_harness_mini.cli run "What is the weather in Hefei?"
```

Use another provider:

```powershell
python -m agent_harness_mini.cli run "Use the calculate tool to compute 12 times 8." --provider KIMI
```

Start an interactive multi-turn chat session:

```powershell
python -m agent_harness_mini.cli chat
```

Run eval cases:

```powershell
python -m agent_harness_mini.cli eval evals/cases.yaml
```

Write eval results to a custom CSV file:

```powershell
python -m agent_harness_mini.cli eval evals/cases.yaml --output evals/results.csv
```

Run tests:

```powershell
python -m pytest
```

## Trace

The CLI writes JSONL traces by default:

- `run`: `.traces/run_basic.jsonl`
- `chat`: `.traces/chat.jsonl`

Trace events include fields such as:

- `run_id`
- `session_id`
- `event`
- `step`
- `model_id`
- `message_count`
- `session_message_count`
- `tool_name`
- `tool_call_id`
- `ok`
- `error_type`
- `latency_ms`

Tracing is best-effort. If trace writing fails, the agent loop should continue.

## Eval Cases

Eval cases live in `evals/cases.yaml`.

The current suite contains 15 cases covering:

- normal text responses
- cases where tools should not be called
- weather tool calls
- user profile tool calls
- calculate tool calls
- tool failure behavior
- combined profile and weather tool use
- max step termination

Each case can check:

- expected final status
- expected tools
- disallowed tools
- required output substrings
- accepted output substrings
- maximum tool call count

## Design Notes

`AgentSession` stores the full conversation history. `ContextWindow` only
decides which messages are sent to the model for the current call. This keeps
memory storage and context selection separate.

`Tool` does input validation, execution, retry handling, latency tracking, and
conversion into `ToolResult`. `ToolRegistry` owns registration and execution of
model tool calls, including invalid JSON and unknown tool errors.

`EvalRunner` judges behavior using the final answer and trace events. It is a
regression tool, not a perfect semantic grader.

## Current Limitations

- Context management is message-count based, not token-count based.
- Timeout is represented in the tool object but not enforced with hard process
  or thread cancellation.
- Eval checks are substring and tool-call based, so they can miss subtle answer
  quality problems.
- Weather depends on an external network API.
- No permission gate is implemented yet because the current built-in tools are
  low risk.
