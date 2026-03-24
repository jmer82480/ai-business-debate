"""Moderator role — process controller, synthesizer, verdict writer."""

from __future__ import annotations

from typing import Any

from debate.roles.base import BaseRole
from debate.prompts.phase2 import get_merge_prompt, get_merge_tool_schema
from debate.prompts.phase3 import (
    get_moderator_synthesis_prompt,
    get_synthesis_tool_schema,
)
from debate.prompts.phase4 import get_deep_dive_prompt, get_deep_dive_tool_schema
from debate.prompts.phase5 import get_verdict_prompt, get_verdict_tool_schema
from debate.schemas.ideas import AcquisitionPath, AutonomyScores, Idea, RevenueHorizons


class Moderator(BaseRole):
    role_name = "moderator"

    def merge_ideas(self, all_ideas_text: str) -> tuple[dict[str, Any], str]:
        """Phase 2a: merge and deduplicate all ideas.

        Uses 32768 max_tokens — with 4 roles × 8 ideas and 15 output fields
        per merged idea, 16384 is not enough and causes truncation. Streaming
        is used automatically for max_tokens > 16384 by the Anthropic client.
        """
        tool = get_merge_tool_schema()
        response = self._call_llm(
            get_merge_prompt(all_ideas_text),
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_merged_pool"},
            max_tokens=32768,
        )
        data = self._extract_tool_data(response, "submit_merged_pool")
        # Validate merge produced ideas
        ideas = data.get("ideas", [])
        if len(ideas) == 0:
            from debate.roles.base import BadOutputError
            raise BadOutputError(
                f"[{self.role_name}] Merge produced 0 ideas. "
                "The merged pool must contain at least 1 idea."
            )
        return data, self._get_raw_for_debug(response)

    def synthesize_round(
        self,
        round_number: int,
        all_arguments_text: str,
        survivor_ids: list[str],
    ) -> tuple[dict[str, Any], str]:
        """Phase 3: synthesize a debate round."""
        tool = get_synthesis_tool_schema()
        response = self._call_llm(
            get_moderator_synthesis_prompt(round_number, all_arguments_text, survivor_ids),
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_synthesis"},
        )
        data = self._extract_tool_data(response, "submit_synthesis")
        return data, self._get_raw_for_debug(response)

    def deep_dive(
        self, idea_name: str, idea_id: str, idea_context: str, debate_context: str
    ) -> tuple[dict[str, Any], str]:
        """Phase 4: comprehensive deep dive on a finalist."""
        tool = get_deep_dive_tool_schema()
        response = self._call_llm(
            get_deep_dive_prompt(idea_name, idea_context, debate_context),
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_deep_dive"},
            model=self._config.model_deep_dive,
            max_tokens=16384,
        )
        data = self._extract_tool_data(response, "submit_deep_dive")
        return data, self._get_raw_for_debug(response)

    def write_verdict(
        self,
        votes_text: str,
        scorecards_text: str,
        finalist_ids: list[str],
    ) -> tuple[dict[str, Any], str]:
        """Phase 5: write the final verdict."""
        tool = get_verdict_tool_schema()
        response = self._call_llm(
            get_verdict_prompt(votes_text, scorecards_text, finalist_ids),
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_verdict"},
            max_tokens=16384,
        )
        data = self._extract_tool_data(response, "submit_verdict")
        return data, self._get_raw_for_debug(response)

    @staticmethod
    def parse_merged_ideas(data: dict[str, Any]) -> list[Idea]:
        """Parse moderator's merged pool into Idea models."""
        ideas: list[Idea] = []
        for raw in data.get("ideas", []):
            autonomy_raw = raw.get("autonomy", {})
            revenue_raw = raw.get("revenue", {})
            acq_raw = raw.get("acquisition_path", {})

            idea = Idea(
                idea_id=raw.get("idea_id", ""),
                name=raw["name"],
                description=raw["description"],
                proposed_by=raw.get("proposed_by", []),
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
