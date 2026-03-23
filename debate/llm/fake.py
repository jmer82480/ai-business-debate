"""Fake LLM client for testing — returns canned or callable responses."""

from __future__ import annotations

from typing import Any, Callable

from debate.llm.client import LLMResponse


class FakeLLMClient:
    """Returns pre-configured responses. Useful for tests and dry-run mode."""

    def __init__(
        self,
        responses: list[LLMResponse] | None = None,
        response_fn: Callable[..., LLMResponse] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._response_fn = response_fn
        self._call_index = 0
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        model: str | None = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Record the call and return the next canned response."""
        self.calls.append(
            {
                "messages": messages,
                "system": system,
                "tools": tools,
                "tool_choice": tool_choice,
                "model": model,
                "max_tokens": max_tokens,
            }
        )

        if self._response_fn is not None:
            return self._response_fn(
                messages=messages,
                system=system,
                tools=tools,
                model=model,
                call_index=self._call_index,
            )

        if self._call_index < len(self._responses):
            resp = self._responses[self._call_index]
        else:
            resp = LLMResponse(
                text="[FAKE] No more canned responses.",
                model=model or "fake",
                tokens_in=100,
                tokens_out=50,
            )

        self._call_index += 1
        return resp
