"""Vote models for Phase 2 and Phase 3."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Vote(BaseModel):
    """A single agent's vote on a single idea."""

    idea_id: str
    role: str
    vote: bool = Field(description="True = YES, False = NO")
    justification: str


class VoteRound(BaseModel):
    """All votes from a single voting round."""

    phase: int
    round_number: int = 1
    votes: list[Vote] = Field(default_factory=list)

    def tally(self, idea_id: str) -> tuple[int, int]:
        """Return (yes_count, no_count) for an idea."""
        idea_votes = [v for v in self.votes if v.idea_id == idea_id]
        yes = sum(1 for v in idea_votes if v.vote)
        no = sum(1 for v in idea_votes if not v.vote)
        return yes, no
