"""Idea model — the core unit of the debate."""

from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, Field, model_validator


class AutonomyScores(BaseModel):
    """Four-dimensional autonomy breakdown."""

    acquisition: int = Field(ge=0, le=100, description="How customers are found")
    fulfillment: int = Field(ge=0, le=100, description="How product/service is delivered")
    support: int = Field(ge=0, le=100, description="How problems are handled")
    qa: int = Field(ge=0, le=100, description="How quality is maintained")

    @property
    def composite(self) -> float:
        """Weighted composite: Acquisition 35%, Fulfillment 30%, Support 20%, QA 15%."""
        return (
            self.acquisition * 0.35
            + self.fulfillment * 0.30
            + self.support * 0.20
            + self.qa * 0.15
        )


class RevenueHorizons(BaseModel):
    """Revenue projections at three time horizons."""

    day_90: str = Field(description="90-day revenue estimate with assumptions")
    month_12: str = Field(description="12-month revenue estimate with assumptions")
    year_3_ceiling: str = Field(description="3-year ceiling estimate with assumptions")


class AcquisitionPath(BaseModel):
    """How customers find the business at each scale."""

    first_10: str
    first_100: str
    first_1000: str


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


class Idea(BaseModel):
    """A business idea with all required fields from the protocol."""

    idea_id: str = Field(default="", description="Stable identifier: slug + short UUID")
    name: str
    description: str
    proposed_by: list[str] = Field(
        default_factory=list, description="Role names that proposed this idea"
    )

    startup_cost_items: list[dict[str, object]] = Field(
        default_factory=list, description="Line-item cost breakdown"
    )
    startup_cost_total: float = Field(ge=0, description="Total startup cost in USD")

    autonomy: AutonomyScores
    revenue: RevenueHorizons
    acquisition_path: AcquisitionPath

    moat: str = Field(description="Defensibility / what stops copying")
    platform_risk: str = Field(description="Single points of failure")
    key_risk: str = Field(description="Most likely way this dies")
    why_now: str = Field(description="What recent change enables this")

    evidence: list[dict[str, str]] = Field(
        default_factory=list, description="Supporting evidence entries"
    )

    @model_validator(mode="after")
    def _assign_stable_id(self) -> "Idea":
        if not self.idea_id:
            slug = _slugify(self.name)
            short_uuid = uuid.uuid4().hex[:8]
            self.idea_id = f"{slug}-{short_uuid}"
        return self
