from pathlib import Path

import pytest

from agent_harness_mini.config import ConfigError, ModelConfig, load_model_config


def clear_config_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "MODEL_PROVIDER",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_MODEL_ID",
        "DEEPSEEK_BASE_URL",
        "KIMI_API_KEY",
        "KIMI_MODEL_ID",
        "KIMI_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def write_env(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_selected_provider_from_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clear_config_environment(monkeypatch)
    env_path = write_env(
        tmp_path / ".env",
        "\n".join(
            [
                "KIMI_API_KEY=test-secret",
                "KIMI_MODEL_ID=kimi-test",
                "KIMI_BASE_URL=https://example.invalid/v1",
            ]
        ),
    )

    config = load_model_config("kimi")

    assert config == ModelConfig(
        provider="KIMI",
        api_key="test-secret",
        model_id="kimi-test",
        base_url="https://example.invalid/v1",
    )
    assert "test-secret" not in repr(config)


def test_reads_provider_choice_from_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clear_config_environment(monkeypatch)
    monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
    env_path = write_env(
        tmp_path / ".env",
        "\n".join(
            [
                "DEEPSEEK_API_KEY=test-secret",
                "DEEPSEEK_MODEL_ID=deepseek-test",
                "DEEPSEEK_BASE_URL=https://example.invalid/v1",
            ]
        ),
    )

    config = load_model_config()

    assert config.provider == "DEEPSEEK"
    assert config.model_id == "deepseek-test"


def test_raises_clear_error_when_required_value_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clear_config_environment(monkeypatch)
    env_path = write_env(
        tmp_path / ".env",
        "\n".join(
            [
                "DEEPSEEK_API_KEY=test-secret",
                "DEEPSEEK_MODEL_ID=deepseek-test",
            ]
        ),
    )

    with pytest.raises(ConfigError, match="DEEPSEEK_BASE_URL"):
        load_model_config("DEEPSEEK")
