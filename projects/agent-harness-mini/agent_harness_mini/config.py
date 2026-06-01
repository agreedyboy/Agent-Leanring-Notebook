"""Runtime configuration for the minimal agent harness."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_ENV_PATH = PROJECT_ROOT / ".env"


DEFAULT_PROVIDER = "DEEPSEEK"
SUPPORTED_PROVIDERS = frozenset({"DEEPSEEK", "KIMI"})


class ConfigError(RuntimeError):
    """Raised when model configuration cannot be constructed."""


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Configuration needed to create one OpenAI-compatible model client."""

    provider: str
    api_key: str = field(repr=False)
    model_id: str
    base_url: str


def load_model_config(
    provider: str | None = None,
) -> ModelConfig:
    """Load one provider's settings from environment variables or dotenv files.

    Process environment values take precedence. When both dotenv files exist,
    ``projects/agent-harness-mini/.env`` takes precedence over ``projects/.env``.
    """

    load_dotenv(dotenv_path=LOCAL_ENV_PATH)

    selected_provider = (
        provider or os.getenv("MODEL_PROVIDER") or DEFAULT_PROVIDER
    ).strip().upper()


    if selected_provider not in SUPPORTED_PROVIDERS:
        choices = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise ConfigError(
            f"Unsupported MODEL_PROVIDER {selected_provider!r}. Choose one of: {choices}."
        )

    variable_names = {
        "api_key": f"{selected_provider}_API_KEY",
        "model_id": f"{selected_provider}_MODEL_ID",
        "base_url": f"{selected_provider}_BASE_URL",
    }
    values = {field_name: os.getenv(name) for field_name, name in variable_names.items()}
    missing = [
        variable_names[field_name]
        for field_name, value in values.items()
        if not value
    ]
    if missing:
        raise ConfigError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return ModelConfig(
        provider=selected_provider,
        api_key=values["api_key"] or "",
        model_id=values["model_id"] or "",
        base_url=values["base_url"] or "",
    )
