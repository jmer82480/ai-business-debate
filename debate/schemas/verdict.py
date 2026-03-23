"""Final verdict models for Phase 5."""

from __future__ import annotations

from pydantic import BaseModel, Field

from debate.schemas.common import ConfidenceLevel


class AgentPosition(BaseModel):
    """An agent's final position in the debate."""

    role: str
    voted_for_idea_id: str
    ranking: list[str] = Field(
        default_factory=list, description="Ordered list of idea_ids best to worst"
    )
    justification: str
    remaining_concerns: str = ""


class RankedFinalist(BaseModel):
    """A finalist in the final ranked table."""

    idea_id: str
    idea_name: str
    autonomy_acquisition: int
    autonomy_fulfillment: int
    autonomy_support: int
    autonomy_qa: int
    autonomy_composite: float
    growth_ceiling: str
    startup_cost: float
    time_to_first_dollar: str
    defensibility: str
    platform_risk: str
    hidden_human_labor_risk: str
    willingness_to_pay: str
    overall_confidence: str
    overall_finish: int = Field(description="Final ranking position, 1 = winner")


class FinalVerdict(BaseModel):
    """The complete verdict document."""

    ranked_table: list[RankedFinalist] = Field(default_factory=list)
    winner_idea_id: str
    winner_narrative: str = Field(description="Why the winner won")
    runner_up_idea_id: str
    runner_up_narrative: str = Field(description="Why the runner-up lost")
    agent_positions: list[AgentPosition] = Field(default_factory=list)
    devils_advocate_remaining_concerns: str
    group_confidence: ConfidenceLevel
