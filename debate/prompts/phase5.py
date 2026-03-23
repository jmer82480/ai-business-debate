"""Phase 5 — Convergence prompts."""


def get_final_vote_prompt(role: str, scorecards_text: str) -> str:
    """Prompt for an agent's final vote."""
    da_extra = ""
    if role == "devils_advocate":
        da_extra = (
            "\nCRITICAL: Even if you vote for the winner, you MUST state your "
            "strongest remaining objection. This is required by the protocol."
        )

    return f"""## Phase 5 — Final Convergence Vote

The debate has reached its final phase. Below are the scorecards for all finalists,
including Devil's Advocate stress test results.

{scorecards_text}

Using the submit_final_vote tool:
1. Rank ALL finalists from best to worst
2. Cast your FINAL VOTE for the winner (one idea_id)
3. Explain why in 2-3 sentences from your perspective
{da_extra}"""


def get_final_vote_tool_schema() -> dict:
    """Tool schema for final vote."""
    return {
        "name": "submit_final_vote",
        "description": "Submit your final vote and ranking.",
        "input_schema": {
            "type": "object",
            "required": ["voted_for_idea_id", "ranking", "justification"],
            "properties": {
                "voted_for_idea_id": {"type": "string"},
                "ranking": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "idea_ids ordered best to worst",
                },
                "justification": {"type": "string"},
                "remaining_concerns": {"type": "string"},
            },
        },
    }


def get_verdict_prompt(
    votes_text: str,
    scorecards_text: str,
    finalist_ids: list[str],
) -> str:
    """Prompt for the moderator to write the final verdict."""
    return f"""## Write the Final Verdict

All agents have voted. Below are their votes and the scorecards.

{votes_text}

{scorecards_text}

Using the submit_verdict tool, write:

1. A **final ranked table** of all finalists sorted by autonomy composite, with columns for
   every scorecard dimension plus an "Overall Finish" column. The Overall Finish may differ
   from autonomy sort if a lower-autonomy idea has meaningfully better ceiling, lower risk,
   or stronger WTP evidence — explain any deviation.

2. The **winner** and why it won

3. The **runner-up** and specifically why it lost

4. Each agent's **final position**

5. The Devil's Advocate's **remaining concerns** (even if they voted yes)

6. An **honest confidence level** (how certain is the group this is the right pick)

Finalist IDs: {', '.join(finalist_ids)}"""


def get_verdict_tool_schema() -> dict:
    """Tool schema for the final verdict."""
    return {
        "name": "submit_verdict",
        "description": "Submit the final verdict document.",
        "input_schema": {
            "type": "object",
            "required": [
                "ranked_table", "winner_idea_id", "winner_narrative",
                "runner_up_idea_id", "runner_up_narrative",
                "agent_positions", "devils_advocate_remaining_concerns",
                "group_confidence",
            ],
            "properties": {
                "ranked_table": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "idea_id", "idea_name", "autonomy_acquisition",
                            "autonomy_fulfillment", "autonomy_support", "autonomy_qa",
                            "autonomy_composite", "growth_ceiling", "startup_cost",
                            "time_to_first_dollar", "defensibility", "platform_risk",
                            "hidden_human_labor_risk", "willingness_to_pay",
                            "overall_confidence", "overall_finish",
                        ],
                        "properties": {
                            "idea_id": {"type": "string"},
                            "idea_name": {"type": "string"},
                            "autonomy_acquisition": {"type": "integer"},
                            "autonomy_fulfillment": {"type": "integer"},
                            "autonomy_support": {"type": "integer"},
                            "autonomy_qa": {"type": "integer"},
                            "autonomy_composite": {"type": "number"},
                            "growth_ceiling": {"type": "string"},
                            "startup_cost": {"type": "number"},
                            "time_to_first_dollar": {"type": "string"},
                            "defensibility": {"type": "string"},
                            "platform_risk": {"type": "string"},
                            "hidden_human_labor_risk": {"type": "string"},
                            "willingness_to_pay": {"type": "string"},
                            "overall_confidence": {"type": "string"},
                            "overall_finish": {"type": "integer"},
                        },
                    },
                },
                "winner_idea_id": {"type": "string"},
                "winner_narrative": {"type": "string"},
                "runner_up_idea_id": {"type": "string"},
                "runner_up_narrative": {"type": "string"},
                "agent_positions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["role", "voted_for_idea_id", "justification"],
                        "properties": {
                            "role": {"type": "string"},
                            "voted_for_idea_id": {"type": "string"},
                            "ranking": {"type": "array", "items": {"type": "string"}},
                            "justification": {"type": "string"},
                            "remaining_concerns": {"type": "string"},
                        },
                    },
                },
                "devils_advocate_remaining_concerns": {"type": "string"},
                "group_confidence": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
            },
        },
    }
