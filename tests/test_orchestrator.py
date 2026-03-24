"""Tests for orchestrator — full flow with FakeLLMClient."""

import pytest

from debate.config import DebateConfig
from debate.orchestrator import Orchestrator
from debate.schemas.state import Phase, StepStatus


class TestOrchestratorDryRun:
    """Test the orchestrator with the CLI's dry-run fake client."""

    def test_full_flow_completes(self, config):
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        state = orch.state
        assert state.current_phase == Phase.COMPLETED
        assert state.verdict is not None
        assert state.verdict.winner_idea_id != ""

    def test_phase1_produces_ideas(self, config):
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)

        # Run just phase 1
        orch._run_phase1()

        assert len(orch.state.phase1_ideas) == 4
        for role, ideas in orch.state.phase1_ideas.items():
            assert len(ideas) == 5, f"{role} produced {len(ideas)} ideas"

    def test_checkpoint_created(self, config):
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        from debate.storage.checkpoint import CheckpointStore
        store = CheckpointStore(config, orch.run_id)
        assert store.exists()
        loaded = store.load()
        assert loaded.current_phase == Phase.COMPLETED

    def test_resume_skips_completed_steps(self, config):
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        # Resume — should be a no-op since everything is completed
        orch2 = Orchestrator(make_dry_run_client(), config, run_id=orch.run_id)
        orch2.resume()
        # State should be loaded
        assert orch2.state.current_phase == Phase.COMPLETED

    def test_output_files_created(self, config):
        from debate.llm.dry_run import make_dry_run_client
        from pathlib import Path

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        output = Path(config.output_dir)
        assert (output / "verdict.md").exists()
        assert (output / "final-plan.md").exists()
        assert (output / "phase1").is_dir()

    def test_steps_tracked(self, config):
        from debate.llm.dry_run import make_dry_run_client

        client = make_dry_run_client()
        orch = Orchestrator(client, config)
        orch.run()

        # Should have many completed steps
        completed = [
            k for k, v in orch.state.steps.items()
            if v.status == StepStatus.COMPLETED
        ]
        assert len(completed) > 10
