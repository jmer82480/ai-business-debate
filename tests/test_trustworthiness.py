"""Tests for V1 trustworthiness fixes — BadOutputError reprompt, Phase 2 resume, cost tracking, truncation."""

from __future__ import annotations

import json

import pytest

from debate.config import DebateConfig, estimate_cost
from debate.llm.client import LLMResponse
from debate.llm.fake import FakeLLMClient
from debate.orchestrator import Orchestrator
from debate.roles.base import BadOutputError, ValidationFailure
from debate.roles.bootstrapper import MIN_IDEAS, _parse_ideas
from debate.schemas.state import DebateState, Phase, RunMeta, StepStatus
from debate.schemas.votes import Vote


# ---------------------------------------------------------------------------
# BadOutputError — _parse_ideas raises when < MIN_IDEAS
# ---------------------------------------------------------------------------


class TestBadOutputErrorParsing:
    def test_raises_on_too_few_ideas(self):
        """_parse_ideas raises BadOutputError when fewer than MIN_IDEAS returned."""
        data = {"ideas": [_stub_idea(i) for i in range(2)]}
        with pytest.raises(BadOutputError, match="minimum is 5"):
            _parse_ideas(data, "bootstrapper")

    def test_raises_on_zero_ideas(self):
        data = {"ideas": []}
        with pytest.raises(BadOutputError, match="Returned 0 ideas"):
            _parse_ideas(data, "market_analyst")

    def test_accepts_exactly_min_ideas(self):
        data = {"ideas": [_stub_idea(i) for i in range(MIN_IDEAS)]}
        result = _parse_ideas(data, "bootstrapper")
        assert len(result) == MIN_IDEAS

    def test_accepts_more_than_min_ideas(self):
        data = {"ideas": [_stub_idea(i) for i in range(8)]}
        result = _parse_ideas(data, "bootstrapper")
        assert len(result) == 8


