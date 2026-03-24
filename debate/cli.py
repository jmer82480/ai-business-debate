"""CLI entry point — run, resume, status, render."""

from __future__ import annotations

import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from debate.config import DebateConfig
from debate.llm.anthropic import AnthropicClient
from debate.llm.dry_run import make_dry_run_client
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
        client = make_dry_run_client()
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
        client = make_dry_run_client()
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


if __name__ == "__main__":
    main()
