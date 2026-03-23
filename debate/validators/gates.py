"""Gate criteria validation — hard pass/fail from CLAUDE.md."""

from __future__ import annotations

from dataclasses import dataclass

from debate.schemas.ideas import Idea


@dataclass
class GateFailure:
    """A specific gate that an idea failed."""

    idea_id: str
    gate: str
    reason: str


MANUAL_OUTBOUND_KEYWORDS = [
    "cold call",
    "cold email",
    "manual outbound",
    "door to door",
    "hand-sell",
    "personally reach out",
]


def validate_gate_criteria(idea: Idea) -> list[GateFailure]:
    """Check an idea against all three gate criteria. Returns list of failures."""
    failures: list[GateFailure] = []

    # Gate 1: Startup cost under $500
    if idea.startup_cost_total > 500:
        failures.append(
            GateFailure(
                idea_id=idea.idea_id,
                gate="startup_cost",
                reason=f"Startup cost ${idea.startup_cost_total:.2f} exceeds $500 limit",
            )
        )

    # Gate 2: AI autonomy above 70%
    composite = idea.autonomy.composite
    if composite < 70:
        failures.append(
            GateFailure(
                idea_id=idea.idea_id,
                gate="ai_autonomy",
                reason=f"Autonomy composite {composite:.1f} is below 70% threshold",
            )
        )

    # Gate 3: No manual outbound sales dependency
    acq_text = (
        f"{idea.acquisition_path.first_10} "
        f"{idea.acquisition_path.first_100} "
        f"{idea.acquisition_path.first_1000}"
    ).lower()
    for keyword in MANUAL_OUTBOUND_KEYWORDS:
        if keyword in acq_text:
            failures.append(
                GateFailure(
                    idea_id=idea.idea_id,
                    gate="customer_acquisition",
                    reason=f"Acquisition path contains manual outbound: '{keyword}'",
                )
            )
            break

    return failures


def passes_gates(idea: Idea) -> bool:
    """Convenience: returns True if the idea passes all gates."""
    return len(validate_gate_criteria(idea)) == 0
