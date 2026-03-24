"""Base role adapter — common logic for all debate agents."""

from __future__ import annotations

import json
import logging
from typing import Any

from debate.config import DebateConfig, estimate_cost
from debate.llm.client import LLMClient, LLMResponse
from debate.prompts.system import SYSTEM_PROMPTS

logger = logging.getLogger(__name__)


class RoleError(Exception):
    """Base error for role adapter failures."""


class ValidationFailure(RoleError):
    """LLM returned structurally invalid output."""


class BadOutputError(RoleError):
    """LLM returned parseable but logically bad output (needs reprompt)."""


class BaseRole:
    """ABC for debate role adapters. Subclasses set role_name."""

    role_name: str = ""

    def __init__(self, client: LLMClient, config: DebateConfig) -> None:
        self._client = client
        self._config = config
        self._last_debug: str | None = None  # set after every LLM call for failure diagnosis

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPTS[self.role_name]

    def _call_llm(
        self,
        user_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        model: str | None = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Call the LLM with the role's system prompt."""
        messages = [{"role": "user", "content": user_prompt}]

        response = self._client.complete(
            messages=messages,
            system=self.system_prompt,
            tools=tools,
            tool_choice=tool_choice,
            model=model or self._config.model_default,
            max_tokens=max_tokens,
        )

        logger.info(
            "[%s] tokens_in=%d tokens_out=%d cost=$%.4f",
            self.role_name,
            response.tokens_in,
            response.tokens_out,
            estimate_cost(
                response.model or self._config.model_default,
                response.tokens_in,
                response.tokens_out,
            ),
        )

        self._last_debug = self._get_raw_for_debug(response)
        return response

    def _extract_tool_data(self, response: LLMResponse, expected_tool: str) -> dict[str, Any]:
        """Extract and validate tool_use data from response."""
        if response.stop_reason == "max_tokens":
            raise ValidationFailure(
                f"[{self.role_name}] Response truncated (stop_reason=max_tokens, "
                f"{response.tokens_out} tokens). Increase max_tokens or simplify output."
            )
        if response.tool_use is None:
            raise ValidationFailure(
                f"[{self.role_name}] Expected tool_use '{expected_tool}' "
                f"but got text response: {response.text[:200]}"
            )
        if response.tool_name != expected_tool:
            raise ValidationFailure(
                f"[{self.role_name}] Expected tool '{expected_tool}' "
                f"but got '{response.tool_name}'"
            )
        return response.tool_use

    def _get_raw_for_debug(self, response: LLMResponse) -> str:
        """Serialize response for debug artifact storage."""
        return json.dumps(
            {
                "text": response.text[:5000],
                "tool_name": response.tool_name,
                "tool_use": response.tool_use,
                "model": response.model,
                "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out,
                "stop_reason": response.stop_reason,
            },
            indent=2,
            default=str,
        )
