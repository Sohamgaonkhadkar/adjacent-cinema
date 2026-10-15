"""Shared LLM provider abstraction (M13.12).

One implementation, two consumers: the evaluation harness (Condition A
baseline) and the optional Role-B synthesis layer. Roles are kept separate —
this module ONLY talks to a model; it never decides what the agent does and
never touches Qloo execution.

Security rules:
* Credentials come from the environment (ADJACENT_LLM_API_KEY and friends),
  are never hardcoded, never logged, and `redacted()` is the only diagnostic
  view.
* No provider → `LLMUnavailableError`. Callers report BLOCKED honestly; they
  never silently substitute a stub. `StubSynthesisProvider` exists for offline
  tests and is labelled `stub` everywhere it is used.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class LLMUnavailableError(RuntimeError):
    """No provider configured, or the provider call failed."""


@dataclass(frozen=True)
class LLMProviderConfig:
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL

    @classmethod
    def from_env(cls) -> LLMProviderConfig:
        return cls(
            api_key=(os.getenv("ADJACENT_LLM_API_KEY") or "").strip() or None,
            base_url=(os.getenv("ADJACENT_LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            model=os.getenv("ADJACENT_LLM_MODEL") or DEFAULT_MODEL,
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def redacted(self) -> dict[str, Any]:
        """Diagnostic view — NEVER contains the key."""
        return {
            "configured": self.configured,
            "base_url": self.base_url,
            "model": self.model,
            "api_key_present": bool(self.api_key),
        }


class CompletionProvider(Protocol):
    kind: str
    model: str

    def complete(self, system: str, user: str) -> str: ...


class OpenAICompatibleProvider:
    """Minimal chat-completions client. ``transport`` injectable for tests."""

    kind = "live_llm"

    #: Bounded response size (M13.13): a runaway generation must not flood
    #: memory or the validator. 100k chars is far beyond a valid brief.
    MAX_RESPONSE_CHARS = 100_000

    def __init__(
        self,
        config: LLMProviderConfig,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not config.configured:
            raise LLMUnavailableError(
                "ADJACENT_LLM_API_KEY not configured — LLM features are BLOCKED "
                "(never silently stubbed)."
            )
        self.config = config
        self.model = config.model
        self._transport = transport

    def complete(self, system: str, user: str) -> str:
        kwargs: dict[str, Any] = {"timeout": 60.0}
        if self._transport is not None:
            kwargs["transport"] = self._transport
        try:
            with httpx.Client(**kwargs) as client:
                response = client.post(
                    f"{self.config.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    json={
                        "model": self.config.model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "temperature": 0.2,
                    },
                )
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"provider transport error: {exc}") from exc
        if response.status_code != 200:
            raise LLMUnavailableError(
                f"provider HTTP {response.status_code}"
            )
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailableError("malformed provider response") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMUnavailableError("empty provider completion")
        if len(content) > self.MAX_RESPONSE_CHARS:
            raise LLMUnavailableError(
                f"provider response exceeds {self.MAX_RESPONSE_CHARS}-char bound"
            )
        return content


class StubSynthesisProvider:
    """DETERMINISTIC test stub. Labelled ``stub`` — never a real model result.

    ``response`` may be a JSON-serialisable dict (returned as JSON text), a raw
    string, or an Exception instance (raised) to exercise failure paths.
    """

    kind = "stub"
    model = "deterministic-test-stub"

    def __init__(self, response: Any) -> None:
        self._response = response

    def complete(self, system: str, user: str) -> str:
        import json

        if isinstance(self._response, Exception):
            raise self._response
        if isinstance(self._response, str):
            return self._response
        return json.dumps(self._response)
