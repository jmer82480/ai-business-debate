"""Global configuration for the debate engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# Model pricing per 1M tokens (input, output) in USD
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-6": (15.00, 75.00),
    "claude-haiku-4-5-20251001": (0.80, 4.00),
}


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate USD cost for an API call."""
    price_in, price_out = MODEL_PRICING.get(model, (3.00, 15.00))
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


@dataclass
class DebateConfig:
    """All tunables for a debate run."""

    # Models
    model_default: str = "claude-sonnet-4-6"
    model_deep_dive: str = "claude-sonnet-4-6"

    # Limits
    max_phase3_rounds: int = 10
    max_retries_per_step: int = 3
    retry_delay_seconds: float = 2.0
    api_timeout_seconds: float = 120.0

    # Budget
    max_total_cost_usd: float | None = None
    prompt_context_budget_tokens: int = 12000

    # Web search (off by default — opt in with --web-search for evidence-grade runs)
    web_search_enabled: bool = False

    # Debug artifacts
    debug_max_files: int = 50
    debug_max_file_bytes: int = 100_000

    # Paths
    output_dir: str = "output"
    checkpoint_dir: str = "checkpoints"

    # Roles
    roles: list[str] = field(
        default_factory=lambda: [
            "bootstrapper",
            "market_analyst",
            "automation_architect",
            "devils_advocate",
        ]
    )

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir)

    @property
    def checkpoint_path(self) -> Path:
        return Path(self.checkpoint_dir)

    def to_dict(self) -> dict[str, object]:
        """Serialize config to a dict for checkpoint persistence."""
        return {
            "model_default": self.model_default,
            "model_deep_dive": self.model_deep_dive,
            "max_phase3_rounds": self.max_phase3_rounds,
            "max_retries_per_step": self.max_retries_per_step,
            "retry_delay_seconds": self.retry_delay_seconds,
            "api_timeout_seconds": self.api_timeout_seconds,
            "web_search_enabled": self.web_search_enabled,
            "prompt_context_budget_tokens": self.prompt_context_budget_tokens,
            "output_dir": self.output_dir,
            "checkpoint_dir": self.checkpoint_dir,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "DebateConfig":
        """Restore config from a checkpoint dict."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
