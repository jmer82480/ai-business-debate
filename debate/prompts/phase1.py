"""Phase 1 — Independent Ideation prompts."""

IDEATION_PROMPT = """Research and propose 5-8 AI business ideas. Work INDEPENDENTLY — do not reference other agents' ideas.

For EACH idea, return structured data using the submit_ideas tool with these fields:
- name: Short descriptive name
- description: One-sentence description
- startup_cost_items: List of {{item, cost_usd, notes}} line items — use web search for real prices
- startup_cost_total: Sum of line items
- autonomy: {{acquisition (0-100), fulfillment (0-100), support (0-100), qa (0-100)}}
- revenue: {{day_90, month_12, year_3_ceiling}} — estimates with stated assumptions
- acquisition_path: {{first_10, first_100, first_1000}} — how customers find this at each scale
- moat: What stops someone copying this in a weekend
- platform_risk: Single points of failure (API dependencies, marketplace risk, regulatory)
- key_risk: The most likely way this dies
- why_now: What recent change (new tools, cost drops, market shifts, regulations) makes this viable today but not 2 years ago
- evidence: List of {{claim, source, date, key_assumption, confidence}} for your major claims

Use web search to verify: tool/service pricing, market sizes, competitor data, any claim about growth or demand. Label unsourced estimates as "UNSOURCED ESTIMATE."

Think creatively. Consider niches others might overlook. Every idea must pass the gates: cost < $500, autonomy > 70%, no manual outbound sales dependency."""


def get_phase1_tool_schema() -> dict:
    """Return the tool schema for submitting Phase 1 ideas."""
    return {
        "name": "submit_ideas",
        "description": "Submit your researched business ideas in structured format.",
        "input_schema": {
            "type": "object",
            "required": ["ideas"],
            "properties": {
                "ideas": {
                    "type": "array",
                    "minItems": 5,
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "required": [
                            "name", "description", "startup_cost_items",
                            "startup_cost_total", "autonomy", "revenue",
                            "acquisition_path", "moat", "platform_risk",
                            "key_risk", "why_now", "evidence",
                        ],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
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
                                    "acquisition": {"type": "integer", "minimum": 0, "maximum": 100},
                                    "fulfillment": {"type": "integer", "minimum": 0, "maximum": 100},
                                    "support": {"type": "integer", "minimum": 0, "maximum": 100},
                                    "qa": {"type": "integer", "minimum": 0, "maximum": 100},
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
                            "evidence": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "claim": {"type": "string"},
                                        "source": {"type": "string"},
                                        "date": {"type": "string"},
                                        "key_assumption": {"type": "string"},
                                        "confidence": {
                                            "type": "string",
                                            "enum": ["low", "medium", "high"],
                                        },
                                    },
                                    "required": ["claim", "source", "date", "key_assumption", "confidence"],
                                },
                            },
                        },
                    },
                },
            },
        },
    }
