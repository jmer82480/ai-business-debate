"""Bootstrapper role — cost-focused idea evaluator."""

from __future__ import annotations

from typing import Any

from debate.roles.base import BadOutputError, BaseRole
from debate.schemas.ideas import AcquisitionPath, AutonomyScores, Idea, RevenueHorizons
from debate.prompts.phase1 import IDEATION_PROMPT, get_phase1_tool_schema
from debate.prompts.phase2 import get_vote_prompt, get_vote_tool_schema
from debate.prompts.phase3 import get_debate_prompt, get_debate_tool_schema
from debate.prompts.phase5 import get_final_vote_prompt, get_final_vote_tool_schema
from debate.schemas.votes import Vote
from debate.schemas.debate import DebateArgument, FailureScenario


class Bootstrapper(BaseRole):
    role_name = "bootstrapper"

    def generate_ideas(self) -> tuple[list[Idea], str]:
        """Phase 1: generate ideas. Returns (ideas, raw_debug)."""
        tool = get_phase1_tool_schema()
        response = self._call_llm(
            IDEATION_PROMPT,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_ideas"},
            max_tokens=16384,
        )
        data = self._extract_tool_data(response, "submit_ideas")
        ideas = _parse_ideas(data, self.role_name)
        return ideas, self._get_raw_for_debug(response)

    def vote(self, merged_pool_text: str, idea_ids: list[str]) -> tuple[list[Vote], str]:
        """Phase 2: vote on merged pool."""
        tool = get_vote_tool_schema()
        response = self._call_llm(
            get_vote_prompt(merged_pool_text),
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_votes"},
        )
        data = self._extract_tool_data(response, "submit_votes")
        votes = _parse_votes(data, self.role_name)
        return votes, self._get_raw_for_debug(response)

    def debate(
        self, survivors_text: str, prior_round_text: str, round_number: int
    ) -> tuple[list[DebateArgument], str]:
        """Phase 3: debate round."""
        tool = get_debate_tool_schema()
        prompt = get_debate_prompt(self.role_name, survivors_text, prior_round_text, round_number)
        response = self._call_llm(
            prompt,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_debate"},
        )
        data = self._extract_tool_data(response, "submit_debate")
        args = _parse_debate_arguments(data, self.role_name)
        return args, self._get_raw_for_debug(response)

    def final_vote(self, scorecards_text: str) -> tuple[dict[str, Any], str]:
        """Phase 5: final convergence vote."""
        tool = get_final_vote_tool_schema()
        response = self._call_llm(
            get_final_vote_prompt(self.role_name, scorecards_text),
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_final_vote"},
        )
        data = self._extract_tool_data(response, "submit_final_vote")
        return data, self._get_raw_for_debug(response)


# --- Shared parsing helpers (used by all role subclasses) ---

MIN_IDEAS = 5


def _parse_ideas(data: dict[str, Any], role: str) -> list[Idea]:
    """Parse raw tool_use output into Idea models.

    Raises BadOutputError if fewer than MIN_IDEAS are returned — this is
    a concrete corrective reprompt path: the output is structurally valid
    JSON but logically insufficient.
    """
    raw_ideas = data.get("ideas", [])
    if len(raw_ideas) < MIN_IDEAS:
        raise BadOutputError(
            f"[{role}] Returned {len(raw_ideas)} ideas but minimum is {MIN_IDEAS}. "
            f"Please return at least {MIN_IDEAS} distinct business ideas."
        )

    ideas: list[Idea] = []
    for raw in raw_ideas:
        autonomy_raw = raw.get("autonomy", {})
        revenue_raw = raw.get("revenue", {})
        acq_raw = raw.get("acquisition_path", {})

        idea = Idea(
            name=raw["name"],
            description=raw["description"],
            proposed_by=[role],
            startup_cost_items=raw.get("startup_cost_items", []),
            startup_cost_total=raw.get("startup_cost_total", 0),
            autonomy=AutonomyScores(
                acquisition=autonomy_raw.get("acquisition", 0),
                fulfillment=autonomy_raw.get("fulfillment", 0),
                support=autonomy_raw.get("support", 0),
                qa=autonomy_raw.get("qa", 0),
            ),
            revenue=RevenueHorizons(
                day_90=revenue_raw.get("day_90", ""),
                month_12=revenue_raw.get("month_12", ""),
                year_3_ceiling=revenue_raw.get("year_3_ceiling", ""),
            ),
            acquisition_path=AcquisitionPath(
                first_10=acq_raw.get("first_10", ""),
                first_100=acq_raw.get("first_100", ""),
                first_1000=acq_raw.get("first_1000", ""),
            ),
            moat=raw.get("moat", ""),
            platform_risk=raw.get("platform_risk", ""),
            key_risk=raw.get("key_risk", ""),
            why_now=raw.get("why_now", ""),
            evidence=raw.get("evidence", []),
        )
        ideas.append(idea)
    return ideas


def _parse_votes(data: dict[str, Any], role: str) -> list[Vote]:
    """Parse raw vote tool_use output into Vote models."""
    votes: list[Vote] = []
    for raw in data.get("votes", []):
        votes.append(
            Vote(
                idea_id=raw["idea_id"],
                role=role,
                vote=raw["vote"],
                justification=raw.get("justification", ""),
            )
        )
    return votes


def _parse_debate_arguments(data: dict[str, Any], role: str) -> list[DebateArgument]:
    """Parse raw debate tool_use output into DebateArgument models."""
    args: list[DebateArgument] = []
    for raw in data.get("arguments", []):
        scenarios = [
            FailureScenario(
                scenario=s.get("scenario", ""),
                evidence=s.get("evidence", ""),
                likelihood=s.get("likelihood", ""),
            )
            for s in raw.get("failure_scenarios", [])
        ]
        args.append(
            DebateArgument(
                idea_id=raw["idea_id"],
                role=role,
                position=raw.get("position", "response"),
                argument=raw.get("argument", ""),
                vote=raw.get("vote"),
                failure_scenarios=scenarios,
            )
        )
    return args
