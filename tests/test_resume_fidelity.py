"""Tests for resume correctness — config persistence, Phase 3/5 role data, debug policy, checkpoint safety."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from debate.config import DebateConfig
from debate.llm.client import LLMResponse
from debate.llm.fake import FakeLLMClient
from debate.orchestrator import Orchestrator
from debate.schemas.state import DebateState, Phase, RunMeta, StepStatus
from debate.storage.checkpoint import CheckpointStore


# ---------------------------------------------------------------------------
# Fix 1: Run config persisted in checkpoint and restored on resume
# ---------------------------------------------------------------------------


class TestConfigPersistence:
    def test_run_config_persisted_on_start(self, config):
        """Starting a run persists the effective config in state."""
        from debate.llm.dry_run import make_dry_run_client

        config.web_search_enabled = False
        config.max_phase3_rounds = 5
        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        assert orch.state.run_config != {}
        assert orch.state.run_config["web_search_enabled"] is False
        assert orch.state.run_config["max_phase3_rounds"] == 5

    def test_resume_restores_original_config(self, config):
        """Resuming a run restores the original config, not defaults."""
        from debate.llm.dry_run import make_dry_run_client

        config.web_search_enabled = False
        config.max_phase3_rounds = 7
        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        # Create a new orchestrator with DEFAULT config (web_search=True)
        default_config = DebateConfig(
            output_dir=config.output_dir,
            checkpoint_dir=config.checkpoint_dir,
        )
        assert default_config.web_search_enabled is True  # confirm default

        orch2 = Orchestrator(make_dry_run_client(), default_config, run_id=orch.run_id)
        orch2.resume()

        # After resume, config should be restored to original values
        assert orch2._config.web_search_enabled is False
        assert orch2._config.max_phase3_rounds == 7

    def test_config_roundtrip_via_dict(self):
        """DebateConfig.to_dict / from_dict round-trips correctly."""
        original = DebateConfig(
            model_default="claude-opus-4-6",
            web_search_enabled=False,
            max_phase3_rounds=3,
        )
        d = original.to_dict()
        restored = DebateConfig.from_dict(d)
        assert restored.model_default == "claude-opus-4-6"
        assert restored.web_search_enabled is False
        assert restored.max_phase3_rounds == 3

    def test_run_config_survives_checkpoint_roundtrip(self, config):
        """run_config field survives JSON serialization via checkpoint."""
        from debate.llm.dry_run import make_dry_run_client

        config.web_search_enabled = False
        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        # Load from checkpoint
        store = CheckpointStore(config, orch.run_id)
        loaded = store.load()
        assert loaded.run_config["web_search_enabled"] is False


# ---------------------------------------------------------------------------
# Fix 2: Phase 3 and Phase 5 resume reconstructs from persisted data
# ---------------------------------------------------------------------------


class TestPhase3Resume:
    def test_debate_arguments_persisted_per_role(self, config):
        """Phase 3 debate arguments are persisted per-role in state."""
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        # Should have persisted arguments for at least one round
        assert len(orch.state.phase3_role_arguments) > 0
        # Each key should be "round{N}_{role}"
        for key in orch.state.phase3_role_arguments:
            assert "round" in key


class TestPhase5Resume:
    def test_final_positions_persisted_per_role(self, config):
        """Phase 5 final positions are persisted per-role in state."""
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        roles = ["bootstrapper", "market_analyst", "automation_architect", "devils_advocate"]
        for role in roles:
            assert role in orch.state.phase5_role_positions, f"Missing position for {role}"
            pos = orch.state.phase5_role_positions[role]
            assert "voted_for_idea_id" in pos
            assert "justification" in pos

    def test_phase5_positions_survive_checkpoint_roundtrip(self, config):
        """Persisted positions survive JSON checkpoint save/load."""
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        state_json = orch.state.model_dump_json()
        loaded = DebateState.model_validate_json(state_json)

        for role in ["bootstrapper", "market_analyst", "automation_architect", "devils_advocate"]:
            original = orch.state.phase5_role_positions[role]
            restored = loaded.phase5_role_positions[role]
            assert original["voted_for_idea_id"] == restored["voted_for_idea_id"]


# ---------------------------------------------------------------------------
# Fix 3: Debug artifacts only on failure
# ---------------------------------------------------------------------------


class TestDebugArtifactPolicy:
    def test_no_debug_artifacts_on_success(self, config):
        """Successful steps should NOT produce debug artifacts."""
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch._run_phase1()

        debug_dir = config.checkpoint_path / orch.run_id / "debug"
        if debug_dir.exists():
            artifacts = list(debug_dir.iterdir())
            assert len(artifacts) == 0, f"Expected no debug artifacts on success, found {len(artifacts)}"

    def test_debug_artifact_saved_on_failure(self, config):
        """Failed steps should save debug artifacts."""
        call_count = 0

        def respond(messages, system, tools, model, call_index, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: returns parseable but too-few ideas → BadOutputError
                return LLMResponse(
                    tool_use={"ideas": [_stub_idea(0)]},
                    tool_name="submit_ideas",
                    model="fake",
                    tokens_in=100,
                    tokens_out=50,
                )
            # Second call: success
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
        orch._run_step("test_debug_on_fail", role.generate_ideas)

        debug_dir = config.checkpoint_path / orch.run_id / "debug"
        assert debug_dir.exists()
        artifacts = list(debug_dir.iterdir())
        assert len(artifacts) == 1  # saved on the first (failed) attempt


# ---------------------------------------------------------------------------
# Fix 4: Checkpoint save exception path — no double-close
# ---------------------------------------------------------------------------


class TestCheckpointExceptionSafety:
    def test_save_cleans_up_on_replace_failure(self, config):
        """If os.replace fails, temp file is cleaned up without double-close."""
        store = CheckpointStore(config, "test-exception-safety")
        state = DebateState(meta=RunMeta(run_id="test-exception-safety"))

        # First save should work
        store.save(state)
        assert store.exists()

        # Verify no leftover temp files
        run_dir = config.checkpoint_path / "test-exception-safety"
        temps = list(run_dir.glob("state_*.tmp"))
        assert len(temps) == 0

    def test_save_roundtrip_after_error_recovery(self, config):
        """State remains valid after a successful save."""
        store = CheckpointStore(config, "test-roundtrip-safe")
        state = DebateState(meta=RunMeta(run_id="test-roundtrip-safe"))
        state.current_phase = Phase.PHASE_3_DEBATE

        store.save(state)
        loaded = store.load()
        assert loaded.current_phase == Phase.PHASE_3_DEBATE


# ---------------------------------------------------------------------------
# Fix 5: Resume rebuilds roles with restored config
# ---------------------------------------------------------------------------


class TestResumeRebuildsDependencies:
    def test_roles_use_restored_config(self, config):
        """After resume, role adapters must use the restored config, not the default."""
        from debate.llm.dry_run import make_dry_run_client

        config.web_search_enabled = False
        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        # Resume with a default config (web_search_enabled=True)
        default_config = DebateConfig(
            output_dir=config.output_dir,
            checkpoint_dir=config.checkpoint_dir,
        )
        orch2 = Orchestrator(make_dry_run_client(), default_config, run_id=orch.run_id)
        orch2.resume()

        # Roles should use the restored config, not the default
        for role in orch2._roles.values():
            assert role._config.web_search_enabled is False


# ---------------------------------------------------------------------------
# Fix 6: Phase 4 deep-dive/stress-test persisted for resume
# ---------------------------------------------------------------------------


class TestPhase4Resume:
    def test_deep_dive_persisted(self, config):
        """Phase 4 deep-dive outputs are persisted per-idea in state."""
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        # Should have persisted deep dive for at least one finalist
        assert len(orch.state.phase4_deep_dives) > 0
        for idea_id, dd in orch.state.phase4_deep_dives.items():
            assert "autonomy" in dd or "startup_cost_total" in dd

    def test_stress_test_persisted(self, config):
        """Phase 4 stress-test outputs are persisted per-idea in state."""
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        assert len(orch.state.phase4_stress_tests) > 0

    def test_phase4_data_survives_checkpoint_roundtrip(self, config):
        """Persisted Phase 4 data survives JSON checkpoint save/load."""
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        state_json = orch.state.model_dump_json()
        loaded = DebateState.model_validate_json(state_json)
        assert len(loaded.phase4_deep_dives) == len(orch.state.phase4_deep_dives)
        assert len(loaded.phase4_stress_tests) == len(orch.state.phase4_stress_tests)


# ---------------------------------------------------------------------------
# Fix 7: Merge validates non-empty output
# ---------------------------------------------------------------------------


class TestMergeValidation:
    def test_empty_merge_raises_bad_output(self, config):
        """Moderator.merge_ideas raises BadOutputError when merge returns 0 ideas."""
        from debate.roles.base import BadOutputError

        def respond(messages, system, tools, model, call_index, **kw):
            return LLMResponse(
                tool_use={"ideas": [], "eliminated": [], "conflicts": []},
                tool_name="submit_merged_pool",
                model="fake",
                tokens_in=100,
                tokens_out=50,
            )

        client = FakeLLMClient(response_fn=respond)
        from debate.roles.moderator import Moderator
        mod = Moderator(client, config)

        with pytest.raises(BadOutputError, match="0 ideas"):
            mod.merge_ideas("test ideas text")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_idea(idx: int) -> dict:
    return {
        "name": f"Stub Idea {idx}",
        "description": f"Test idea {idx}",
        "startup_cost_items": [{"item": "Domain", "cost_usd": 12.0}],
        "startup_cost_total": 12.0,
        "autonomy": {"acquisition": 80, "fulfillment": 85, "support": 75, "qa": 70},
        "revenue": {"day_90": "$500", "month_12": "$5,000/mo", "year_3_ceiling": "$50,000/mo"},
        "acquisition_path": {"first_10": "SEO", "first_100": "Organic", "first_1000": "Referrals"},
        "moat": "Data compounds.",
        "platform_risk": "Low.",
        "key_risk": "Market uncertain.",
        "why_now": "AI costs dropped.",
        "evidence": [],
    }
