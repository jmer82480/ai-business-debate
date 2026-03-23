"""Phase 2 — Merge & Vote prompts."""


def get_merge_prompt(all_ideas_text: str) -> str:
    """Prompt for the moderator to merge and deduplicate ideas."""
    return f"""Below are ideas proposed independently by four agents. Your job is to:

1. Merge all ideas into a single numbered pool
2. Deduplicate — if two agents proposed the same or very similar idea, merge them (note which agents proposed it, take the best elements)
3. Apply gate criteria and ELIMINATE any idea that clearly fails:
   - Startup cost over $500
   - AI autonomy composite below 70%
   - Customer acquisition depends on manual outbound sales
4. For each surviving idea, produce a merged entry using the submit_merged_pool tool

Flag any data conflicts between agents on the same idea.

{all_ideas_text}"""


def get_merge_tool_schema() -> dict:
    """Tool schema for submitting the merged pool."""
    return {
        "name": "submit_merged_pool",
        "description": "Submit the merged and deduplicated idea pool.",
        "input_schema": {
            "type": "object",
            "required": ["ideas", "eliminated", "conflicts"],
            "properties": {
                "ideas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "name", "description", "proposed_by",
                            "startup_cost_items", "startup_cost_total",
                            "autonomy", "revenue", "acquisition_path",
                            "moat", "platform_risk", "key_risk", "why_now", "evidence",
                        ],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "proposed_by": {"type": "array", "items": {"type": "string"}},
                            "startup_cost_items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "item": {"type": "string"},
                                        "cost_usd": {"type": "number"},
                                        "notes": {"type": "string"},
                                    },
                                    "required": ["item", "cost_usd"],
                                },
                            },
                            "startup_cost_total": {"type": "number"},
                            "autonomy": {
                                "type": "object",
                                "required": ["acquisition", "fulfillment", "support", "qa"],
                                "properties": {
                                    "acquisition": {"type": "integer"},
                                    "fulfillment": {"type": "integer"},
                                    "support": {"type": "integer"},
                                    "qa": {"type": "integer"},
                                },
                            },
                            "revenue": {
                                "type": "object",
                                "required": ["day_90", "month_12", "year_3_ceiling"],
                                "properties": {
                                    "day_90": {"type": "string"},
                                    "month_12": {"type": "string"},
                                    "year_3_ceiling": {"type": "string"},
                                },
                            },
                            "acquisition_path": {
                                "type": "object",
                                "required": ["first_10", "first_100", "first_1000"],
                                "properties": {
                                    "first_10": {"type": "string"},
                                    "first_100": {"type": "string"},
                                    "first_1000": {"type": "string"},
                                },
                            },
                            "moat": {"type": "string"},
                            "platform_risk": {"type": "string"},
                            "key_risk": {"type": "string"},
                            "why_now": {"type": "string"},
                            "evidence": {"type": "array", "items": {"type": "object"}},
                        },
                    },
                },
                "eliminated": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["name", "reason"],
                    },
                },
                "conflicts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "idea_name": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["idea_name", "description"],
                    },
                },
            },
        },
    }


def get_vote_prompt(merged_pool_text: str) -> str:
    """Prompt for an agent to vote on each idea in the merged pool."""
    return f"""Below is the merged idea pool. Vote YES or NO on each idea from YOUR perspective.

For each idea, use the submit_votes tool to submit your votes with a 1-2 sentence justification.

Rules:
- Apply gate criteria strictly
- Vote based on YOUR area of expertise
- Be honest — a bad idea is a bad idea regardless of who proposed it

{merged_pool_text}"""


def get_vote_tool_schema() -> dict:
    """Tool schema for submitting votes."""
    return {
        "name": "submit_votes",
        "description": "Submit your YES/NO votes on each idea.",
        "input_schema": {
            "type": "object",
            "required": ["votes"],
            "properties": {
                "votes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["idea_id", "vote", "justification"],
                        "properties": {
                            "idea_id": {"type": "string"},
                            "vote": {"type": "boolean", "description": "true=YES, false=NO"},
                            "justification": {"type": "string"},
                        },
                    },
                },
            },
        },
    }
