"""Protocol definition for the LLM client."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""

    text: str = ""
    tool_use: dict[str, Any] | None = Field(
        default=None, description="Parsed tool_use input if the model called a tool"
    )
    tool_name: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    raw_response: str = Field(default="", description="Serialized raw response for debug")
    stop_reason: str = ""


class LLMClient(Protocol):
    """Abstract interface for LLM calls. Roles depend only on this."""

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        model: str | None = None,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Send messages to the LLM and return a structured response."""
        ...