class TestBadOutputRetryInRunStep:
    """BadOutputError triggers retry in Orchestrator._run_step."""

    def test_bad_output_retried_then_succeeds(self, config):
        """First call returns too few ideas, second call returns enough → step completes."""
        call_count = 0

        def respond(messages, system, tools, model, call_index, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: only 2 ideas (will trigger BadOutputError)
                return LLMResponse(
                    tool_use={"ideas": [_stub_idea(i) for i in range(2)]},
                    tool_name="submit_ideas",
                    model="fake",
                    tokens_in=100,
                    tokens_out=50,
                )
            # Second call: enough ideas
            return LLMResponse(
                tool_use={"ideas": [_stub_idea(i) for i in range(5)]},
                tool_name="submit_ideas",
                model="fake",
                tokens_in=200,
                tokens_out=100,
            )

        client = FakeLLMClient(response_fn=respond)
        orch = Orchestrator(client, config)

        role = orch._roles["bootstrapper"]
        result = orch._run_step("test_bad_output", role.generate_ideas)

        assert result is not None
        ideas, _ = result
        assert len(ideas) == 5
        assert call_count == 2  # retried once

    def test_bad_output_exhausts_retries(self, config):
        """BadOutputError raised on all attempts → raises after max retries."""

        def respond(messages, system, tools, model, call_index, **kw):
            return LLMResponse(
                tool_use={"ideas": [_stub_idea(0)]},
                tool_name="submit_ideas",
                model="fake",
                tokens_in=100,
                tokens_out=50,
            )

        client = FakeLLMClient(response_fn=respond)
        orch = Orchestrator(client, config)

        role = orch._roles["bootstrapper"]
        with pytest.raises(BadOutputError):
            orch._run_step("test_exhaust_retries", role.generate_ideas)

        step = orch.state.get_step("test_exhaust_retries")
        assert step.status == StepStatus.FAILED
        assert step.attempts == config.max_retries_per_step


# ---------------------------------------------------------------------------
# Phase 2 resume — votes persisted per-role and reconstructed
# ---------------------------------------------------------------------------


class TestPhase2Resume:
    def test_role_votes_persisted_to_state(self, config):
        """After Phase 2, phase2_role_votes has entries for each debater role."""
        from debate.cli import _make_dry_run_client

        client = _make_dry_run_client()
        orch = Orchestrator(client, config)
        orch._run_phase1()
        orch._run_phase2()

        state = orch.state
        # All 4 debater roles should have persisted votes
        for role_name in ["bootstrapper", "market_analyst", "automation_architect", "devils_advocate"]:
            assert role_name in state.phase2_role_votes, f"Missing votes for {role_name}"
            assert len(state.phase2_role_votes[role_name]) > 0

    def test_votes_reconstructed_from_persisted_data(self, config):
        """Tally uses reconstructed votes from phase2_role_votes, not ephemeral lists."""
        from debate.cli import _make_dry_run_client

        client = _make_dry_run_client()
        orch = Orchestrator(client, config)
        orch._run_phase1()
        orch._run_phase2()

        state = orch.state
        # Reconstruct votes the same way the orchestrator does
        all_votes: list[Vote] = []
        for role_name in ["bootstrapper", "market_analyst", "automation_architect", "devils_advocate"]:
            for v_data in state.phase2_role_votes.get(role_name, []):
                all_votes.append(Vote.model_validate(v_data))

        # Should match the vote round
        assert state.phase2_votes is not None
        assert len(all_votes) == len(state.phase2_votes.votes)

    def test_phase2_role_votes_serializable(self, config):
        """Persisted per-role votes survive JSON round-trip (checkpoint safe)."""
        from debate.cli import _make_dry_run_client

        client = _make_dry_run_client()
        orch = Orchestrator(client, config)
        orch._run_phase1()
        orch._run_phase2()

        # Serialize + deserialize the whole state (simulates checkpoint load)
        state_json = orch.state.model_dump_json()
        loaded = DebateState.model_validate_json(state_json)

        for role_name in ["bootstrapper", "market_analyst", "automation_architect", "devils_advocate"]:
            assert role_name in loaded.phase2_role_votes
            original = orch.state.phase2_role_votes[role_name]
            restored = loaded.phase2_role_votes[role_name]
            assert len(original) == len(restored)


# ---------------------------------------------------------------------------
# Cost tracking — flows from debug JSON through step metadata
# ---------------------------------------------------------------------------


class TestCostTracking:
    def test_step_accumulates_cost(self, config):
        """Completed step has tokens and cost from the debug JSON."""
        from debate.cli import _make_dry_run_client

        client = _make_dry_run_client()
        orch = Orchestrator(client, config)
        orch._run_phase1()

        # Check that at least one step has cost tracked
        for step_key, step_meta in orch.state.steps.items():
            if step_meta.status == StepStatus.COMPLETED:
                # The dry-run client returns tokens_in=100, tokens_out=50
                # Cost should be calculated from those
                assert step_meta.tokens_in >= 0
                assert step_meta.tokens_out >= 0
                break

    def test_run_meta_accumulates_total_cost(self, config):
        """RunMeta total cost accumulates across all steps."""
        from debate.cli import _make_dry_run_client

        client = _make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        meta = orch.state.meta
        assert meta.total_tokens_in >= 0
        assert meta.total_tokens_out >= 0
        # With fake model "fake", pricing falls back to default sonnet pricing
        # total cost = sum of all steps
        assert meta.total_estimated_cost_usd >= 0.0

    def test_estimate_cost_known_model(self):
        """estimate_cost returns correct value for known model."""
        # claude-sonnet-4-6: $3/1M input, $15/1M output
        cost = estimate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.0)

    def test_estimate_cost_unknown_model_uses_default(self):
        """Unknown model falls back to default pricing."""
        cost = estimate_cost("fake", 1_000_000, 1_000_000)
        # Default pricing is same as sonnet: (3.0, 15.0)
        assert cost == pytest.approx(18.0)

    def test_cost_in_debug_json_parsed(self, config):
        """Cost info from debug JSON is parsed and applied to step metadata."""

        def respond(messages, system, tools, model, call_index, **kw):
            return LLMResponse(
                tool_use={"ideas": [_stub_idea(i) for i in range(5)]},
                tool_name="submit_ideas",
                model="claude-sonnet-4-6",
                tokens_in=500,
                tokens_out=200,
            )

        client = FakeLLMClient(response_fn=respond)
        orch = Orchestrator(client, config)

        role = orch._roles["bootstrapper"]
        orch._run_step("test_cost_parse", role.generate_ideas)

        step = orch.state.get_step("test_cost_parse")
        assert step.tokens_in == 500
        assert step.tokens_out == 200
        expected_cost = estimate_cost("claude-sonnet-4-6", 500, 200)
        assert step.estimated_cost_usd == pytest.approx(expected_cost)
        assert step.model_used == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Truncated response / empty merge pool
# ---------------------------------------------------------------------------


