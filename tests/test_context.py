"""Tests for context compression — budget enforcement, no key data loss."""

from debate.context import (
    compress_idea,
    compress_ideas_list,
    compress_merged_pool,
    compress_survivors,
    compress_all_scorecards,
    _estimate_tokens,
    _truncate_to_budget,
)
from tests.conftest import make_idea, make_state_at_phase2, make_state_at_phase5


class TestTokenEstimation:
    def test_basic_estimation(self):
        assert _estimate_tokens("1234") == 1
        assert _estimate_tokens("12345678") == 2

    def test_empty_string(self):
        assert _estimate_tokens("") == 0


class TestTruncation:
    def test_within_budget(self):
        text = "Short text"
        result = _truncate_to_budget(text, budget_tokens=1000)
        assert result == text
        assert "[TRUNCATED]" not in result

    def test_over_budget(self):
        text = "x" * 10000
        result = _truncate_to_budget(text, budget_tokens=100)
        assert "TRUNCATED" in result
        assert len(result) < len(text)


class TestCompressIdea:
    def test_contains_key_fields(self):
        idea = make_idea("My Idea", cost=250)
        compressed = compress_idea(idea)
        assert "My Idea" in compressed
        assert "250" in compressed
        assert idea.idea_id in compressed


class TestCompressMergedPool:
    def test_within_budget(self):
        state = make_state_at_phase2(5)
        compressed = compress_merged_pool(state, budget_tokens=5000)
        tokens = _estimate_tokens(compressed)
        assert tokens <= 5000

    def test_all_ideas_present(self):
        state = make_state_at_phase2(5)
        compressed = compress_merged_pool(state)
        for idea in state.merged_pool:
            assert idea.idea_id in compressed


class TestCompressSurvivors:
    def test_only_survivors_included(self):
        state = make_state_at_phase2(8)
        state.survivors = [state.merged_pool[0].idea_id, state.merged_pool[1].idea_id]
        compressed = compress_survivors(state)
        assert state.merged_pool[0].idea_id in compressed
        assert state.merged_pool[2].idea_id not in compressed


class TestCompressAllScorecards:
    def test_contains_scorecard_data(self):
        state = make_state_at_phase5()
        compressed = compress_all_scorecards(state)
        assert "Autonomy Composite" in compressed
        assert "Confidence" in compressed
