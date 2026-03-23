"""Phase transition validation — pre/post conditions for each phase."""

from __future__ import annotations

from debate.schemas.state import DebateState, Phase


class PhaseTransitionError(Exception):
    """Raised when a phase transition's preconditions aren't met."""


# Minimum ideas per role in Phase 1
MIN_IDEAS_PER_ROLE = 5
MAX_IDEAS_PER_ROLE = 8

# Minimum YES votes to survive Phase 2
MIN_YES_VOTES = 3

# Target survivor range
MIN_SURVIVORS = 2
MAX_SURVIVORS_TARGET = 12

# Minimum finalists for Phase 4
MIN_FINALISTS = 2
MAX_FINALISTS = 3


def validate_phase_transition(state: DebateState, target_phase: Phase) -> None:
    """Validate that we can transition to the target phase. Raises on failure."""

    if target_phase == Phase.PHASE_2_MERGE_VOTE:
        _validate_phase1_complete(state)
    elif target_phase == Phase.PHASE_3_DEBATE:
        _validate_phase2_complete(state)
    elif target_phase == Phase.PHASE_4_DEEP_DIVE:
        _validate_phase3_complete(state)
    elif target_phase == Phase.PHASE_5_CONVERGENCE:
        _validate_phase4_complete(state)
    elif target_phase == Phase.COMPLETED:
        _validate_phase5_complete(state)


def _validate_phase1_complete(state: DebateState) -> None:
    """Phase 1 → 2: all roles must have produced ideas."""
    if not state.phase1_ideas:
        raise PhaseTransitionError("Phase 1 incomplete: no ideas produced by any role.")

    expected_roles = {"bootstrapper", "market_analyst", "automation_architect", "devils_advocate"}
    missing = expected_roles - set(state.phase1_ideas.keys())
    if missing:
        raise PhaseTransitionError(f"Phase 1 incomplete: missing ideas from {missing}")

    for role, ideas in state.phase1_ideas.items():
        if len(ideas) < MIN_IDEAS_PER_ROLE:
            raise PhaseTransitionError(
                f"Phase 1 incomplete: {role} produced {len(ideas)} ideas "
                f"(minimum {MIN_IDEAS_PER_ROLE})"
            )


def _validate_phase2_complete(state: DebateState) -> None:
    """Phase 2 → 3: merged pool exists and survivors identified."""
    if not state.merged_pool:
        raise PhaseTransitionError("Phase 2 incomplete: no merged pool.")
    if state.phase2_votes is None:
        raise PhaseTransitionError("Phase 2 incomplete: no votes recorded.")
    if len(state.survivors) < MIN_SURVIVORS:
        raise PhaseTransitionError(
            f"Phase 2 produced only {len(state.survivors)} survivors "
            f"(minimum {MIN_SURVIVORS})"
        )


def _validate_phase3_complete(state: DebateState) -> None:
    """Phase 3 → 4: debate rounds complete, finalists selected."""
    if not state.debate_rounds:
        raise PhaseTransitionError("Phase 3 incomplete: no debate rounds.")
    if len(state.finalists) < MIN_FINALISTS:
        raise PhaseTransitionError(
            f"Phase 3 produced only {len(state.finalists)} finalists "
            f"(minimum {MIN_FINALISTS})"
        )


def _validate_phase4_complete(state: DebateState) -> None:
    """Phase 4 → 5: all finalists have scorecards."""
    if not state.scorecards:
        raise PhaseTransitionError("Phase 4 incomplete: no scorecards.")
    missing = set(state.finalists) - set(state.scorecards.keys())
    if missing:
        raise PhaseTransitionError(
            f"Phase 4 incomplete: missing scorecards for {missing}"
        )


def _validate_phase5_complete(state: DebateState) -> None:
    """Phase 5 → Completed: verdict exists."""
    if state.verdict is None:
        raise PhaseTransitionError("Phase 5 incomplete: no final verdict.")
