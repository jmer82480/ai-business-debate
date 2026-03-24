# AI Business Idea Debate

A deterministic orchestration engine that runs a structured multi-agent debate to find the best AI-first business idea. Five AI agents (Bootstrapper, Market Analyst, Automation Architect, Devil's Advocate, Moderator) debate through 5 phases, producing a final verdict and 90-day launch plan.

## Architecture

The engine is built as a Python CLI with typed workflow state as the source of truth:

```
debate/
├── schemas/        # Pydantic models — ideas, votes, scorecards, state
├── llm/            # LLM client abstraction (roles never import anthropic directly)
├── roles/          # Role adapters — one per debate agent
├── prompts/        # Prompt templates per role × phase
├── validators/     # Gate criteria, evidence standards, phase transitions
├── renderers/      # State → markdown output files
├── storage/        # Atomic checkpoint persistence with resume
├── orchestrator.py # Main loop — phase transitions, validation, rendering
├── context.py      # Budget-aware context compression
├── config.py       # All tunables (models, limits, costs, paths)
└── cli.py          # Click CLI: run, resume, status, render
```

Key design decisions:
- **Machine-readable state** is the source of truth; markdown files are rendered artifacts
- **LLM client abstraction** — roles depend on a protocol, not the Anthropic SDK
- **Atomic checkpoint writes** — write to temp file, `os.replace()` to final path
- **Stable idea IDs** — slug + UUID suffix, survives name drift across phases
- **Failure taxonomy** — transport errors (retry), validation errors (corrective reprompt), bad output (reprompt)
- **Context compression** — later phases get summaries, not full transcripts

## Prerequisites

- Python 3.11+
- An Anthropic API key (set `ANTHROPIC_API_KEY` environment variable)

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Start a new debate

```bash
debate run
```

Options:
- `--model claude-sonnet-4-6` — default model for all phases
- `--deep-dive-model claude-opus-4-6` — model for Phase 4 deep dives
- `--no-web-search` — disable web search (faster, less evidence)
- `--dry-run` — use fake LLM client (no API calls, validates full flow)
- `--max-rounds 10` — max Phase 3 debate rounds before forcing finalists
- `--output-dir output` — where markdown files are rendered
- `-v` — verbose/debug logging

### Resume a failed or interrupted run

```bash
debate resume --run-id <run-id>
```

Resume restores the **original run config** (model, web search, max rounds) from the checkpoint. You don't need to re-pass flags like `--no-web-search` — they're persisted automatically.

### Check status of all runs

```bash
debate status
```

### Re-render markdown from a checkpoint

```bash
debate render --run-id <run-id>
```

### Dry-run (validate without API calls)

```bash
debate run --dry-run
```

This exercises the full pipeline with a fake LLM client — useful for testing that schemas, validators, renderers, and orchestration logic work end-to-end.

## Output

All output goes to the `output/` directory:

- `output/phase1/` — each role's independent ideas
- `output/phase2/` — merged pool and survivors
- `output/phase3/` — debate round summaries
- `output/phase4/` — deep dives and scorecards
- **`output/verdict.md`** — final ranked table, winner/runner-up narrative, agent positions, confidence
- **`output/final-plan.md`** — 90-day launch plan with acquisition system and automation architecture

## Checkpoints

State is persisted to `checkpoints/<run-id>/state.json` after every step. If a run fails:
1. The error and step are recorded
2. Run `debate resume --run-id <id>` to pick up where it left off
3. Completed steps are skipped; failed steps are retried

Debug artifacts (raw API responses) are saved to `checkpoints/<run-id>/debug/` **only on failure** — not on every step. Bounded to 50 files, 100KB each.

### Rate limits

With web search enabled, a single call can consume 300K+ input tokens (search results are included). If your plan has a low per-minute token limit, use `--no-web-search` or expect longer backoff waits (60s+ between retries on 429).

## Testing

```bash
python3 -m pytest tests/ -v
```

101 tests covering: schemas, validators, checkpoint persistence, context compression, renderers, orchestrator flow, phase invariants, failure recovery, resume fidelity (config + client + roles + all phases), cost tracking, truncation guards, merge validation, and Phase 2/3/4/5 resume safety.

## Protocol

The full debate protocol is defined in `CLAUDE.md` — gate criteria, optimization priorities, evidence standards, realism rules, phase structure, and convergence conditions.

## Alternative: Agent Teams Mode

For an interactive experience, you can also run this debate using Claude Code's Agent Teams feature. See the launch prompt in `CLAUDE.md` for details. The CLI engine provides deterministic, resumable, auditable runs as an alternative.
