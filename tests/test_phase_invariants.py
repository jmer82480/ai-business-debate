"""Tests for phase transition invariants — can't skip phases, state is valid."""

import pytest

from debate.schemas.state import DebateState, Phase
from debate.schemas.votes import VoteRound
from debate.validators.phase import PhaseTransitionError, validate_phase_transition
from tests.conftest import make_idea, make_state_at_phase2, make_state_at_phase5
from debate.schemas.debate import DebateRound


class TestPhaseInvariants:
    def test_cannot_enter_phase3_without_phase2(self):
        state = DebateState()
        with pytest.raises(PhaseTransitionError):
            validate_phase_transition(state, Phase.PHASE_3_DEBATE)

    def test_cannot_enter_phase4_without_finalists(self):
        state = make_state_at_phase2()
        state.survivors = ["idea-0", "idea-1", "idea-2"]
        state.phase2_votes = VoteRound(phase=2, votes=[])
        # No debate rounds
        with pytest.raises(PhaseTransitionError, match="no debate rounds"):
            validate_phase_transition(state, Phase.PHASE_4_DEEP_DIVE)

    def test_cannot_enter_phase5_without_scorecards(self):
        state = make_state_at_phase5()
        state.scorecards = {}
        with pytest.raises(PhaseTransitionError, match="no scorecards"):
            validate_phase_transition(state, Phase.PHASE_5_CONVERGENCE)

    def test_cannot_complete_without_verdict(self):
        state = make_state_at_phase5()
        state.verdict = None
        with pytest.raises(PhaseTransitionError, match="no final verdict"):
            validate_phase_transition(state, Phase.COMPLETED)

    def test_valid_phase2_to_phase3(self):
        state = make_state_at_phase2()
        state.phase2_votes = VoteRound(phase=2, votes=[])
        state.survivors = ["idea-0", "idea-1", "idea-2"]
        # Should not raise
        validate_phase_transition(state, Phase.PHASE_3_DEBATE)

    def test_valid_phase3_to_phase4(self):
        state = make_state_at_phase2()
        state.survivors = ["idea-0", "idea-1"]
        state.phase2_votes = VoteRound(phase=2, votes=[])
        state.debate_rounds = [DebateRound(round_number=1)]
        state.finalists = ["idea-0", "idea-1"]
        # Should not raise
        validate_phase_transition(state, Phase.PHASE_4_DEEP_DIVE)

    def test_valid_phase4_to_phase5(self):
        state = make_state_at_phase5()
        # Should not raise
        validate_phase_transition(state, Phase.PHASE_5_CONVERGENCE)
