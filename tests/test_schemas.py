"""Tests for pydantic schema models — construction, validation, serialization."""

import json

import pytest

from debate.schemas.common import ConfidenceLevel, Evidence, RiskLevel
from debate.schemas.ideas import AutonomyScores, Idea
from debate.schemas.state import DebateState, Phase, RunMeta, StepMeta, StepStatus
from debate.schemas.votes import Vote, VoteRound
from tests.conftest import make_idea


class TestAutonomyScores:
    def test_composite_calculation(self):
        scores = AutonomyScores(acquisition=80, fulfillment=90, support=70, qa=60)
        # 80*0.35 + 90*0.30 + 70*0.20 + 60*0.15 = 28 + 27 + 14 + 9 = 78
        assert scores.composite == 78.0

    def test_composite_all_100(self):
        scores = AutonomyScores(acquisition=100, fulfillment=100, support=100, qa=100)
        assert scores.composite == 100.0

    def test_composite_all_0(self):
        scores = AutonomyScores(acquisition=0, fulfillment=0, support=0, qa=0)
        assert scores.composite == 0.0

    def test_validation_range(self):
        with pytest.raises(Exception):
            AutonomyScores(acquisition=101, fulfillment=0, support=0, qa=0)
        with pytest.raises(Exception):
            AutonomyScores(acquisition=-1, fulfillment=0, support=0, qa=0)


class TestIdea:
    def test_stable_id_generated(self):
        idea = make_idea("My Test Idea")
        assert idea.idea_id.startswith("my-test-idea-")
        assert len(idea.idea_id) > len("my-test-idea-")

    def test_stable_id_preserved_if_set(self):
        idea = make_idea("Test", idea_id="custom-id-123")
        assert idea.idea_id == "custom-id-123"

    def test_serialization_roundtrip(self):
        idea = make_idea("Roundtrip Test")
        data = idea.model_dump(mode="json")
        restored = Idea.model_validate(data)
        assert restored.name == idea.name
        assert restored.idea_id == idea.idea_id
        assert restored.autonomy.composite == idea.autonomy.composite


class TestVoteRound:
    def test_tally(self):
        vr = VoteRound(
            phase=2,
            votes=[
                Vote(idea_id="a", role="r1", vote=True, justification="yes"),
                Vote(idea_id="a", role="r2", vote=True, justification="yes"),
                Vote(idea_id="a", role="r3", vote=False, justification="no"),
                Vote(idea_id="b", role="r1", vote=False, justification="no"),
            ],
        )
        yes_a, no_a = vr.tally("a")
        assert yes_a == 2
        assert no_a == 1

        yes_b, no_b = vr.tally("b")
        assert yes_b == 0
        assert no_b == 1


class TestStepMeta:
    def test_lifecycle(self):
        step = StepMeta()
        assert step.status == StepStatus.PENDING
        assert step.attempts == 0

        step.mark_running()
        assert step.status == StepStatus.RUNNING
        assert step.attempts == 1
        assert step.started_at is not None

        step.mark_completed(model="test", tokens_in=100, tokens_out=50, cost_usd=0.01)
        assert step.status == StepStatus.COMPLETED
        assert step.finished_at is not None
        assert step.tokens_in == 100
        assert step.duration_ms >= 0

    def test_failure(self):
        step = StepMeta()
        step.mark_running()
        step.mark_failed("something broke")
        assert step.status == StepStatus.FAILED
        assert step.last_error == "something broke"


class TestDebateState:
    def test_json_roundtrip(self):
        state = DebateState(meta=RunMeta(run_id="test-123"))
        state.phase1_ideas["bootstrapper"] = [make_idea(f"Idea {i}") for i in range(5)]

        data = state.model_dump(mode="json")
        json_str = json.dumps(data, default=str)
        restored = DebateState.model_validate(json.loads(json_str))

        assert restored.meta.run_id == "test-123"
        assert len(restored.phase1_ideas["bootstrapper"]) == 5

    def test_get_step_creates_if_missing(self):
        state = DebateState()
        step = state.get_step("new_step")
        assert step.status == StepStatus.PENDING
        assert "new_step" in state.steps

    def test_is_step_completed(self):
        state = DebateState()
        assert not state.is_step_completed("x")
        state.get_step("x").mark_running()
        state.get_step("x").mark_completed()
        assert state.is_step_completed("x")

    def test_accumulate_cost(self):
        state = DebateState()
        state.accumulate_cost(1000, 500, 0.05)
        state.accumulate_cost(2000, 1000, 0.10)
        assert state.meta.total_tokens_in == 3000
        assert state.meta.total_tokens_out == 1500
        assert abs(state.meta.total_estimated_cost_usd - 0.15) < 0.001
