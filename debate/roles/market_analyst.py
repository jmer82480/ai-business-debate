"""Market Analyst role — demand/competition evaluator."""

from __future__ import annotations

from typing import Any

from debate.roles.base import BaseRole
from debate.roles.bootstrapper import _parse_debate_arguments, _parse_ideas, _parse_votes
from debate.prompts.phase1 import IDEATION_PROMPT, get_phase1_tool_schema
from debate.prompts.phase2 import get_vote_prompt, get_vote_tool_schema
from debate.prompts.phase3 import get_debate_prompt, get_debate_tool_schema
from debate.prompts.phase5 import get_final_vote_prompt, get_final_vote_tool_schema
from debate.schemas.debate import DebateArgument
from debate.schemas.ideas import Idea
from debate.schemas.votes import Vote


class MarketAnalyst(BaseRole):
    role_name = "market_analyst"

    def generate_ideas(self) -> tuple[list[Idea], str]:
        tool = get_phase1_tool_schema()
        response = self._call_llm(
            IDEATION_PROMPT,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_ideas"},
            max_tokens=16384,
        )
        data = self._extract_tool_data(response, "submit_ideas")
        return _parse_ideas(data, self.role_name), self._get_raw_for_debug(response)

    def vote(self, merged_pool_text: str, idea_ids: list[str]) -> tuple[list[Vote], str]:
        tool = get_vote_tool_schema()
        response = self._call_llm(
            get_vote_prompt(merged_pool_text),
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_votes"},
        )
        data = self._extract_tool_data(response, "submit_votes")
        return _parse_votes(data, self.role_name), self._get_raw_for_debug(response)

    def debate(
        self, survivors_text: str, prior_round_text: str, round_number: int
    ) -> tuple[list[DebateArgument], str]:
        tool = get_debate_tool_schema()
        prompt = get_debate_prompt(self.role_name, survivors_text, prior_round_text, round_number)
        response = self._call_llm(
            prompt, tools=[tool], tool_choice={"type": "tool", "name": "submit_debate"},
        )
        data = self._extract_tool_data(response, "submit_debate")
        return _parse_debate_arguments(data, self.role_name), self._get_raw_for_debug(response)

    def final_vote(self, scorecards_text: str) -> tuple[dict[str, Any], str]:
        tool = get_final_vote_tool_schema()
        response = self._call_llm(
            get_final_vote_prompt(self.role_name, scorecards_text),
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_final_vote"},
        )
        data = self._extract_tool_data(response, "submit_final_vote")
        return data, self._get_raw_for_debug(response)
