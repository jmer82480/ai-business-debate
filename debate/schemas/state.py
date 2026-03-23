"""Root debate state — the single source of truth."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from debate.schemas.debate import DebateRound
from debate.schemas.ideas import Idea
from debate.schemas.scorecard import Scorecard
from debate.schemas.verdict import FinalVerdict
from debate.schemas.votes import VoteRound


SCHEMA_VERSION = "0.1.0"


class Phase(str, Enum):
    PHASE_1_IDEATION = "phase_1_ideation"
    PHASE_2_MERGE_VOTE = "phase_2_merge_vote"
    PHASE_3_DEBATE = "phase_3_debate"
    PHASE_4_DEEP_DIVE = "phase_4_deep_dive"
    PHASE_5_CONVERGENCE = "phase_5_convergence"
    COMPLETED = "completed"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepMeta(BaseModel):
    """Rich metadata for a single orchestrator step."""

    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    last_error: str | None = None
    model_used: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    estimated_cost_usd: float = 0.0
    duration_ms: int = 0

    def mark_running(self) -> None:
        self.status = StepStatus.RUNNING
        self.attempts += 1
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at = None
        self.last_error = None

    def mark_completed(
        self,
        model: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        self.status = StepStatus.COMPLETED
        self.finished_at = datetime.now(timezone.utc).isoformat()
        if model:
            self.model_used = model
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.estimated_cost_usd += cost_usd
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.finished_at)
            self.duration_ms = int((end - start).total_seconds() * 1000)

    def mark_failed(self, error: str) -> None:
        self.status = StepStatus.FAILED
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.last_error = error
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.finished_at)
            self.duration_ms = int((end - start).total_seconds() * 1000)


class RunMeta(BaseModel):
    """Metadata about the current run."""

    run_id: str = ""
    schema_version: str = SCHEMA_VERSION
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_estimated_cost_usd: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0


class DebateState(BaseModel):
    """The complete state of a debate run. This is the source of truth."""

    meta: RunMeta = Field(default_factory=RunMeta)
    current_phase: Phase = Phase.PHASE_1_IDEATION
    steps: dict[str, StepMeta] = Field(default_factory=dict)

    # Phase 1: ideas proposed by each role
    phase1_ideas: dict[str, list[Idea]] = Field(
        default_factory=dict, description="role_name -> list of ideas"
    )

    # Phase 2: merged pool and vote results
    merged_pool: list[Idea] = Field(default_factory=list)
    phase2_votes: VoteRound | None = None
    survivors: list[str] = Field(
        default_factory=list, description="idea_ids that survived Phase 2"
    )

    # Phase 3: debate rounds
    debate_rounds: list[DebateRound] = Field(default_factory=list)
    finalists: list[str] = Field(
        default_factory=list, description="idea_ids that reached Phase 4"
    )

    # Phase 4: scorecards
    scorecards: dict[str, Scorecard] = Field(
        default_factory=dict, description="idea_id -> Scorecard"
    )

    # Phase 5: verdict
    final_votes: list[dict[str, object]] = Field(default_factory=list)
    verdict: FinalVerdict | None = None

    def get_step(self, step_key: str) -> StepMeta:
        """Get or create step metadata."""
        if step_key not in self.steps:
            self.steps[step_key] = StepMeta()
        return self.steps[step_key]

    def is_step_completed(self, step_key: str) -> bool:
        return self.steps.get(step_key, StepMeta()).status == StepStatus.COMPLETED

    def accumulate_cost(self, tokens_in: int, tokens_out: int, cost_usd: float) -> None:
        self.meta.total_tokens_in += tokens_in
        self.meta.total_tokens_out += tokens_out
        self.meta.total_estimated_cost_usd += cost_usd
        self.meta.updated_at = datetime.now(timezone.utc).isoformat()

    def get_idea_by_id(self, idea_id: str) -> Idea | None:
        """Look up an idea from the merged pool by stable ID."""
        for idea in self.merged_pool:
            if idea.idea_id == idea_id:
                return idea
        return None
