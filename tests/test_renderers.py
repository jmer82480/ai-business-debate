"""Tests for markdown rendering — state to output files."""

from pathlib import Path

import pytest

from debate.config import DebateConfig
from debate.renderers.markdown import MarkdownRenderer
from debate.schemas.common import ConfidenceLevel, RiskLevel
from debate.schemas.ideas import AutonomyScores
from debate.schemas.scorecard import Scorecard
from debate.schemas.state import DebateState, Phase, RunMeta
from debate.schemas.verdict import AgentPosition, FinalVerdict, RankedFinalist
from tests.conftest import make_idea, make_state_at_phase2, make_state_at_phase5


class TestPhase1Rendering:
    def test_renders_phase1_files(self, config):
        renderer = MarkdownRenderer(config)
        state = DebateState(meta=RunMeta(run_id="render-test"))
        state.phase1_ideas["bootstrapper"] = [make_idea(f"Idea {i}") for i in range(5)]

        written = renderer.render_all(state)
        assert any("bootstrapper-ideas.md" in p for p in written)

        content = Path(written[0]).read_text()
        assert "Bootstrapper" in content
        assert "Idea 0" in content


class TestPhase2Rendering:
    def test_renders_merged_pool(self, config):
        renderer = MarkdownRenderer(config)
        state = make_state_at_phase2()
        state.survivors = [state.merged_pool[0].idea_id]

        written = renderer.render_all(state)
        md_files = [p for p in written if "merged-pool.md" in p]
        assert len(md_files) == 1

        content = Path(md_files[0]).read_text()
        assert "SURVIVOR" in content


class TestScorecardRendering:
    def test_renders_scorecard_table(self, config):
        renderer = MarkdownRenderer(config)
        state = make_state_at_phase5()

        written = renderer.render_all(state)
        scorecard_files = [p for p in written if "scorecard-" in p]
        assert len(scorecard_files) == 3

        content = Path(scorecard_files[0]).read_text()
        assert "Autonomy Composite" in content
        assert "Willingness to Pay" in content


class TestVerdictRendering:
    def test_renders_verdict_and_plan(self, config):
        renderer = MarkdownRenderer(config)
        state = make_state_at_phase5()
        state.current_phase = Phase.PHASE_5_CONVERGENCE

        state.verdict = FinalVerdict(
            ranked_table=[
                RankedFinalist(
                    idea_id="idea-0",
                    idea_name="Winner Idea",
                    autonomy_acquisition=80,
                    autonomy_fulfillment=85,
                    autonomy_support=75,
                    autonomy_qa=70,
                    autonomy_composite=79.5,
                    growth_ceiling="$50K/mo",
                    startup_cost=100.0,
                    time_to_first_dollar="30 days",
                    defensibility="medium",
                    platform_risk="medium",
                    hidden_human_labor_risk="low",
                    willingness_to_pay="Competitors charge $99/mo",
                    overall_confidence="medium",
                    overall_finish=1,
                ),
            ],
            winner_idea_id="idea-0",
            winner_narrative="Best overall performance across all dimensions.",
            runner_up_idea_id="idea-1",
            runner_up_narrative="Close but lower defensibility.",
            agent_positions=[
                AgentPosition(
                    role="bootstrapper",
                    voted_for_idea_id="idea-0",
                    justification="Cheapest and most autonomous.",
                )
            ],
            devils_advocate_remaining_concerns="Market size uncertain.",
            group_confidence=ConfidenceLevel.MEDIUM,
        )

        written = renderer.render_all(state)
        verdict_files = [p for p in written if "verdict.md" in p]
        plan_files = [p for p in written if "final-plan.md" in p]

        assert len(verdict_files) == 1
        assert len(plan_files) == 1

        verdict_content = Path(verdict_files[0]).read_text()
        assert "Final Ranked Table" in verdict_content
        assert "Winner" in verdict_content
        assert "Runner-Up" in verdict_content
        assert "Devil's Advocate" in verdict_content
