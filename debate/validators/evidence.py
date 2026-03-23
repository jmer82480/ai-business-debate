"""Evidence standard validation — checks that major claims are sourced."""

from __future__ import annotations

from dataclasses import dataclass

from debate.schemas.ideas import Idea


@dataclass
class EvidenceWarning:
    """A warning about missing or weak evidence."""

    idea_id: str
    field: str
    message: str


def validate_evidence(idea: Idea) -> list[EvidenceWarning]:
    """Check that the idea has evidence entries and key fields aren't empty."""
    warnings: list[EvidenceWarning] = []

    if not idea.evidence:
        warnings.append(
            EvidenceWarning(
                idea_id=idea.idea_id,
                field="evidence",
                message="No evidence entries provided. Major claims require sources.",
            )
        )

    # Check key narrative fields aren't suspiciously short
    min_length_fields = {
        "moat": idea.moat,
        "platform_risk": idea.platform_risk,
        "key_risk": idea.key_risk,
        "why_now": idea.why_now,
    }
    for field_name, value in min_length_fields.items():
        if len(value.strip()) < 10:
            warnings.append(
                EvidenceWarning(
                    idea_id=idea.idea_id,
                    field=field_name,
                    message=f"Field '{field_name}' is too short ({len(value)} chars). Provide substantive content.",
                )
            )

    return warnings
