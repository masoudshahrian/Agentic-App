"""Environment-based configuration. Secrets only ever come from the environment."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_MODEL = "google/gemma-4-31b-it:free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
SUPPORTED_PROVIDERS = ("openrouter",)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    provider: str
    api_key: str = ""
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    temperature: float = 0.2
    timeout_seconds: float = 90.0
    max_retries: int = 4

    def __repr__(self) -> str:  # never leak the key in logs/tracebacks
        return f"Settings(provider={self.provider!r}, model={self.model!r}, api_key=<hidden>)"


def _number(env: Mapping[str, str], name: str, default: float, cast: type) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from None


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Read settings from ``env`` (default: ``.env`` file + process environment)."""
    if env is None:
        load_dotenv()
        env = os.environ
    provider = env.get("LLM_PROVIDER", "openrouter").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ConfigError(f"LLM_PROVIDER={provider!r} is not supported (use one of {SUPPORTED_PROVIDERS})")
    api_key = env.get("OPENROUTER_API_KEY", "").strip()
    if not api_key or api_key == "your_openrouter_api_key":
        raise ConfigError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your free OpenRouter key."
        )
    return Settings(
        provider=provider,
        api_key=api_key,
        model=env.get("LLM_MODEL", "").strip() or DEFAULT_MODEL,
        base_url=env.get("OPENROUTER_BASE_URL", "").strip() or DEFAULT_BASE_URL,
        temperature=float(_number(env, "LLM_TEMPERATURE", 0.2, float)),
        timeout_seconds=float(_number(env, "LLM_TIMEOUT_SECONDS", 90.0, float)),
        max_retries=int(_number(env, "LLM_MAX_RETRIES", 4, int)),
    )
