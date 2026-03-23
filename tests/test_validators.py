"""Tests for gate criteria, evidence standard, and phase transition validators."""

import pytest

from debate.schemas.ideas import AcquisitionPath, AutonomyScores
from debate.validators.gates import GateFailure, passes_gates, validate_gate_criteria
from debate.validators.evidence import EvidenceWarning, validate_evidence
from debate.validators.phase import PhaseTransitionError, validate_phase_transition
from debate.schemas.state import DebateState, Phase
from tests.conftest import make_idea, make_state_at_phase2


class TestGateCriteria:
    def test_passes_all_gates(self):
        idea = make_idea("Good Idea", cost=200.0, acq=80, ful=85, sup=75, qa=70)
        failures = validate_gate_criteria(idea)
        assert failures == []
        assert passes_gates(idea)

    def test_fails_cost_gate(self):
        idea = make_idea("Expensive", cost=600.0)
        failures = validate_gate_criteria(idea)
        assert any(f.gate == "startup_cost" for f in failures)
        assert not passes_gates(idea)

    def test_fails_autonomy_gate(self):
        idea = make_idea("Low Autonomy", acq=30, ful=40, sup=30, qa=20)
        failures = validate_gate_criteria(idea)
        assert any(f.gate == "ai_autonomy" for f in failures)

    def test_fails_acquisition_gate_cold_call(self):
        idea = make_idea("Cold Caller")
        idea.acquisition_path = AcquisitionPath(
            first_10="Cold call local businesses",
            first_100="More cold calls",
            first_1000="Hire sales team",
        )
        failures = validate_gate_criteria(idea)
        assert any(f.gate == "customer_acquisition" for f in failures)

    def test_fails_acquisition_gate_manual_outbound(self):
        idea = make_idea("Manual Outbound")
        idea.acquisition_path.first_10 = "Manual outbound emails to prospects"
        failures = validate_gate_criteria(idea)
        assert any(f.gate == "customer_acquisition" for f in failures)

    def test_exactly_500_passes(self):
        idea = make_idea("Borderline", cost=500.0)
        assert passes_gates(idea)

    def test_exactly_70_autonomy_passes(self):
        # Composite = 70*0.35 + 70*0.30 + 70*0.20 + 70*0.15 = 70
        idea = make_idea("Borderline Autonomy", acq=70, ful=70, sup=70, qa=70)
        assert passes_gates(idea)


class TestEvidenceValidation:
    def test_warns_on_no_evidence(self):
        idea = make_idea("No Evidence")
        idea.evidence = []
        warnings = validate_evidence(idea)
        assert any(w.field == "evidence" for w in warnings)

    def test_warns_on_short_fields(self):
        idea = make_idea("Short")
        idea.moat = "none"
        warnings = validate_evidence(idea)
        assert any(w.field == "moat" for w in warnings)

    def test_no_warnings_for_good_idea(self):
        idea = make_idea("Good")
        warnings = validate_evidence(idea)
        assert len(warnings) == 0


class TestPhaseTransitions:
    def test_phase1_to_phase2_requires_all_roles(self):
        state = DebateState()
        with pytest.raises(PhaseTransitionError, match="no ideas"):
            validate_phase_transition(state, Phase.PHASE_2_MERGE_VOTE)

    def test_phase1_to_phase2_requires_min_ideas(self):
        state = DebateState()
        state.phase1_ideas["bootstrapper"] = [make_idea(f"Idea {i}") for i in range(3)]
        with pytest.raises(PhaseTransitionError, match="missing ideas"):
            validate_phase_transition(state, Phase.PHASE_2_MERGE_VOTE)

    def test_phase2_requires_merged_pool(self):
        state = make_state_at_phase2()
        state.merged_pool = []
        with pytest.raises(PhaseTransitionError, match="no merged pool"):
            validate_phase_transition(state, Phase.PHASE_3_DEBATE)

    def test_phase2_requires_survivors(self):
        state = make_state_at_phase2()
        from debate.schemas.votes import VoteRound
        state.phase2_votes = VoteRound(phase=2, votes=[])
        state.survivors = []
        with pytest.raises(PhaseTransitionError, match="survivors"):
            validate_phase_transition(state, Phase.PHASE_3_DEBATE)

    def test_valid_phase1_to_phase2(self):
        state = make_state_at_phase2()
        # Should not raise
        validate_phase_transition(state, Phase.PHASE_2_MERGE_VOTE)
