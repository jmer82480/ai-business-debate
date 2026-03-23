"""Shared test fixtures."""

from __future__ import annotations

import pytest

from debate.config import DebateConfig
from debate.llm.client import LLMResponse
from debate.llm.fake import FakeLLMClient
from debate.schemas.common import ConfidenceLevel, RiskLevel
from debate.schemas.ideas import (
    AcquisitionPath,
    AutonomyScores,
    Idea,
    RevenueHorizons,
)
from debate.schemas.scorecard import Scorecard
from debate.schemas.state import DebateState, Phase, RunMeta
from debate.schemas.verdict import AgentPosition, FinalVerdict, RankedFinalist
from debate.schemas.votes import Vote, VoteRound


@pytest.fixture
def config(tmp_path):
    return DebateConfig(
        output_dir=str(tmp_path / "output"),
        checkpoint_dir=str(tmp_path / "checkpoints"),
    )


@pytest.fixture
def fake_client():
    return FakeLLMClient()


def make_idea(
    name: str = "Test Idea",
    cost: float = 100.0,
    acq: int = 80,
    ful: int = 85,
    sup: int = 75,
    qa: int = 70,
    idea_id: str = "",
    proposed_by: list[str] | None = None,
) -> Idea:
    """Create a test idea with sensible defaults."""
    return Idea(
        idea_id=idea_id,
        name=name,
        description=f"A test idea: {name}",
        proposed_by=proposed_by or ["bootstrapper"],
        startup_cost_items=[{"item": "Domain", "cost_usd": cost}],
        startup_cost_total=cost,
        autonomy=AutonomyScores(acquisition=acq, fulfillment=ful, support=sup, qa=qa),
        revenue=RevenueHorizons(
            day_90="$500", month_12="$5,000/mo", year_3_ceiling="$50,000/mo"
        ),
        acquisition_path=AcquisitionPath(
            first_10="SEO + content",
            first_100="Organic growth",
            first_1000="Referral program",
        ),
        moat="Proprietary data compounds over time",
        platform_risk="Depends on single API provider",
        key_risk="Market may not exist at this price",
        why_now="AI tool costs dropped significantly in 2025",
        evidence=[
            {
                "claim": "AI costs dropped",
                "source": "UNSOURCED ESTIMATE",
                "date": "2025",
                "key_assumption": "Trend continues",
                "confidence": "medium",
            }
        ],
    )


def make_state_at_phase2(num_ideas: int = 8) -> DebateState:
    """Create a state with Phase 1 complete and merged pool ready."""
    state = DebateState(meta=RunMeta(run_id="test-run"))
    roles = ["bootstrapper", "market_analyst", "automation_architect", "devils_advocate"]

    # Phase 1 ideas
    for role in roles:
        state.phase1_ideas[role] = [make_idea(f"Idea {i} by {role}") for i in range(5)]

    # Merged pool
    state.merged_pool = [make_idea(f"Merged Idea {i}", idea_id=f"idea-{i}") for i in range(num_ideas)]

    return state


def make_state_at_phase5() -> DebateState:
    """Create a state ready for Phase 5 convergence."""
    state = make_state_at_phase2(8)
    state.current_phase = Phase.PHASE_4_DEEP_DIVE
    state.survivors = [f"idea-{i}" for i in range(5)]
    state.finalists = ["idea-0", "idea-1", "idea-2"]

    for idea_id in state.finalists:
        idea = state.get_idea_by_id(idea_id)
        state.scorecards[idea_id] = Scorecard(
            idea_id=idea_id,
            idea_name=idea.name if idea else f"Idea {idea_id}",
            autonomy=AutonomyScores(acquisition=80, fulfillment=85, support=75, qa=70),
            growth_ceiling_3yr="$50,000/mo",
            startup_cost=100.0,
            time_to_first_dollar="30 days",
            defensibility=RiskLevel.MEDIUM,
            platform_risk=RiskLevel.MEDIUM,
            hidden_human_labor_risk=RiskLevel.LOW,
            willingness_to_pay_evidence=["Competitors charge $99/mo"],
            overall_confidence=ConfidenceLevel.MEDIUM,
        )

    return state
