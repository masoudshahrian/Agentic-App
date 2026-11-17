"""Thin LLM wrapper: one method, `complete(system, user) -> str`.

Graph nodes depend only on the `LLM` protocol, so tests inject a fake and the real
OpenRouter client is created lazily. Provider errors are mapped to `LLMError` with
messages that never contain credentials.
"""
from __future__ import annotations

from typing import Protocol

from app.config import Settings


class LLMError(RuntimeError):
    """Any failure to obtain a completion (network, rate limit, auth, empty reply)."""


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenRouterLLM:
    """OpenRouter (OpenAI-compatible) chat model through langchain-openai."""

    def __init__(self, settings: Settings) -> None:
        from langchain_openai import ChatOpenAI  # imported lazily: tests never need it

        self._model = settings.model
        self._client = ChatOpenAI(
            model=settings.model,
            api_key=settings.api_key,
            base_url=settings.base_url,
            temperature=settings.temperature,
            timeout=settings.timeout_seconds,
            max_retries=settings.max_retries,  # exponential back-off on 429 / transient errors
        )

    def complete(self, system: str, user: str) -> str:
        import openai
        from langchain_core.messages import HumanMessage, SystemMessage

        try:
            message = self._client.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        except openai.RateLimitError:
            raise LLMError(f"rate limit reached for {self._model} (free tier); retry in a minute") from None
        except openai.AuthenticationError:
            raise LLMError("authentication failed: check OPENROUTER_API_KEY") from None
        except openai.APITimeoutError:
            raise LLMError("the model request timed out") from None
        except openai.APIConnectionError:
            raise LLMError("could not reach the provider (network error)") from None
        except openai.APIStatusError as exc:
            raise LLMError(f"provider returned HTTP {exc.status_code}") from None
        except openai.OpenAIError as exc:
            raise LLMError(f"LLM call failed: {type(exc).__name__}") from None

        content = message.content
        if isinstance(content, list):  # content blocks -> plain text
            content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
        text = (content or "").strip()
        if not text:
            raise LLMError("the model returned an empty reply")
        return text
