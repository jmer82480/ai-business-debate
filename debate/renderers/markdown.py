"""State → markdown file renderer. All output files are generated from state."""

from __future__ import annotations

from pathlib import Path

from debate.config import DebateConfig
from debate.context import compress_idea
from debate.schemas.ideas import Idea
from debate.schemas.scorecard import Scorecard
from debate.schemas.state import DebateState
from debate.schemas.verdict import FinalVerdict


class MarkdownRenderer:
    """Renders all output/*.md files from DebateState."""

    def __init__(self, config: DebateConfig) -> None:
        self._output = Path(config.output_dir)

    def render_all(self, state: DebateState) -> list[str]:
        """Render all applicable files. Returns list of paths written."""
        written: list[str] = []

        # Phase 1
        for role, ideas in state.phase1_ideas.items():
            path = self._render_phase1(role, ideas)
            written.append(str(path))

        # Phase 2
        if state.merged_pool:
            written.append(str(self._render_merged_pool(state)))
        if state.survivors:
            written.append(str(self._render_survivors(state)))

        # Phase 3
        for rnd in state.debate_rounds:
            written.append(str(self._render_debate_round(rnd.round_number, state)))

        # Phase 4
        for idea_id, sc in state.scorecards.items():
            written.append(str(self._render_scorecard(sc)))

        # Phase 5
        if state.verdict:
            written.append(str(self._render_verdict(state.verdict)))
            written.append(str(self._render_final_plan(state)))

        return written

    def _ensure_dir(self, subdir: str) -> Path:
        path = self._output / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _render_phase1(self, role: str, ideas: list[Idea]) -> Path:
        d = self._ensure_dir("phase1")
        path = d / f"{role}-ideas.md"

        lines = [f"# {role.replace('_', ' ').title()} — Phase 1 Ideas\n"]
        for i, idea in enumerate(ideas, 1):
            lines.append(f"## {i}. {idea.name}\n")
            lines.append(f"**ID:** {idea.idea_id}\n")
            lines.append(f"{idea.description}\n")
            lines.append(f"**Startup Cost:** ${idea.startup_cost_total:.2f}")
            if idea.startup_cost_items:
                for item in idea.startup_cost_items:
                    lines.append(f"  - {item.get('item', '?')}: ${item.get('cost_usd', 0):.2f}")
            lines.append(f"\n**Autonomy:** Composite {idea.autonomy.composite:.0f}")
            lines.append(f"  - Acquisition: {idea.autonomy.acquisition}")
            lines.append(f"  - Fulfillment: {idea.autonomy.fulfillment}")
            lines.append(f"  - Support: {idea.autonomy.support}")
            lines.append(f"  - QA: {idea.autonomy.qa}")
            lines.append(f"\n**Revenue:** 90d: {idea.revenue.day_90} | 12m: {idea.revenue.month_12} | 3yr: {idea.revenue.year_3_ceiling}")
            lines.append(f"\n**Acquisition Path:**")
            lines.append(f"  - First 10: {idea.acquisition_path.first_10}")
            lines.append(f"  - First 100: {idea.acquisition_path.first_100}")
            lines.append(f"  - First 1000: {idea.acquisition_path.first_1000}")
            lines.append(f"\n**Moat:** {idea.moat}")
            lines.append(f"**Platform Risk:** {idea.platform_risk}")
            lines.append(f"**Key Risk:** {idea.key_risk}")
            lines.append(f"**Why Now:** {idea.why_now}\n")

        path.write_text("\n".join(lines))
        return path

    def _render_merged_pool(self, state: DebateState) -> Path:
        d = self._ensure_dir("phase2")
        path = d / "merged-pool.md"

        lines = ["# Merged Idea Pool — Phase 2\n"]
        for i, idea in enumerate(state.merged_pool, 1):
            status = "SURVIVOR" if idea.idea_id in state.survivors else "ELIMINATED"
            lines.append(f"## {i}. {idea.name} [{status}]\n")
            lines.append(f"**ID:** {idea.idea_id} | **Proposed by:** {', '.join(idea.proposed_by)}")
            lines.append(f"\n{compress_idea(idea)}\n")

        path.write_text("\n".join(lines))
        return path

    def _render_survivors(self, state: DebateState) -> Path:
        d = self._ensure_dir("phase2")
        path = d / "survivors.md"

        survivors = [i for i in state.merged_pool if i.idea_id in state.survivors]
        lines = [f"# Phase 2 Survivors ({len(survivors)} ideas)\n"]
        for i, idea in enumerate(survivors, 1):
            lines.append(f"{i}. **{idea.name}** ({idea.idea_id}) — Autonomy: {idea.autonomy.composite:.0f}, Cost: ${idea.startup_cost_total:.0f}")

        if state.phase2_votes:
            lines.append("\n## Vote Details\n")
            for vote in state.phase2_votes.votes:
                yn = "YES" if vote.vote else "NO"
                lines.append(f"- [{vote.role}] {vote.idea_id}: {yn} — {vote.justification}")

        path.write_text("\n".join(lines))
        return path

    def _render_debate_round(self, round_number: int, state: DebateState) -> Path:
        d = self._ensure_dir("phase3")
        path = d / f"round-{round_number}.md"

        rnd = next((r for r in state.debate_rounds if r.round_number == round_number), None)
        if not rnd:
            path.write_text(f"# Round {round_number}\n\nNo data.")
            return path

        lines = [f"# Debate Round {round_number}\n"]

        if rnd.moderator_summary:
            lines.append(f"## Moderator Summary\n\n{rnd.moderator_summary}\n")

        for arg in rnd.arguments:
            vote_str = ""
            if arg.vote is not None:
                vote_str = " | Vote: YES" if arg.vote else " | Vote: NO"
            lines.append(f"### [{arg.role}] on {arg.idea_id} ({arg.position}){vote_str}\n")
            lines.append(arg.argument)
            for fs in arg.failure_scenarios:
                lines.append(f"\n  - **Failure scenario:** {fs.scenario}")
                lines.append(f"    Evidence: {fs.evidence}")
            lines.append("")

        if rnd.eliminated_idea_ids:
            lines.append(f"\n**Eliminated:** {', '.join(rnd.eliminated_idea_ids)}")
        if rnd.surviving_idea_ids:
            lines.append(f"**Surviving:** {', '.join(rnd.surviving_idea_ids)}")

        path.write_text("\n".join(lines))
        return path

    def _render_scorecard(self, sc: Scorecard) -> Path:
        d = self._ensure_dir("phase4")
        slug = sc.idea_id.split("-")[0] if "-" in sc.idea_id else sc.idea_id
        path = d / f"scorecard-{slug}.md"

        lines = [f"# Scorecard: {sc.idea_name}\n"]
        lines.append(f"**ID:** {sc.idea_id}\n")
        lines.append("| Dimension | Score | Evidence/Notes |")
        lines.append("|---|---|---|")
        lines.append(f"| AI Autonomy — Acquisition | {sc.autonomy.acquisition} | |")
        lines.append(f"| AI Autonomy — Fulfillment | {sc.autonomy.fulfillment} | |")
        lines.append(f"| AI Autonomy — Support | {sc.autonomy.support} | |")
        lines.append(f"| AI Autonomy — QA | {sc.autonomy.qa} | |")
        lines.append(f"| **Autonomy Composite** | **{sc.autonomy.composite:.0f}** | Weighted: Acq 35%, Ful 30%, Sup 20%, QA 15% |")
        lines.append(f"| Growth Ceiling (3-year) | {sc.growth_ceiling_3yr} | |")
        lines.append(f"| Startup Cost | ${sc.startup_cost:.0f} | |")
        lines.append(f"| Time to First Dollar | {sc.time_to_first_dollar} | |")
        lines.append(f"| Defensibility / Moat | {sc.defensibility.value} | |")
        lines.append(f"| Platform Risk | {sc.platform_risk.value} | |")
        lines.append(f"| Hidden Human Labor Risk | {sc.hidden_human_labor_risk.value} | |")
        wtp = "; ".join(sc.willingness_to_pay_evidence[:5])
        lines.append(f"| Willingness to Pay Evidence | {wtp} | |")
        lines.append(f"| **Overall Confidence** | **{sc.overall_confidence.value}** | |")

        if sc.deep_dive_summary:
            lines.append(f"\n## Deep Dive Summary\n\n{sc.deep_dive_summary}")
        if sc.launch_plan_90day:
            lines.append(f"\n## 90-Day Launch Plan\n\n{sc.launch_plan_90day}")
        if sc.automation_architecture:
            lines.append(f"\n## Automation Architecture\n\n{sc.automation_architecture}")
        if sc.acquisition_system:
            lines.append(f"\n## Customer Acquisition System\n\n{sc.acquisition_system}")
        if sc.kill_criteria:
            lines.append(f"\n## Kill Criteria\n\n{sc.kill_criteria}")
        if sc.devils_advocate_objections:
            lines.append("\n## Devil's Advocate Objections\n")
            for obj in sc.devils_advocate_objections:
                lines.append(f"- {obj}")

        path.write_text("\n".join(lines))
        return path

    def _render_verdict(self, verdict: FinalVerdict) -> Path:
        self._output.mkdir(parents=True, exist_ok=True)
        path = self._output / "verdict.md"

        lines = ["# Final Verdict\n"]

        # Ranked table
        lines.append("## Final Ranked Table\n")
        lines.append("| # | Idea | Autonomy (Acq/Ful/Sup/QA) | Composite | Growth Ceiling | Cost | Time to $1 | Defensibility | Platform Risk | Hidden Labor | WTP | Confidence | Finish |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for f in sorted(verdict.ranked_table, key=lambda x: x.overall_finish):
            lines.append(
                f"| {f.overall_finish} | {f.idea_name} | "
                f"{f.autonomy_acquisition}/{f.autonomy_fulfillment}/{f.autonomy_support}/{f.autonomy_qa} | "
                f"{f.autonomy_composite:.0f} | {f.growth_ceiling} | ${f.startup_cost:.0f} | "
                f"{f.time_to_first_dollar} | {f.defensibility} | {f.platform_risk} | "
                f"{f.hidden_human_labor_risk} | {f.willingness_to_pay} | "
                f"{f.overall_confidence} | {f.overall_finish} |"
            )

        lines.append(f"\n## Winner\n\n{verdict.winner_narrative}")
        lines.append(f"\n## Runner-Up\n\n{verdict.runner_up_narrative}")

        lines.append("\n## Agent Positions\n")
        for pos in verdict.agent_positions:
            lines.append(f"### {pos.role}")
            lines.append(f"**Voted for:** {pos.voted_for_idea_id}")
            lines.append(f"{pos.justification}")
            if pos.remaining_concerns:
                lines.append(f"**Remaining concerns:** {pos.remaining_concerns}")
            lines.append("")

        lines.append(f"\n## Devil's Advocate Remaining Concerns\n\n{verdict.devils_advocate_remaining_concerns}")
        lines.append(f"\n## Group Confidence: **{verdict.group_confidence.value}**")

        path.write_text("\n".join(lines))
        return path

    def _render_final_plan(self, state: DebateState) -> Path:
        self._output.mkdir(parents=True, exist_ok=True)
        path = self._output / "final-plan.md"

        if not state.verdict:
            path.write_text("# Final Plan\n\nNo verdict reached.")
            return path

        winner_id = state.verdict.winner_idea_id
        sc = state.scorecards.get(winner_id)
        idea = state.get_idea_by_id(winner_id)

        lines = ["# 90-Day Launch Plan\n"]

        if idea:
            lines.append(f"## {idea.name}\n")
            lines.append(f"{idea.description}\n")

        if sc:
            lines.append(f"## Startup Budget: ${sc.startup_cost:.0f}\n")
            if sc.startup_cost_items:
                lines.append("| Item | Cost |")
                lines.append("|---|---|")
                for item in sc.startup_cost_items:
                    lines.append(f"| {item.get('item', '?')} | ${item.get('cost_usd', 0):.2f} |")

            if sc.launch_plan_90day:
                lines.append(f"\n## Week-by-Week Plan\n\n{sc.launch_plan_90day}")
            if sc.acquisition_system:
                lines.append(f"\n## Customer Acquisition System\n\n{sc.acquisition_system}")
            if sc.automation_architecture:
                lines.append(f"\n## Automation Architecture\n\n{sc.automation_architecture}")
            if sc.kill_criteria:
                lines.append(f"\n## Kill Criteria\n\n{sc.kill_criteria}")
            if sc.why_now:
                lines.append(f"\n## Why Now\n\n{sc.why_now}")
            if sc.proof_of_wtp:
                lines.append(f"\n## Proof of Willingness to Pay\n\n{sc.proof_of_wtp}")

        path.write_text("\n".join(lines))
        return path
