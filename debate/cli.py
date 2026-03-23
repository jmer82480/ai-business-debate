"""CLI entry point — run, resume, status, render."""

from __future__ import annotations

import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from debate.config import DebateConfig
from debate.llm.anthropic import AnthropicClient
from debate.llm.fake import FakeLLMClient
from debate.llm.client import LLMResponse
from debate.orchestrator import Orchestrator
from debate.renderers.markdown import MarkdownRenderer
from debate.storage.checkpoint import CheckpointStore

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def main(verbose: bool) -> None:
    """AI Business Idea Debate — Orchestration Engine."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@main.command()
@click.option("--model", default="claude-sonnet-4-6", help="Default model")
@click.option("--deep-dive-model", default=None, help="Model for deep dives (defaults to --model)")
@click.option("--no-web-search", is_flag=True, help="Disable web search")
@click.option("--dry-run", is_flag=True, help="Use fake LLM client (no API calls)")
@click.option("--max-rounds", default=10, type=int, help="Max Phase 3 debate rounds")
@click.option("--output-dir", default="output", help="Output directory")
def run(
    model: str,
    deep_dive_model: str | None,
    no_web_search: bool,
    dry_run: bool,
    max_rounds: int,
    output_dir: str,
) -> None:
    """Start a new debate run."""
    config = DebateConfig(
        model_default=model,
        model_deep_dive=deep_dive_model or model,
        web_search_enabled=not no_web_search,
        max_phase3_rounds=max_rounds,
        output_dir=output_dir,
    )

    if dry_run:
        console.print("[yellow]DRY RUN — using fake LLM client[/]")
        client = _make_dry_run_client()
    else:
        try:
            client = AnthropicClient(config)
        except Exception as e:
            console.print(f"[red]Failed to initialize Anthropic client: {e}[/]")
            console.print("Set ANTHROPIC_API_KEY or check your configuration.")
            sys.exit(1)

    orchestrator = Orchestrator(client, config)
    console.print(f"Run ID: [bold]{orchestrator.run_id}[/]")

    try:
        orchestrator.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. State saved. Resume with:[/]")
        console.print(f"  debate resume --run-id {orchestrator.run_id}")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/]")
        console.print(f"Resume with: debate resume --run-id {orchestrator.run_id}")
        raise


@main.command()
@click.option("--run-id", required=True, help="Run ID to resume")
@click.option("--model", default="claude-sonnet-4-6", help="Default model")
@click.option("--dry-run", is_flag=True, help="Use fake LLM client")
@click.option("--output-dir", default="output", help="Output directory")
def resume(run_id: str, model: str, dry_run: bool, output_dir: str) -> None:
    """Resume a previous debate run from checkpoint."""
    config = DebateConfig(model_default=model, output_dir=output_dir)

    if dry_run:
        client = _make_dry_run_client()
    else:
        client = AnthropicClient(config)

    orchestrator = Orchestrator(client, config, run_id=run_id)

    try:
        orchestrator.resume()
        orchestrator.run()
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/]")
        raise


@main.command()
@click.option("--output-dir", default="output", help="Output directory")
def status(output_dir: str) -> None:
    """Show status of all debate runs."""
    config = DebateConfig(output_dir=output_dir)
    runs = CheckpointStore.list_runs(config)

    if not runs:
        console.print("No runs found.")
        return

    table = Table(title="Debate Runs")
    table.add_column("Run ID")
    table.add_column("Phase")
    table.add_column("Steps")
    table.add_column("Cost")

    for run_id in runs:
        store = CheckpointStore(config, run_id)
        try:
            state = store.load()
            completed = sum(
                1 for s in state.steps.values() if s.status.value == "completed"
            )
            total = len(state.steps)
            table.add_row(
                run_id,
                state.current_phase.value,
                f"{completed}/{total}",
                f"${state.meta.total_estimated_cost_usd:.4f}",
            )
        except Exception as e:
            table.add_row(run_id, f"[red]Error: {e}[/]", "", "")

    console.print(table)


@main.command()
@click.option("--run-id", required=True, help="Run ID to re-render")
@click.option("--output-dir", default="output", help="Output directory")
def render(run_id: str, output_dir: str) -> None:
    """Re-render markdown output from a saved checkpoint."""
    config = DebateConfig(output_dir=output_dir)
    store = CheckpointStore(config, run_id)

    try:
        state = store.load()
    except FileNotFoundError:
        console.print(f"[red]No checkpoint for run {run_id}[/]")
        sys.exit(1)

    renderer = MarkdownRenderer(config)
    written = renderer.render_all(state)
    console.print(f"[green]Rendered {len(written)} files:[/]")
    for path in written:
        console.print(f"  {path}")


def _make_dry_run_client() -> FakeLLMClient:
    """Create a fake client that returns minimal valid responses for all phases."""
    def respond(messages, system, tools, model, call_index, **kw):
        tool_name = ""
        tool_data = {}

        if tools:
            # Find the tool name from the tools list (skip web_search)
            for t in tools:
                if isinstance(t, dict) and "name" in t:
                    tool_name = t["name"]
                    break

        if tool_name == "submit_ideas":
            tool_data = {"ideas": [_make_dry_idea(i) for i in range(5)]}
        elif tool_name == "submit_merged_pool":
            merged = []
            for i in range(8):
                idea = _make_dry_idea(i, include_id=True)
                idea["proposed_by"] = ["bootstrapper", "market_analyst"]
                merged.append(idea)
            tool_data = {
                "ideas": merged,
                "eliminated": [],
                "conflicts": [],
            }
        elif tool_name == "submit_votes":
            tool_data = {
                "votes": [
                    {"idea_id": f"dry-idea-{i}-00000000", "vote": i < 6, "justification": "Dry run vote."}
                    for i in range(8)
                ]
            }
        elif tool_name == "submit_debate":
            tool_data = {
                "arguments": [
                    {
                        "idea_id": f"dry-idea-{i}-00000000",
                        "position": "response",
                        "argument": "Dry run argument.",
                        "vote": i < 3,
                    }
                    for i in range(5)
                ]
            }
        elif tool_name == "submit_synthesis":
            tool_data = {
                "summary": "Dry run synthesis.",
                "eliminated_ids": [f"dry-idea-{i}-00000000" for i in range(3, 5)],
                "surviving_ids": [f"dry-idea-{i}-00000000" for i in range(3)],
                "declare_finalists": True,
            }
        elif tool_name == "submit_deep_dive":
            tool_data = _make_dry_deep_dive()
        elif tool_name == "submit_stress_test":
            tool_data = _make_dry_stress_test()
        elif tool_name == "submit_final_vote":
            tool_data = {
                "voted_for_idea_id": "dry-idea-0-00000000",
                "ranking": [f"dry-idea-{i}-00000000" for i in range(3)],
                "justification": "Dry run vote.",
                "remaining_concerns": "None (dry run).",
            }
        elif tool_name == "submit_verdict":
            tool_data = _make_dry_verdict()
        else:
            return LLMResponse(text="[DRY RUN] No matching tool.", model="fake")

        return LLMResponse(
            tool_use=tool_data,
            tool_name=tool_name,
            model="fake",
            tokens_in=100,
            tokens_out=50,
        )

    return FakeLLMClient(response_fn=respond)


def _make_dry_idea(idx: int, include_id: bool = False) -> dict:
    d = {
        "name": f"Dry Run Idea {idx}",
        "description": f"A test idea for dry-run mode (idea {idx}).",
        "startup_cost_items": [{"item": "Domain", "cost_usd": 12.0}],
        "startup_cost_total": 12.0,
        "autonomy": {"acquisition": 80, "fulfillment": 85, "support": 75, "qa": 70},
        "revenue": {
            "day_90": "$500 (test)",
            "month_12": "$5,000/mo (test)",
            "year_3_ceiling": "$50,000/mo (test)",
        },
        "acquisition_path": {
            "first_10": "SEO + content marketing",
            "first_100": "Organic growth + partnerships",
            "first_1000": "Referral program + paid ads",
        },
        "moat": "Proprietary data from early users compounds over time.",
        "platform_risk": "Depends on Claude API — medium risk.",
        "key_risk": "Market may not exist at this price point.",
        "why_now": "AI tool costs dropped 10x in 2025, enabling sub-$500 startup.",
        "evidence": [
            {
                "claim": "AI API costs dropped significantly in 2025",
                "source": "UNSOURCED ESTIMATE",
                "date": "2025",
                "key_assumption": "Trend continues",
                "confidence": "medium",
            }
        ],
    }
    if include_id:
        d["idea_id"] = f"dry-idea-{idx}-00000000"
    return d


def _make_dry_deep_dive() -> dict:
    return {
        "idea_id": "dry-idea-0-00000000",
        "startup_cost_items": [{"item": "Domain", "cost_usd": 12.0}],
        "startup_cost_total": 12.0,
        "launch_plan_90day": "Week 1-4: Build MVP. Week 5-8: Beta. Week 9-12: Launch.",
        "automation_architecture": "Claude handles fulfillment, support, QA. Human handles strategy.",
        "acquisition_system": "SEO-driven content → organic signups → referral loop.",
        "revenue_model": {
            "day_90": "$500",
            "month_12": "$5,000/mo",
            "year_3_ceiling": "$50,000/mo",
        },
        "moat_analysis": "Data compounds with usage.",
        "proof_of_wtp": "Competitors charge $50-200/mo for similar services.",
        "platform_risk": "medium",
        "kill_criteria": "If <10 paying users by day 60, stop.",
        "why_now": "AI cost drop in 2025.",
        "autonomy": {"acquisition": 80, "fulfillment": 85, "support": 75, "qa": 70},
        "willingness_to_pay_evidence": ["Competitor A charges $99/mo", "Freelancers charge $500+"],
        "growth_ceiling_3yr": "$50,000/mo",
        "time_to_first_dollar": "30 days",
        "defensibility": "medium",
        "hidden_human_labor_risk": "low",
        "overall_confidence": "medium",
    }


def _make_dry_stress_test() -> dict:
    return {
        "idea_id": "dry-idea-0-00000000",
        "failure_scenarios": [
            {"scenario": "Market too small", "evidence": "Dry run test.", "likelihood": "medium"},
            {"scenario": "API costs spike", "evidence": "Dry run test.", "likelihood": "low"},
        ],
        "hidden_human_labor": "Quality review may require human spot-checks.",
        "likely_death_reason": "Insufficient demand at this price.",
        "overall_objections": ["Market size uncertain", "API dependency"],
    }


def _make_dry_verdict() -> dict:
    return {
        "ranked_table": [
            {
                "idea_id": f"dry-idea-{i}-00000000",
                "idea_name": f"Dry Run Idea {i}",
                "autonomy_acquisition": 80,
                "autonomy_fulfillment": 85,
                "autonomy_support": 75,
                "autonomy_qa": 70,
                "autonomy_composite": 79.5,
                "growth_ceiling": "$50,000/mo",
                "startup_cost": 12.0,
                "time_to_first_dollar": "30 days",
                "defensibility": "medium",
                "platform_risk": "medium",
                "hidden_human_labor_risk": "low",
                "willingness_to_pay": "Competitors charge $99/mo",
                "overall_confidence": "medium",
                "overall_finish": i + 1,
            }
            for i in range(3)
        ],
        "winner_idea_id": "dry-idea-0-00000000",
        "winner_narrative": "Best overall scores across autonomy, ceiling, and cost.",
        "runner_up_idea_id": "dry-idea-1-00000000",
        "runner_up_narrative": "Close second but lower defensibility.",
        "agent_positions": [
            {
                "role": role,
                "voted_for_idea_id": "dry-idea-0-00000000",
                "ranking": [f"dry-idea-{i}-00000000" for i in range(3)],
                "justification": "Dry run vote.",
                "remaining_concerns": "",
            }
            for role in ["bootstrapper", "market_analyst", "automation_architect", "devils_advocate"]
        ],
        "devils_advocate_remaining_concerns": "Market size and API dependency remain open questions.",
        "group_confidence": "medium",
    }


if __name__ == "__main__":
    main()
