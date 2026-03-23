"""Main orchestration loop — drives all 5 phases with validation, checkpointing, and rendering."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from rich.console import Console

from debate.config import DebateConfig, estimate_cost
from debate.context import (
    compress_all_scorecards,
    compress_debate_history,
    compress_idea,
    compress_merged_pool,
    compress_survivors,
)
from debate.llm.client import LLMClient
from debate.renderers.markdown import MarkdownRenderer
from debate.roles import ROLE_REGISTRY
from debate.roles.base import BadOutputError, ValidationFailure
from debate.roles.moderator import Moderator
from debate.schemas.common import ConfidenceLevel, RiskLevel
from debate.schemas.debate import DebateRound
from debate.schemas.ideas import AutonomyScores
from debate.schemas.scorecard import Scorecard
from debate.schemas.state import DebateState, Phase, RunMeta, StepStatus
from debate.schemas.verdict import AgentPosition, FinalVerdict, RankedFinalist
from debate.schemas.votes import Vote, VoteRound
from debate.storage.checkpoint import CheckpointStore
from debate.validators.gates import passes_gates, validate_gate_criteria
from debate.validators.phase import PhaseTransitionError, validate_phase_transition

logger = logging.getLogger(__name__)
console = Console()

DEBATER_ROLES = ["bootstrapper", "market_analyst", "automation_architect", "devils_advocate"]


class Orchestrator:
    """Drives the full debate workflow: phases 1-5 with checkpointing."""

    def __init__(
        self,
        client: LLMClient,
        config: DebateConfig,
        run_id: str | None = None,
    ) -> None:
        self._client = client
        self._config = config
        self._run_id = run_id or uuid.uuid4().hex[:12]
        self._store = CheckpointStore(config, self._run_id)
        self._renderer = MarkdownRenderer(config)
        self._state = DebateState(meta=RunMeta(run_id=self._run_id))

        # Instantiate all role adapters
        self._roles = {
            name: cls(client, config) for name, cls in ROLE_REGISTRY.items()
        }
        self._moderator: Moderator = self._roles["moderator"]  # type: ignore[assignment]

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def state(self) -> DebateState:
        return self._state

    def resume(self) -> None:
        """Resume from a saved checkpoint."""
        self._state = self._store.load()
        console.print(f"[bold green]Resumed run {self._run_id} at {self._state.current_phase.value}[/]")

    def run(self) -> None:
        """Execute the full debate from current state to completion."""
        console.print(f"[bold]Starting debate run {self._run_id}[/]\n")

        phases = [
            (Phase.PHASE_1_IDEATION, self._run_phase1),
            (Phase.PHASE_2_MERGE_VOTE, self._run_phase2),
            (Phase.PHASE_3_DEBATE, self._run_phase3),
            (Phase.PHASE_4_DEEP_DIVE, self._run_phase4),
            (Phase.PHASE_5_CONVERGENCE, self._run_phase5),
        ]

        for phase, fn in phases:
            if self._state.current_phase.value > phase.value and phase != Phase.COMPLETED:
                # Skip already-completed phases on resume
                if self._is_phase_done(phase):
                    console.print(f"[dim]Skipping completed {phase.value}[/]")
                    continue

            console.print(f"\n[bold blue]{'='*60}[/]")
            console.print(f"[bold blue]{phase.value.upper().replace('_', ' ')}[/]")
            console.print(f"[bold blue]{'='*60}[/]\n")

            self._state.current_phase = phase
            fn()
            self._renderer.render_all(self._state)
            self._checkpoint()

        self._state.current_phase = Phase.COMPLETED
        self._renderer.render_all(self._state)
        self._checkpoint()

        console.print(f"\n[bold green]Debate complete! Run ID: {self._run_id}[/]")
        console.print(f"[bold green]Total cost: ${self._state.meta.total_estimated_cost_usd:.4f}[/]")
        console.print(f"Output files in: {self._config.output_dir}/")

    def _is_phase_done(self, phase: Phase) -> bool:
        """Check if all steps for a phase are completed."""
        prefix = phase.value
        return any(
            k.startswith(prefix) and v.status == StepStatus.COMPLETED
            for k, v in self._state.steps.items()
        )

    def _checkpoint(self) -> None:
        """Persist state atomically."""
        self._store.save(self._state)

    def _run_step(self, step_key: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute a step with status tracking, retry, and checkpointing."""
        step = self._state.get_step(step_key)

        if step.status == StepStatus.COMPLETED:
            console.print(f"  [dim]Skipping completed step: {step_key}[/]")
            return None

        for attempt in range(1, self._config.max_retries_per_step + 1):
            step.mark_running()
            self._checkpoint()

            try:
                console.print(f"  [yellow]Running: {step_key} (attempt {attempt})[/]")
                result = fn(*args, **kwargs)

                # Extract cost info from the debug JSON string
                tokens_in = 0
                tokens_out = 0
                model_used = ""
                if isinstance(result, tuple) and len(result) == 2:
                    _, debug = result
                    if isinstance(debug, str):
                        self._store.save_debug_artifact(step_key, debug)
                        try:
                            debug_data = json.loads(debug)
                            tokens_in = debug_data.get("tokens_in", 0)
                            tokens_out = debug_data.get("tokens_out", 0)
                            model_used = debug_data.get("model", "")
                        except (json.JSONDecodeError, TypeError):
                            pass

                cost = estimate_cost(
                    model_used or self._config.model_default, tokens_in, tokens_out
                )
                step.mark_completed(
                    model=model_used,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost,
                )
                self._state.accumulate_cost(tokens_in, tokens_out, cost)
                self._checkpoint()

                if cost > 0:
                    console.print(
                        f"  [green]Completed: {step_key} "
                        f"(tokens: {tokens_in}+{tokens_out}, cost: ${cost:.4f})[/]"
                    )
                else:
                    console.print(f"  [green]Completed: {step_key}[/]")
                return result

            except ValidationFailure as e:
                logger.warning("Validation failure in %s: %s", step_key, e)
                step.mark_failed(str(e))
                if attempt >= self._config.max_retries_per_step:
                    raise
                console.print(f"  [red]Validation error, retrying: {e}[/]")

            except BadOutputError as e:
                logger.warning("Bad output in %s: %s", step_key, e)
                step.mark_failed(str(e))
                if attempt >= self._config.max_retries_per_step:
                    raise
                console.print(f"  [red]Bad output, retrying with correction: {e}[/]")

            except Exception as e:
                logger.error("Unexpected error in %s: %s", step_key, e)
                step.mark_failed(str(e))
                raise

    # ---- Phase 1: Independent Ideation ----

    def _run_phase1(self) -> None:
        """Each role independently generates ideas."""
        for role_name in DEBATER_ROLES:
            step_key = f"phase_1_ideation.{role_name}"
            if self._state.is_step_completed(step_key):
                continue

            role = self._roles[role_name]
            result = self._run_step(step_key, role.generate_ideas)
            if result is not None:
                ideas, _ = result
                self._state.phase1_ideas[role_name] = ideas
                console.print(f"  [green]{role_name}: {len(ideas)} ideas[/]")

    # ---- Phase 2: Merge & Vote ----

    def _run_phase2(self) -> None:
        """Moderator merges, then all roles vote."""
        # Validate we can enter Phase 2
        try:
            validate_phase_transition(self._state, Phase.PHASE_2_MERGE_VOTE)
        except PhaseTransitionError as e:
            console.print(f"[red]Cannot enter Phase 2: {e}[/]")
            raise

        # Step 2a: Moderator merge
        step_key = "phase_2_merge_vote.merge"
        if not self._state.is_step_completed(step_key):
            all_ideas_text = self._format_all_phase1_ideas()
            result = self._run_step(step_key, self._moderator.merge_ideas, all_ideas_text)
            if result is not None:
                data, _ = result
                merged = Moderator.parse_merged_ideas(data)
                # Gate-check each idea
                for idea in merged:
                    failures = validate_gate_criteria(idea)
                    if failures:
                        console.print(f"  [red]Gate fail: {idea.name} — {[f.reason for f in failures]}[/]")
                self._state.merged_pool = [i for i in merged if passes_gates(i)]
                console.print(f"  [green]Merged pool: {len(self._state.merged_pool)} ideas[/]")

        # Step 2b: Each role votes (persisted per-role for resume safety)
        pool_text = compress_merged_pool(self._state)
        idea_ids = [i.idea_id for i in self._state.merged_pool]

        for role_name in DEBATER_ROLES:
            step_key = f"phase_2_merge_vote.vote_{role_name}"
            if self._state.is_step_completed(step_key):
                continue

            role = self._roles[role_name]
            result = self._run_step(step_key, role.vote, pool_text, idea_ids)
            if result is not None:
                votes, _ = result
                # Persist this role's votes to state immediately
                self._state.phase2_role_votes[role_name] = [
                    v.model_dump(mode="json") for v in votes
                ]
                self._checkpoint()

        # Step 2c: Tally — reconstruct all votes from persisted per-role data
        all_votes: list[Vote] = []
        for role_name in DEBATER_ROLES:
            for v_data in self._state.phase2_role_votes.get(role_name, []):
                all_votes.append(Vote.model_validate(v_data))

        if all_votes:
            vote_round = VoteRound(phase=2, round_number=1, votes=all_votes)
            self._state.phase2_votes = vote_round

            survivors: list[str] = []
            for idea in self._state.merged_pool:
                yes, no = vote_round.tally(idea.idea_id)
                if yes >= 3:
                    survivors.append(idea.idea_id)
                    console.print(f"  [green]SURVIVES: {idea.name} ({yes}Y/{no}N)[/]")
                else:
                    console.print(f"  [red]ELIMINATED: {idea.name} ({yes}Y/{no}N)[/]")

            self._state.survivors = survivors
            console.print(f"\n  [bold]{len(survivors)} survivors advance to Phase 3[/]")

    # ---- Phase 3: Debate Rounds ----

    def _run_phase3(self) -> None:
        """Iterative debate rounds until 2-3 finalists remain."""
        try:
            validate_phase_transition(self._state, Phase.PHASE_3_DEBATE)
        except PhaseTransitionError as e:
            console.print(f"[red]Cannot enter Phase 3: {e}[/]")
            raise

        current_survivors = list(self._state.survivors)

        for round_num in range(1, self._config.max_phase3_rounds + 1):
            if len(current_survivors) <= 3:
                self._state.finalists = current_survivors
                console.print(f"\n  [bold green]{len(current_survivors)} finalists selected![/]")
                break

            console.print(f"\n  [bold]--- Debate Round {round_num} ({len(current_survivors)} ideas) ---[/]")

            # All roles debate
            round_arguments = []
            survivors_text = compress_survivors(self._state)
            prior_text = compress_debate_history(self._state)

            for role_name in DEBATER_ROLES:
                step_key = f"phase_3_debate.round{round_num}_{role_name}"
                if self._state.is_step_completed(step_key):
                    continue

                role = self._roles[role_name]
                result = self._run_step(
                    step_key, role.debate, survivors_text, prior_text, round_num
                )
                if result is not None:
                    args, _ = result
                    round_arguments.extend(args)

            # Moderator synthesis
            synth_key = f"phase_3_debate.round{round_num}_synthesis"
            if not self._state.is_step_completed(synth_key):
                args_text = self._format_debate_arguments(round_arguments)
                result = self._run_step(
                    synth_key,
                    self._moderator.synthesize_round,
                    round_num,
                    args_text,
                    current_survivors,
                )
                if result is not None:
                    synth_data, _ = result
                    debate_round = DebateRound(
                        round_number=round_num,
                        arguments=round_arguments,
                        moderator_summary=synth_data.get("summary", ""),
                        eliminated_idea_ids=synth_data.get("eliminated_ids", []),
                        surviving_idea_ids=synth_data.get("surviving_ids", []),
                    )
                    self._state.debate_rounds.append(debate_round)

                    # Update survivors
                    eliminated = set(synth_data.get("eliminated_ids", []))
                    current_survivors = [s for s in current_survivors if s not in eliminated]
                    self._state.survivors = current_survivors

                    if synth_data.get("declare_finalists"):
                        self._state.finalists = current_survivors
                        console.print(f"\n  [bold green]Moderator declared finalists![/]")
                        break
        else:
            # Hit max rounds — force top 3
            console.print(f"\n  [yellow]Max rounds reached. Forcing top 3 into Phase 4.[/]")
            self._state.finalists = current_survivors[:3]

    # ---- Phase 4: Deep Dive ----

    def _run_phase4(self) -> None:
        """Deep dive + scorecard for each finalist."""
        try:
            validate_phase_transition(self._state, Phase.PHASE_4_DEEP_DIVE)
        except PhaseTransitionError as e:
            console.print(f"[red]Cannot enter Phase 4: {e}[/]")
            raise

        for idea_id in self._state.finalists:
            idea = self._state.get_idea_by_id(idea_id)
            if not idea:
                console.print(f"  [red]Finalist {idea_id} not found in merged pool[/]")
                continue

            idea_context = compress_idea(idea)
            debate_context = compress_debate_history(self._state)

            # Deep dive
            dd_key = f"phase_4_deep_dive.{idea_id}"
            dd_data: dict[str, Any] | None = None
            if not self._state.is_step_completed(dd_key):
                result = self._run_step(
                    dd_key,
                    self._moderator.deep_dive,
                    idea.name,
                    idea_id,
                    idea_context,
                    debate_context,
                )
                if result is not None:
                    dd_data, _ = result

            # DA stress test
            da_key = f"phase_4_deep_dive.da_stress_{idea_id}"
            da_data: dict[str, Any] | None = None
            if not self._state.is_step_completed(da_key):
                da_role = self._roles["devils_advocate"]
                dd_text = json.dumps(dd_data, indent=2) if dd_data else "No deep dive data."
                result = self._run_step(
                    da_key, da_role.stress_test, idea.name, idea_id, dd_text
                )
                if result is not None:
                    da_data, _ = result

            # Build scorecard
            if dd_data:
                sc = self._build_scorecard(idea, dd_data, da_data)
                self._state.scorecards[idea_id] = sc
                console.print(f"  [green]Scorecard: {idea.name} — Autonomy: {sc.autonomy.composite:.0f}[/]")

    # ---- Phase 5: Convergence ----

    def _run_phase5(self) -> None:
        """Final votes and verdict."""
        try:
            validate_phase_transition(self._state, Phase.PHASE_5_CONVERGENCE)
        except PhaseTransitionError as e:
            console.print(f"[red]Cannot enter Phase 5: {e}[/]")
            raise

        scorecards_text = compress_all_scorecards(self._state)

        # Each role votes
        all_positions: list[AgentPosition] = []
        for role_name in DEBATER_ROLES:
            step_key = f"phase_5_convergence.vote_{role_name}"
            if self._state.is_step_completed(step_key):
                continue

            role = self._roles[role_name]
            result = self._run_step(step_key, role.final_vote, scorecards_text)
            if result is not None:
                data, _ = result
                all_positions.append(
                    AgentPosition(
                        role=role_name,
                        voted_for_idea_id=data["voted_for_idea_id"],
                        ranking=data.get("ranking", []),
                        justification=data["justification"],
                        remaining_concerns=data.get("remaining_concerns", ""),
                    )
                )

        self._state.final_votes = [p.model_dump() for p in all_positions]

        # Moderator writes verdict
        verdict_key = "phase_5_convergence.verdict"
        if not self._state.is_step_completed(verdict_key):
            votes_text = "\n".join(
                f"[{p.role}] voted for {p.voted_for_idea_id}: {p.justification}"
                for p in all_positions
            )
            result = self._run_step(
                verdict_key,
                self._moderator.write_verdict,
                votes_text,
                scorecards_text,
                self._state.finalists,
            )
            if result is not None:
                vdata, _ = result
                self._state.verdict = self._build_verdict(vdata, all_positions)
                console.print(f"\n  [bold green]Winner: {self._state.verdict.winner_idea_id}[/]")

    # ---- Helpers ----

    def _format_all_phase1_ideas(self) -> str:
        """Format all Phase 1 ideas for the moderator merge prompt."""
        sections: list[str] = []
        for role, ideas in self._state.phase1_ideas.items():
            lines = [f"--- {role.upper()} IDEAS ---"]
            for i, idea in enumerate(ideas, 1):
                lines.append(f"\n{i}. {idea.name}: {idea.description}")
                lines.append(f"   Cost: ${idea.startup_cost_total:.0f}")
                lines.append(
                    f"   Autonomy: Acq={idea.autonomy.acquisition} "
                    f"Ful={idea.autonomy.fulfillment} "
                    f"Sup={idea.autonomy.support} QA={idea.autonomy.qa} "
                    f"(Composite: {idea.autonomy.composite:.0f})"
                )
                lines.append(f"   Revenue 90d: {idea.revenue.day_90}")
                lines.append(f"   Revenue 12m: {idea.revenue.month_12}")
                lines.append(f"   Revenue 3yr: {idea.revenue.year_3_ceiling}")
                lines.append(f"   Acquisition: 10={idea.acquisition_path.first_10}")
                lines.append(f"   Moat: {idea.moat}")
                lines.append(f"   Platform risk: {idea.platform_risk}")
                lines.append(f"   Key risk: {idea.key_risk}")
                lines.append(f"   Why now: {idea.why_now}")
            sections.append("\n".join(lines))
        return "\n\n".join(sections)

    def _format_debate_arguments(self, arguments: list) -> str:
        """Format debate arguments for moderator synthesis."""
        lines: list[str] = []
        for arg in arguments:
            vote_str = "YES" if arg.vote else "NO" if arg.vote is not None else "ABSTAIN"
            lines.append(f"[{arg.role}] on {arg.idea_id} ({arg.position}, vote={vote_str}):")
            lines.append(f"  {arg.argument}")
            for fs in arg.failure_scenarios:
                lines.append(f"  FAILURE SCENARIO: {fs.scenario} — {fs.evidence}")
            lines.append("")
        return "\n".join(lines)

    def _build_scorecard(
        self, idea: Any, dd_data: dict[str, Any], da_data: dict[str, Any] | None
    ) -> Scorecard:
        """Build a Scorecard from deep dive + stress test data."""
        autonomy_raw = dd_data.get("autonomy", {})
        objections: list[str] = []
        if da_data:
            objections = da_data.get("overall_objections", [])
            for fs in da_data.get("failure_scenarios", []):
                objections.append(f"{fs.get('scenario', '')}: {fs.get('evidence', '')}")

        return Scorecard(
            idea_id=idea.idea_id,
            idea_name=idea.name,
            autonomy=AutonomyScores(
                acquisition=autonomy_raw.get("acquisition", idea.autonomy.acquisition),
                fulfillment=autonomy_raw.get("fulfillment", idea.autonomy.fulfillment),
                support=autonomy_raw.get("support", idea.autonomy.support),
                qa=autonomy_raw.get("qa", idea.autonomy.qa),
            ),
            growth_ceiling_3yr=dd_data.get("growth_ceiling_3yr", "Unknown"),
            startup_cost=dd_data.get("startup_cost_total", idea.startup_cost_total),
            startup_cost_items=dd_data.get("startup_cost_items", []),
            time_to_first_dollar=dd_data.get("time_to_first_dollar", "Unknown"),
            defensibility=RiskLevel(dd_data.get("defensibility", "medium")),
            platform_risk=RiskLevel(dd_data.get("platform_risk", idea.platform_risk if idea.platform_risk in ("low", "medium", "high") else "medium")),
            hidden_human_labor_risk=RiskLevel(dd_data.get("hidden_human_labor_risk", "medium")),
            willingness_to_pay_evidence=dd_data.get("willingness_to_pay_evidence", []),
            overall_confidence=ConfidenceLevel(dd_data.get("overall_confidence", "medium")),
            deep_dive_summary=dd_data.get("revenue_model", {}).get("year_3_ceiling", ""),
            launch_plan_90day=dd_data.get("launch_plan_90day", ""),
            automation_architecture=dd_data.get("automation_architecture", ""),
            acquisition_system=dd_data.get("acquisition_system", ""),
            kill_criteria=dd_data.get("kill_criteria", ""),
            why_now=dd_data.get("why_now", ""),
            proof_of_wtp=dd_data.get("proof_of_wtp", ""),
            devils_advocate_objections=objections,
        )

    def _build_verdict(
        self, vdata: dict[str, Any], positions: list[AgentPosition]
    ) -> FinalVerdict:
        """Build FinalVerdict from moderator output + agent positions."""
        ranked = []
        for entry in vdata.get("ranked_table", []):
            ranked.append(
                RankedFinalist(
                    idea_id=entry["idea_id"],
                    idea_name=entry["idea_name"],
                    autonomy_acquisition=entry.get("autonomy_acquisition", 0),
                    autonomy_fulfillment=entry.get("autonomy_fulfillment", 0),
                    autonomy_support=entry.get("autonomy_support", 0),
                    autonomy_qa=entry.get("autonomy_qa", 0),
                    autonomy_composite=entry.get("autonomy_composite", 0),
                    growth_ceiling=entry.get("growth_ceiling", "Unknown"),
                    startup_cost=entry.get("startup_cost", 0),
                    time_to_first_dollar=entry.get("time_to_first_dollar", "Unknown"),
                    defensibility=entry.get("defensibility", "medium"),
                    platform_risk=entry.get("platform_risk", "medium"),
                    hidden_human_labor_risk=entry.get("hidden_human_labor_risk", "medium"),
                    willingness_to_pay=entry.get("willingness_to_pay", ""),
                    overall_confidence=entry.get("overall_confidence", "medium"),
                    overall_finish=entry.get("overall_finish", 0),
                )
            )

        return FinalVerdict(
            ranked_table=ranked,
            winner_idea_id=vdata["winner_idea_id"],
            winner_narrative=vdata["winner_narrative"],
            runner_up_idea_id=vdata["runner_up_idea_id"],
            runner_up_narrative=vdata["runner_up_narrative"],
            agent_positions=positions,
            devils_advocate_remaining_concerns=vdata.get(
                "devils_advocate_remaining_concerns", ""
            ),
            group_confidence=ConfidenceLevel(vdata.get("group_confidence", "medium")),
        )
