# AI Business Idea Debate — How to Run This

## Prerequisites

1. **Claude Code installed** (v2.1.32 or later) — check with `claude --version`
2. **Claude Pro or Max plan** (Agent Teams requires Opus 4.6)
3. **tmux installed** (optional but recommended — lets you see each agent in its own pane)
   - Mac: `brew install tmux`
   - Ubuntu/Debian: `sudo apt install tmux`

## Step 1: Enable Agent Teams

Open your settings file:

```bash
# The file is at ~/.claude/settings.json
# If it doesn't exist, create it
```

Add or merge this into it:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

If you already have other settings in that file, just add the `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` line inside the existing `"env"` block.

## Step 2: Navigate to This Project

```bash
cd /path/to/ai-business-debate
```

Make sure the `CLAUDE.md` file is in this directory. Claude Code will read it automatically.

## Step 3: Create the Output Directory

```bash
mkdir -p output/phase1 output/phase2 output/phase3 output/phase4
```

## Step 4: Launch Claude Code

```bash
claude
```

Or if you want split panes (recommended):

```bash
claude --teammate-display tmux
```

## Step 5: Paste This Prompt

Copy and paste the following into Claude Code. This is the launch prompt that spawns the team:

---

```
I need you to run a structured multi-agent debate to find the best AI-first business idea. Read the CLAUDE.md for the full protocol — it has gate criteria, optimization priorities, evidence standards, realism rules, phase structure, and convergence rules. Follow it precisely.

Create an agent team with 5 teammates:

1. "bootstrapper" — Evaluates every idea through startup cost. Breaks down costs to the dollar with real pricing from web search. Proposes lean MVPs. Has a strong bias toward ideas under $200, but this is the agent's preference, not a protocol rule — the hard gate is $500 per CLAUDE.md.

2. "market-analyst" — Evaluates demand, competition, defensibility, and distribution using real data. MUST use web search for competitor pricing, market sizes, and demand signals. Skeptical of "blue ocean" claims. For every idea, answers: who is already paying for something similar?

3. "automation-architect" — Evaluates what AI can truly handle vs. what requires the human. Scores autonomy across four dimensions separately: acquisition, fulfillment, support, QA. Applies the "2am test" from CLAUDE.md. Designs specific automation stacks with named tools.

4. "devils-advocate" — MUST disagree with any emerging consensus. For every favored idea, presents 2 concrete failure scenarios with evidence. Only concedes when objections are addressed with data, not hand-waving. Also proposes contrarian/overlooked ideas the others will miss.

5. "moderator" — Controls phase transitions. Merges and deduplicates ideas. Runs votes. Flags conflicting data between agents and forces resolution. Synthesizes debate rounds. Forces decisions when stuck. Writes final verdict including why the runner-up lost.

CRITICAL RULES:
- Every agent message must start with [ROLE NAME] so I can track who's talking at every step
- EVIDENCE IS MANDATORY: every major claim about market size, revenue potential, tool pricing, or growth needs a source, date, assumption, and confidence level. "UNSOURCED ESTIMATE" is allowed but must be labeled.
- Phase 1: Each agent independently researches and proposes 5-8 ideas using web search. Write to output/phase1/[role]-ideas.md. Agents should NOT see each other's lists during this phase.
- Each idea in Phase 1 must include: startup cost, autonomy sub-scores (acquisition/fulfillment/support/QA), revenue at 3 horizons (90-day, 12-month, 3-year), customer acquisition path, moat/defensibility, platform risk, key risk, and "why now?" (what recent change makes this viable today).
- After Phase 1, follow the protocol in CLAUDE.md through all phases until convergence
- The debate ends when there's a winner with a 90-day plan in output/final-plan.md and a verdict in output/verdict.md
- The verdict MUST include a final ranked table of all finalists (sorted by autonomy composite, with all scorecard dimensions as columns) plus the winner/runner-up narrative
- No fixed round limit — let the agents decide when they've genuinely converged
- If Phase 3 goes past 10 rounds without progress, moderator forces top 3 into final showdown

Start Phase 1 now. Have all agents research and generate their ideas in parallel.
```

---

## What to Expect

- If using tmux, you'll see 5+ panes — one per agent plus the lead
- Phase 1 will take a few minutes as agents research independently
- You can watch each agent working in real time
- The full debate might take 15-30 minutes depending on how many rounds
- You can intervene at any point by messaging the lead or individual agents
- Final deliverables land in `output/final-plan.md` and `output/verdict.md`

## Tips

- **To see the task list**: Press Ctrl+T (in-process mode)
- **To cycle between agents**: Press Shift+Down (in-process mode)
- **To intervene**: Just type to the lead agent — "push harder on idea X" or "I think you're overlooking Y"
- **If an agent gets stuck**: The lead can message teammates directly
- **Cost**: Expect roughly $5-15 for the full debate depending on how many rounds

## After It's Done

Read these two files:
- `output/verdict.md` — Starts with a **ranked table** of all finalists sorted by autonomy composite, with every scorecard dimension as columns plus an "Overall Finish" column. The winner may not be the top autonomy scorer — if it isn't, the narrative explains why the full optimization stack favored it. Also includes: why the winner won, why the runner-up lost, each agent's final position, Devil's Advocate remaining concerns, and group confidence level.
- `output/final-plan.md` — 90-day launch plan including customer acquisition system and automation architecture

If you want to run it again with different priorities, edit the gate criteria and optimization priorities at the top of CLAUDE.md and relaunch.
