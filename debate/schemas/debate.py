"""Debate round models for Phase 3."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FailureScenario(BaseModel):
    """A concrete failure scenario from Devil's Advocate."""

    scenario: str
    evidence: str
    likelihood: str = ""


class DebateArgument(BaseModel):
    """A single agent's argument in a debate round."""

    idea_id: str
    role: str
    position: str = Field(description="bull, bear, or response")
    argument: str
    vote: bool | None = Field(default=None, description="YES/NO if voting in this round")
    failure_scenarios: list[FailureScenario] = Field(default_factory=list)


class DebateRound(BaseModel):
    """A complete debate round covering one or more ideas."""

    round_number: int
    arguments: list[DebateArgument] = Field(default_factory=list)
    moderator_summary: str = ""
    eliminated_idea_ids: list[str] = Field(default_factory=list)
    surviving_idea_ids: list[str] = Field(default_factory=list)
