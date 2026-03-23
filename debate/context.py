"""Context compression — budget-aware prompt context generation."""

from __future__ import annotations

from debate.schemas.ideas import Idea
from debate.schemas.scorecard import Scorecard
from debate.schemas.state import DebateState


# Rough token estimate: ~4 chars per token
CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def _truncate_to_budget(text: str, budget_tokens: int) -> str:
    max_chars = budget_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [CONTEXT TRUNCATED TO FIT BUDGET]"


def compress_idea(idea: Idea) -> str:
    """One-paragraph summary of an idea for compact context."""
    return (
        f"**{idea.name}** (ID: {idea.idea_id}): {idea.description} | "
        f"Cost: ${idea.startup_cost_total:.0f} | "
        f"Autonomy: {idea.autonomy.composite:.0f} "
        f"(Acq:{idea.autonomy.acquisition} Ful:{idea.autonomy.fulfillment} "
        f"Sup:{idea.autonomy.support} QA:{idea.autonomy.qa}) | "
        f"Key risk: {idea.key_risk}"
    )


def compress_ideas_list(ideas: list[Idea], budget_tokens: int = 8000) -> str:
    """Compact summary of a list of ideas within token budget."""
    lines = [compress_idea(idea) for idea in ideas]
    text = "\n".join(f"- {line}" for line in lines)
    return _truncate_to_budget(text, budget_tokens)


def compress_merged_pool(state: DebateState, budget_tokens: int = 8000) -> str:
    """Compact merged pool for voting context."""
    lines: list[str] = []
    for i, idea in enumerate(state.merged_pool, 1):
        lines.append(f"{i}. {compress_idea(idea)}")
    text = "\n".join(lines)
    return _truncate_to_budget(text, budget_tokens)


def compress_survivors(state: DebateState, budget_tokens: int = 6000) -> str:
    """Compact list of surviving ideas for debate context."""
    survivors = [
        idea for idea in state.merged_pool if idea.idea_id in state.survivors
    ]
    return compress_ideas_list(survivors, budget_tokens)


def compress_debate_history(state: DebateState, budget_tokens: int = 4000) -> str:
    """Last round summary only — not full transcript."""
    if not state.debate_rounds:
        return "No debate rounds yet."

    last_round = state.debate_rounds[-1]
    lines = [f"## Debate Round {last_round.round_number} Summary"]

    if last_round.moderator_summary:
        lines.append(last_round.moderator_summary)

    if last_round.eliminated_idea_ids:
        lines.append(f"\nEliminated: {', '.join(last_round.eliminated_idea_ids)}")
    if last_round.surviving_idea_ids:
        lines.append(f"Surviving: {', '.join(last_round.surviving_idea_ids)}")

    text = "\n".join(lines)
    return _truncate_to_budget(text, budget_tokens)


def compress_scorecard(scorecard: Scorecard) -> str:
    """Compact scorecard for convergence context."""
    return (
        f"**{scorecard.idea_name}** (ID: {scorecard.idea_id})\n"
        f"  Autonomy Composite: {scorecard.autonomy.composite:.0f} "
        f"(Acq:{scorecard.autonomy.acquisition} Ful:{scorecard.autonomy.fulfillment} "
        f"Sup:{scorecard.autonomy.support} QA:{scorecard.autonomy.qa})\n"
        f"  Growth Ceiling: {scorecard.growth_ceiling_3yr}\n"
        f"  Startup Cost: ${scorecard.startup_cost:.0f}\n"
        f"  Time to $1: {scorecard.time_to_first_dollar}\n"
        f"  Defensibility: {scorecard.defensibility} | "
        f"Platform Risk: {scorecard.platform_risk} | "
        f"Hidden Human Labor: {scorecard.hidden_human_labor_risk}\n"
        f"  WTP Evidence: {', '.join(scorecard.willingness_to_pay_evidence[:3])}\n"
        f"  Confidence: {scorecard.overall_confidence}\n"
        f"  DA Objections: {'; '.join(scorecard.devils_advocate_objections[:2])}"
    )


def compress_all_scorecards(state: DebateState, budget_tokens: int = 6000) -> str:
    """Compact all scorecards for final voting."""
    lines = [compress_scorecard(sc) for sc in state.scorecards.values()]
    text = "\n\n".join(lines)
    return _truncate_to_budget(text, budget_tokens)
