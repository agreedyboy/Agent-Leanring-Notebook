from pathlib import Path

from agent_harness_mini.cli import (
    DEFAULT_EVAL_OUTPUT_PATH,
    DEFAULT_SYSTEM_PROMPT,
    build_parser,
    build_session,
)


def test_cli_run_parser_accepts_prompt_and_options():
    parser = build_parser()

    args = parser.parse_args(
        [
            "run",
            "What is the weather in Hefei?",
            "--provider",
            "KIMI",
            "--max-steps",
            "2",
            "--trace",
            ".traces/test.jsonl",
            "--no-trace-content",
        ]
    )

    assert args.command == "run"
    assert args.prompt == "What is the weather in Hefei?"
    assert args.provider == "KIMI"
    assert args.max_steps == 2
    assert args.trace == Path(".traces/test.jsonl")
    assert args.no_trace_content is True


def test_cli_run_parser_uses_default_system_prompt():
    parser = build_parser()

    args = parser.parse_args(["run", "Hello"])

    assert args.system == DEFAULT_SYSTEM_PROMPT
    assert args.max_steps == 3
    assert args.provider == "DEEPSEEK"
    assert args.trace == Path(".traces/run_basic.jsonl")


def test_cli_eval_parser_accepts_cases_path_and_options():
    parser = build_parser()

    args = parser.parse_args(
        [
            "eval",
            "evals/cases.yaml",
            "--provider",
            "KIMI",
            "--output",
            "evals/results.csv",
        ]
    )

    assert args.command == "eval"
    assert args.cases_path == Path("evals/cases.yaml")
    assert args.provider == "KIMI"
    assert args.output == Path("evals/results.csv")


def test_cli_eval_parser_uses_default_options():
    parser = build_parser()

    args = parser.parse_args(["eval", "evals/cases.yaml"])

    assert args.command == "eval"
    assert args.provider == "DEEPSEEK"
    assert args.output == DEFAULT_EVAL_OUTPUT_PATH


def test_build_session_adds_system_and_user_messages():
    session = build_session("System prompt.", "User prompt.")

    assert session.messages == [
        {"role": "system", "content": "System prompt."},
        {"role": "user", "content": "User prompt."},
    ]
