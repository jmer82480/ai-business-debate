"""Concrete LLM client wrapping the Anthropic SDK."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import anthropic

from debate.config import DebateConfig, estimate_cost
from debate.llm.client import LLMResponse

logger = logging.getLogger(__name__)


class AnthropicTransportError(Exception):
    """Retryable transport/provider error."""


class AnthropicValidationError(Exception):
    """Non-retryable schema/validation error."""


class AnthropicClient:
    """Calls the Anthropic Messages API with retry and web_search support."""

    def __init__(self, config: DebateConfig) -> None:
        self._client = anthropic.Anthropic()
        self._config = config

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        model: str | None = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Call the API with retry for transport errors."""
        resolved_model = model or self._config.model_default
        all_tools = list(tools or [])

        if self._config.web_search_enabled:
            all_tools.append({"type": "web_search_20250305", "name": "web_search"})

        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if all_tools:
            kwargs["tools"] = all_tools
        if tool_choice:
            # When web_search is present, forcing a specific tool prevents the
            # model from doing research first. Relax to "any" so the model can
            # use web_search internally before calling the required tool.
            has_web_search = any(
                t.get("type", "").startswith("web_search") for t in all_tools
            )
            if has_web_search and tool_choice.get("type") == "tool":
                kwargs["tool_choice"] = {"type": "any"}
            else:
                kwargs["tool_choice"] = tool_choice

        last_error: Exception | None = None
        for attempt in range(1, self._config.max_retries_per_step + 1):
            try:
                # Use streaming for large max_tokens to avoid SDK timeout
                # rejection (>10 min estimate). get_final_message() collects
                # the full response identically to messages.create().
                if max_tokens > 16384:
                    with self._client.messages.stream(**kwargs) as stream:
                        response = stream.get_final_message()
                else:
                    response = self._client.messages.create(**kwargs)
                return self._parse_response(response, resolved_model)
            except anthropic.RateLimitError as e:
                last_error = e
                # Rate limits need a much longer backoff (60s base)
                delay = 60.0 * attempt
                logger.warning(
                    "Rate limited (attempt %d/%d), waiting %.0fs: %s",
                    attempt,
                    self._config.max_retries_per_step,
                    delay,
                    e,
                )
                if attempt < self._config.max_retries_per_step:
                    time.sleep(delay)
            except (
                anthropic.APITimeoutError,
                anthropic.APIConnectionError,
                anthropic.InternalServerError,
            ) as e:
                last_error = e
                logger.warning(
                    "Transport error (attempt %d/%d): %s",
                    attempt,
                    self._config.max_retries_per_step,
                    e,
                )
                if attempt < self._config.max_retries_per_step:
                    time.sleep(self._config.retry_delay_seconds * attempt)
            except anthropic.BadRequestError as e:
                raise AnthropicValidationError(str(e)) from e

        raise AnthropicTransportError(
            f"Failed after {self._config.max_retries_per_step} attempts: {last_error}"
        )

    def _parse_response(self, response: Any, model: str) -> LLMResponse:
        """Extract text and tool_use from the API response."""
        text_parts: list[str] = []
        tool_use_data: dict[str, Any] | None = None
        tool_name = ""

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_use_data = block.input
                tool_name = block.name

        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        return LLMResponse(
            text="\n".join(text_parts),
            tool_use=tool_use_data,
            tool_name=tool_name,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            raw_response=json.dumps(
                {"id": response.id, "model": response.model, "stop_reason": response.stop_reason},
            ),
            stop_reason=response.stop_reason or "",
        )