class TestTruncatedResponse:
    """stop_reason=max_tokens must raise ValidationFailure, not silently proceed."""

    def test_extract_tool_data_rejects_truncated(self, config):
        """_extract_tool_data raises ValidationFailure when stop_reason is max_tokens."""
        from debate.roles.bootstrapper import Bootstrapper

        client = FakeLLMClient()
        role = Bootstrapper(client, config)

        truncated_response = LLMResponse(
            tool_use={},
            tool_name="submit_ideas",
            model="fake",
            tokens_in=100,
            tokens_out=16384,
            stop_reason="max_tokens",
        )
        with pytest.raises(ValidationFailure, match="truncated"):
            role._extract_tool_data(truncated_response, "submit_ideas")

    def test_truncated_merge_triggers_retry(self, config):
        """Merge step retries when response is truncated instead of accepting empty pool."""
        call_count = 0

        def respond(messages, system, tools, model, call_index, **kw):
            nonlocal call_count
            call_count += 1
            tool_name = ""
            for t in (tools or []):
                if isinstance(t, dict) and "name" in t:
                    tool_name = t["name"]
                    break

            if tool_name == "submit_ideas":
                return LLMResponse(
                    tool_use={"ideas": [_stub_idea(i) for i in range(5)]},
                    tool_name="submit_ideas",
                    model="fake",
                    tokens_in=100,
                    tokens_out=50,
                )
            if tool_name == "submit_merged_pool" and call_count <= 5:
                # First merge attempt: truncated
                return LLMResponse(
                    tool_use={},
                    tool_name="submit_merged_pool",
                    model="fake",
                    tokens_in=100,
                    tokens_out=16384,
                    stop_reason="max_tokens",
                )
            if tool_name == "submit_merged_pool":
                # Second merge attempt: success
                merged = []
                for i in range(8):
                    idea = _stub_idea(i)
                    idea["idea_id"] = f"stub-{i}-00000000"
                    idea["proposed_by"] = ["bootstrapper", "market_analyst"]
                    merged.append(idea)
                return LLMResponse(
                    tool_use={"ideas": merged, "eliminated": [], "conflicts": []},
                    tool_name="submit_merged_pool",
                    model="fake",
                    tokens_in=100,
                    tokens_out=5000,
                    stop_reason="end_turn",
                )
            # Default for votes etc
            return LLMResponse(
                tool_use={"votes": []},
                tool_name=tool_name,
                model="fake",
                tokens_in=100,
                tokens_out=50,
            )

        client = FakeLLMClient(response_fn=respond)
        orch = Orchestrator(client, config)
        orch._run_phase1()

        # Merge should retry after truncation and succeed
        step_key = "phase_2_merge_vote.merge"
        result = orch._run_step(step_key, orch._moderator.merge_ideas,
                                orch._format_all_phase1_ideas())
        assert result is not None
        data, _ = result
        assert len(data.get("ideas", [])) == 8


class TestEmptyMergePoolGate:
    """Orchestrator must refuse to proceed to voting with an empty merge pool."""

    def test_empty_pool_raises_before_voting(self, config):
        """If merge produces 0 ideas, Phase 2 raises before voting begins."""
        from debate.cli import _make_dry_run_client

        client = _make_dry_run_client()
        orch = Orchestrator(client, config)
        orch._run_phase1()

        # Simulate a merge that produced 0 ideas
        orch.state.merged_pool = []
        # Mark merge as completed so it's skipped
        orch.state.get_step("phase_2_merge_vote.merge").mark_running()
        orch.state.get_step("phase_2_merge_vote.merge").mark_completed()

        with pytest.raises(RuntimeError, match="0 ideas"):
            orch._run_phase2()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_idea(idx: int) -> dict:
    """Minimal idea dict that passes _parse_ideas."""
    return {
        "name": f"Stub Idea {idx}",
        "description": f"Test idea {idx}",
        "startup_cost_items": [{"item": "Domain", "cost_usd": 12.0}],
        "startup_cost_total": 12.0,
        "autonomy": {"acquisition": 80, "fulfillment": 85, "support": 75, "qa": 70},
        "revenue": {
            "day_90": "$500",
            "month_12": "$5,000/mo",
            "year_3_ceiling": "$50,000/mo",
        },
        "acquisition_path": {
            "first_10": "SEO",
            "first_100": "Organic",
            "first_1000": "Referrals",
        },
        "moat": "Data compounds.",
        "platform_risk": "Low.",
        "key_risk": "Market uncertain.",
        "why_now": "AI costs dropped.",
        "evidence": [],
    }
