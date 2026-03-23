"""Scorecard model for Phase 4 deep dives."""

from __future__ import annotations

from pydantic import BaseModel, Field

from debate.schemas.common import ConfidenceLevel, RiskLevel
from debate.schemas.ideas import AutonomyScores


class Scorecard(BaseModel):
    """Official scorecard for a finalist idea — drives the final vote."""

    idea_id: str
    idea_name: str

    autonomy: AutonomyScores

    growth_ceiling_3yr: str = Field(description="$/month with key assumptions")
    startup_cost: float = Field(ge=0)
    startup_cost_items: list[dict[str, object]] = Field(default_factory=list)
    time_to_first_dollar: str

    defensibility: RiskLevel
    platform_risk: RiskLevel
    hidden_human_labor_risk: RiskLevel

    willingness_to_pay_evidence: list[str] = Field(
        default_factory=list,
        description="Named examples of what buyers already pay for",
    )

    overall_confidence: ConfidenceLevel

    deep_dive_summary: str = Field(default="", description="Compressed deep dive text")
    launch_plan_90day: str = Field(default="", description="Week-by-week 90-day plan")
    automation_architecture: str = Field(
        default="", description="What AI does vs human, by month"
    )
    acquisition_system: str = Field(
        default="", description="How customers acquired at each stage"
    )
    kill_criteria: str = Field(
        default="", description="Metrics and deadlines that signal stop"
    )
    why_now: str = Field(default="", description="Recent change enabling this idea")
    proof_of_wtp: str = Field(
        default="", description="Proof of willingness to pay narrative"
    )

    devils_advocate_objections: list[str] = Field(default_factory=list)
