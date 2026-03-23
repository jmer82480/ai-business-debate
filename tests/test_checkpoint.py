"""Tests for checkpoint persistence — save/load, atomic writes, schema version."""

import json
import os

import pytest

from debate.config import DebateConfig
from debate.schemas.state import SCHEMA_VERSION, DebateState, RunMeta
from debate.storage.checkpoint import CheckpointStore, SchemaVersionMismatch
from tests.conftest import make_idea


class TestCheckpointStore:
    def test_save_and_load_roundtrip(self, config):
        store = CheckpointStore(config, "test-run")
        state = DebateState(meta=RunMeta(run_id="test-run"))
        state.phase1_ideas["bootstrapper"] = [make_idea(f"Idea {i}") for i in range(5)]

        store.save(state)
        loaded = store.load()

        assert loaded.meta.run_id == "test-run"
        assert len(loaded.phase1_ideas["bootstrapper"]) == 5

    def test_load_nonexistent_raises(self, config):
        store = CheckpointStore(config, "nonexistent")
        with pytest.raises(FileNotFoundError):
            store.load()

    def test_schema_version_mismatch(self, config):
        store = CheckpointStore(config, "version-test")
        state = DebateState(meta=RunMeta(run_id="version-test"))
        store.save(state)

        # Tamper with schema version
        state_path = config.checkpoint_path / "version-test" / "state.json"
        data = json.loads(state_path.read_text())
        data["meta"]["schema_version"] = "99.99.99"
        state_path.write_text(json.dumps(data))

        with pytest.raises(SchemaVersionMismatch, match="99.99.99"):
            store.load()

    def test_atomic_write_no_partial_file(self, config):
        store = CheckpointStore(config, "atomic-test")
        state = DebateState(meta=RunMeta(run_id="atomic-test"))
        store.save(state)

        # Verify no .tmp files remain
        run_dir = config.checkpoint_path / "atomic-test"
        tmp_files = list(run_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_exists(self, config):
        store = CheckpointStore(config, "exists-test")
        assert not store.exists()

        state = DebateState(meta=RunMeta(run_id="exists-test"))
        store.save(state)
        assert store.exists()

    def test_list_runs(self, config):
        for rid in ["run-a", "run-b", "run-c"]:
            store = CheckpointStore(config, rid)
            store.save(DebateState(meta=RunMeta(run_id=rid)))

        runs = CheckpointStore.list_runs(config)
        assert set(runs) == {"run-a", "run-b", "run-c"}

    def test_debug_artifact_saved(self, config):
        store = CheckpointStore(config, "debug-test")
        store.save_debug_artifact("step-1", '{"test": "data"}')

        debug_dir = config.checkpoint_path / "debug-test" / "debug"
        assert (debug_dir / "step-1.json").exists()

    def test_debug_artifact_bounded(self, config):
        config.debug_max_files = 3
        store = CheckpointStore(config, "bounded-test")

        for i in range(5):
            store.save_debug_artifact(f"step-{i}", f'{{"step": {i}}}')

        debug_dir = config.checkpoint_path / "bounded-test" / "debug"
        files = list(debug_dir.iterdir())
        assert len(files) <= 3

    def test_debug_artifact_truncated(self, config):
        config.debug_max_file_bytes = 50
        store = CheckpointStore(config, "truncate-test")
        store.save_debug_artifact("big-step", "x" * 200)

        content = (config.checkpoint_path / "truncate-test" / "debug" / "big-step.json").read_text()
        assert "[TRUNCATED]" in content
