"""Phase 4 — Deep Dive prompts."""


def get_deep_dive_prompt(idea_name: str, idea_context: str, debate_context: str) -> str:
    """Prompt for a comprehensive deep dive on a finalist."""
    return f"""## Deep Dive: {idea_name}

Produce a comprehensive analysis of this finalist idea. Use web search extensively for real pricing, competitor data, and market validation.

### Idea Context
{idea_context}

### Debate Highlights
{debate_context}

You MUST cover ALL of the following using the submit_deep_dive tool:

1. **Line-item startup cost breakdown** — web-searched real prices for every tool/service
2. **Week-by-week 90-day launch plan** — specific milestones, not vague phases
3. **Automation architecture** — what AI does vs. human, by month, scored across acquisition/fulfillment/support/QA
4. **Customer acquisition system** — how customers acquired at 0-10, 10-100, 100-1000; automated vs. manual; cost per acquisition
5. **Revenue model** — 90-day, 12-month, 3-year with explicit assumptions
6. **Moat analysis** — what compounds over time
7. **Proof of willingness to pay** — NAME specific adjacent products/services/budget items buyers already spend on (use web search)
8. **Platform/compliance risk** — single points of failure, API dependencies, regulatory
9. **Kill criteria** — specific metrics and deadlines that signal "stop"
10. **Why now** — what specific recent change enables this"""


def get_deep_dive_tool_schema() -> dict:
    """Tool schema for deep dive submissions."""
    return {
        "name": "submit_deep_dive",
        "description": "Submit the comprehensive deep dive analysis.",
        "input_schema": {
            "type": "object",
            "required": [
                "idea_id", "startup_cost_items", "startup_cost_total",
                "launch_plan_90day", "automation_architecture",
                "acquisition_system", "revenue_model",
                "moat_analysis", "proof_of_wtp",
                "platform_risk", "kill_criteria", "why_now",
                "autonomy",
            ],
            "properties": {
                "idea_id": {"type": "string"},
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
                "launch_plan_90day": {"type": "string"},
                "automation_architecture": {"type": "string"},
                "acquisition_system": {"type": "string"},
                "revenue_model": {
                    "type": "object",
                    "properties": {
                        "day_90": {"type": "string"},
                        "month_12": {"type": "string"},
                        "year_3_ceiling": {"type": "string"},
                    },
                    "required": ["day_90", "month_12", "year_3_ceiling"],
                },
                "moat_analysis": {"type": "string"},
                "proof_of_wtp": {"type": "string"},
                "platform_risk": {"type": "string"},
                "kill_criteria": {"type": "string"},
                "why_now": {"type": "string"},
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
                "willingness_to_pay_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "growth_ceiling_3yr": {"type": "string"},
                "time_to_first_dollar": {"type": "string"},
                "defensibility": {"type": "string", "enum": ["low", "medium", "high"]},
                "hidden_human_labor_risk": {"type": "string", "enum": ["low", "medium", "high"]},
                "overall_confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            },
        },
    }


def get_da_stress_test_prompt(idea_name: str, deep_dive_text: str) -> str:
    """Devil's Advocate final stress test for a finalist."""
    return f"""## Devil's Advocate Final Stress Test: {idea_name}

This is your FINAL chance to kill this idea. Below is the deep dive.

{deep_dive_text}

Using the submit_stress_test tool, present:
1. Your 2 strongest remaining failure scenarios with evidence
2. The hidden human labor you see that others are ignoring
3. The most likely reason this business dies within 12 months
4. What the autonomy score should ACTUALLY be (lower it if the deep dive is optimistic)

Use web search to find evidence for your objections."""


def get_stress_test_tool_schema() -> dict:
    """Tool schema for DA stress test."""
    return {
        "name": "submit_stress_test",
        "description": "Submit Devil's Advocate stress test results.",
        "input_schema": {
            "type": "object",
            "required": ["idea_id", "failure_scenarios", "hidden_human_labor", "likely_death_reason"],
            "properties": {
                "idea_id": {"type": "string"},
                "failure_scenarios": {
                    "type": "array",
                    "minItems": 2,
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
                "hidden_human_labor": {"type": "string"},
                "likely_death_reason": {"type": "string"},
                "revised_autonomy": {
                    "type": "object",
                    "properties": {
                        "acquisition": {"type": "integer"},
                        "fulfillment": {"type": "integer"},
                        "support": {"type": "integer"},
                        "qa": {"type": "integer"},
                    },
                },
                "overall_objections": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    }
