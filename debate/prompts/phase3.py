"""Phase 3 — Debate Rounds prompts."""


def get_debate_prompt(
    role: str,
    survivors_text: str,
    prior_round_text: str,
    round_number: int,
) -> str:
    """Prompt for an agent to debate surviving ideas."""
    prior_context = ""
    if prior_round_text:
        prior_context = f"""
## Prior Round Summary
{prior_round_text}
"""

    da_extra = ""
    if role == "devils_advocate":
        da_extra = """
CRITICAL: You MUST present at least 2 concrete failure scenarios for EVERY idea you consider viable.
Not vague "it might not work" — specific, named ways the business dies.
Apply the "disguised service business" test: could this serve its 50th customer
without meaningfully more human time than its 5th?
"""

    return f"""## Debate Round {round_number}

Below are the surviving ideas. For each, provide:
1. Your assessment (bull case or bear case) from your expertise area
2. A YES (keep) or NO (eliminate) vote with justification
3. Any new evidence you found via web search

Use the submit_debate tool to submit your arguments.

"I agree" is BANNED — you must add new evidence or a new angle.
{da_extra}
{prior_context}
## Surviving Ideas
{survivors_text}"""


def get_debate_tool_schema() -> dict:
    """Tool schema for debate round submissions."""
    return {
        "name": "submit_debate",
        "description": "Submit your debate arguments and votes for this round.",
        "input_schema": {
            "type": "object",
            "required": ["arguments"],
            "properties": {
                "arguments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["idea_id", "position", "argument", "vote"],
                        "properties": {
                            "idea_id": {"type": "string"},
                            "position": {
                                "type": "string",
                                "enum": ["bull", "bear", "response"],
                            },
                            "argument": {"type": "string"},
                            "vote": {"type": "boolean", "description": "true=keep, false=eliminate"},
                            "failure_scenarios": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "scenario": {"type": "string"},
                                        "evidence": {"type": "string"},
                                        "likelihood": {"type": "string"},
                                    },
                                    "required": ["scenario", "evidence"],
                                },
                            },
                        },
                    },
                },
            },
        },
    }


def get_moderator_synthesis_prompt(
    round_number: int,
    all_arguments_text: str,
    survivor_ids: list[str],
) -> str:
    """Prompt for moderator to synthesize a debate round."""
    return f"""## Synthesize Debate Round {round_number}

Below are all agents' arguments and votes for this round.

Your tasks:
1. Tally YES/NO votes for each idea (3+ NO = eliminated)
2. Flag any data conflicts between agents
3. Summarize key arguments and new evidence
4. Identify which ideas are strongest/weakest going forward
5. If fewer than 3 ideas remain, declare finalists

Use the submit_synthesis tool.

Current survivor IDs: {', '.join(survivor_ids)}

{all_arguments_text}"""


def get_synthesis_tool_schema() -> dict:
    """Tool schema for moderator round synthesis."""
    return {
        "name": "submit_synthesis",
        "description": "Submit the round synthesis including eliminations.",
        "input_schema": {
            "type": "object",
            "required": ["summary", "eliminated_ids", "surviving_ids"],
            "properties": {
                "summary": {"type": "string"},
                "eliminated_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "surviving_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "data_conflicts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "idea_id": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                },
                "declare_finalists": {"type": "boolean", "default": False},
            },
        },
    }
