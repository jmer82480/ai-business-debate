"""LLM client abstraction — roles never import the provider SDK directly."""

from debate.llm.client import LLMClient, LLMResponse

__all__ = ["LLMClient", "LLMResponse"]
