"""Atomic checkpoint persistence — save/load/resume DebateState."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from debate.config import DebateConfig
from debate.schemas.state import SCHEMA_VERSION, DebateState

logger = logging.getLogger(__name__)


class SchemaVersionMismatch(Exception):
    """Raised when a checkpoint's schema version doesn't match current."""


class CheckpointStore:
    """Persists DebateState as JSON with atomic writes and debug artifacts."""

    def __init__(self, config: DebateConfig, run_id: str) -> None:
        self._config = config
        self._run_id = run_id
        self._run_dir = config.checkpoint_path / run_id
        self._state_path = self._run_dir / "state.json"
        self._debug_dir = self._run_dir / "debug"

    def save(self, state: DebateState) -> None:
        """Atomically persist state: write to temp, then rename."""
        self._run_dir.mkdir(parents=True, exist_ok=True)

        data = state.model_dump(mode="json")
        json_bytes = json.dumps(data, indent=2, default=str).encode("utf-8")

        # Atomic write: temp file in same directory, then os.replace
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._run_dir), suffix=".tmp", prefix="state_"
        )
        try:
            os.write(fd, json_bytes)
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp_path, str(self._state_path))
            logger.debug("Checkpoint saved: %s", self._state_path)
        except Exception:
            os.close(fd) if not os.get_inheritable(fd) else None
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def load(self) -> DebateState:
        """Load state from checkpoint. Raises on schema version mismatch."""
        if not self._state_path.exists():
            raise FileNotFoundError(f"No checkpoint at {self._state_path}")

        data = json.loads(self._state_path.read_text())

        saved_version = data.get("meta", {}).get("schema_version", "unknown")
        if saved_version != SCHEMA_VERSION:
            raise SchemaVersionMismatch(
                f"Checkpoint schema version '{saved_version}' does not match "
                f"current '{SCHEMA_VERSION}'. Cannot safely resume."
            )

        return DebateState.model_validate(data)

    def exists(self) -> bool:
        """Check if a checkpoint exists for this run."""
        return self._state_path.exists()

    def save_debug_artifact(self, step_key: str, content: str) -> None:
        """Save a debug artifact (e.g., raw API response). Bounded by config."""
        self._debug_dir.mkdir(parents=True, exist_ok=True)

        # Enforce file count limit — remove oldest if at capacity
        existing = sorted(self._debug_dir.iterdir(), key=lambda p: p.stat().st_mtime)
        while len(existing) >= self._config.debug_max_files:
            oldest = existing.pop(0)
            oldest.unlink()
            logger.debug("Rotated debug artifact: %s", oldest.name)

        # Truncate content to max size
        max_bytes = self._config.debug_max_file_bytes
        if len(content.encode("utf-8")) > max_bytes:
            content = content[:max_bytes] + "\n... [TRUNCATED]"

        artifact_path = self._debug_dir / f"{step_key}.json"
        artifact_path.write_text(content)

    @staticmethod
    def list_runs(config: DebateConfig) -> list[str]:
        """List all available run IDs."""
        checkpoint_dir = config.checkpoint_path
        if not checkpoint_dir.exists():
            return []
        return [
            d.name
            for d in sorted(checkpoint_dir.iterdir())
            if d.is_dir() and (d / "state.json").exists()
        ]
