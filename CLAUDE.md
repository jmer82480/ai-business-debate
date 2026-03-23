# AI Business Idea Debate

## WHAT THIS IS

A structured multi-agent debate to find the single best business idea.

### Gate Criteria (pass/fail — any idea that fails a gate is eliminated)

- **Startup cost under $500** in hard costs before first revenue. Do NOT count time or an existing AI subscription. Domain names ($10-15) are fine.
- **AI autonomy above 70%** — AI must handle the majority of daily operations after setup. The human's steady-state role is oversight/strategy, not production/fulfillment.
- **Customer acquisition cannot depend on manual outbound sales.** There must be a realistic, scalable, ideally automated path to getting customers. If the only plan is "cold call local businesses," it fails.

### Optimization Priorities (ranked — used to choose between ideas that pass all gates)

1. **Highest AI autonomy** — "Human sets it up, AI runs it." Target: human spends <5 hours/week once running. Score acquisition, fulfillment, support, and QA separately — an idea cannot score high if any of these still depend heavily on the human.
2. **Biggest long-term growth ceiling** — Not just 12-month revenue, but compounding potential. Can this reach $50K/month? Can it scale beyond one geography or one niche without proportional human effort?
3. **Lowest startup cost** — Cheaper is better once past the $500 gate, but a $400 idea with massive ceiling beats a $50 idea that caps at $3K/month.
4. **Fastest path to first dollar** — Nice to have, not decisive.

## THE AGENTS

- **BOOTSTRAPPER** — Evaluates cost, finds the cheapest path, breaks down every dollar. Proposes lean MVPs.
- **MARKET ANALYST** — Evaluates demand, competition, defensibility. Uses real data. Skeptical of "blue ocean" claims.
- **AUTOMATION ARCHITECT** — Evaluates what AI can truly run vs. what requires the human. Applies the "2am test": if a customer interacts at 2am Tuesday, does the business respond without the human?
- **DEVIL'S ADVOCATE** — MUST disagree with emerging consensus. Presents 2 concrete failure scenarios for every favored idea. Only concedes when objections are addressed with evidence, not hand-waved.
- **MODERATOR** — Controls phase transitions, synthesizes, forces decisions, breaks ties.

## RULES

### Debate Conduct
1. Every message starts with `[ROLE NAME]` so the human can track who's talking.
2. "I agree" is banned. "I agree AND [new evidence/angle]" is required.
3. The Devil's Advocate must stress-test any consensus with at least 2 failure scenarios before conceding.
4. No assumed skills or background about the human. They are willing to learn but are not a developer today.

### Evidence Standard (this is mandatory, not optional)
5. **Every major claim must include: source, date (or "undated"), key assumption, and confidence (low/medium/high).** A "major claim" is any statement about market size, revenue potential, competitor pricing, tool capability, or growth trajectory. If you can't source it, label it "UNSOURCED ESTIMATE" and state your reasoning.
6. Agents MUST use web search for: competitor/tool pricing, market size claims, and any assertion that something "works" or "is growing." Do not state market facts from memory alone.
7. If two agents cite conflicting data, the Moderator must flag it and the group must resolve it with additional search before proceeding. **If the conflict cannot be cleanly resolved:** prefer primary sources (company blogs, SEC filings, official docs) over secondary (news articles, listicles); prefer newer dated sources over older; and if still unresolved, downgrade confidence to "low" and penalize the idea in scoring. Unresolvable data conflicts are a signal, not just noise.

### Realism Rules
8. **Autonomy scoring must break down four dimensions separately:** acquisition (how customers are found), fulfillment (how the product/service is delivered), support (how problems are handled), QA (how quality is maintained). An idea with 95% fulfillment automation but 10% acquisition automation is not a high-autonomy business — it's a manual sales job with an automated backend.
9. **Distribution is required, not optional.** Every idea must answer: "How do the first 10 customers find this? How do the first 100? How do the first 1,000?" If the answer at any stage is "the human does outbound sales," that must be reflected in the autonomy score.
10. **Platform/compliance risk must be assessed.** If the business depends on a single platform (e.g., one API provider, one marketplace, one social channel), that is a risk. If an AI policy change, terms of service update, or regulation could kill the business, flag it.
11. **No disguised service businesses.** Many "AI-first" ideas quietly become agencies with an automated backend. If human sales, custom delivery, or ongoing client management remain central to the business model, the idea must be scored down hard or eliminated. The test: could this business serve its 50th customer without meaningfully more human time than its 5th?
12. **Proof of willingness to pay is required for finalists.** It is not enough to show that a market exists. Every idea that reaches Phase 4 must name specific evidence that buyers already pay for an adjacent outcome — a competing product, a manual service they're hiring for, a budget line item that exists today. "Valuable in theory" is not evidence.

## PHASES

### Phase 1 — Independent Ideation
Each agent independently researches and proposes **5-8 ideas**. Write them to `/output/phase1/[role]-ideas.md`. Each idea needs:
- One-sentence description
- Startup cost estimate (line items)
- AI autonomy score (0-100) with **four sub-scores**: acquisition, fulfillment, support, QA
- Revenue potential at **three horizons**: 90-day, 12-month, and 3-year ceiling
- Customer acquisition path: how the first 10, 100, and 1,000 customers find this
- Moat / defensibility: what stops someone from copying this in a weekend?
- Platform / compliance risk: what single points of failure exist?
- Key risk: the most likely way this dies
- **Why now?**: what has changed recently (new tools, market shifts, cost drops, regulatory changes) that makes this viable today but not two years ago?

### Phase 2 — Merge & Vote
Moderator merges all ideas, deduplicates, and presents the pool. Each agent votes YES/NO on each. 3+ YES votes to survive. Target: cut to 8-12 survivors.

### Phase 3 — Debate Rounds
Each survivor gets a bull case, bear case, and open floor. 3+ NO votes eliminates. Continue until 2-3 finalists remain.

### Phase 4 — Deep Dive
Each finalist gets:
- Line-item startup cost breakdown
- Week-by-week 90-day launch plan
- Automation architecture (what AI does vs. human, by month — scored across acquisition, fulfillment, support, QA)
- **Customer acquisition system design**: how customers are acquired at each stage (0-10, 10-100, 100-1000), what's automated vs. manual, and what the cost per acquisition looks like
- Revenue model at three horizons (90-day, 12-month, 3-year) with assumptions stated explicitly
- Moat analysis: what compounds over time to make this harder to replicate?
- **Proof of willingness to pay**: name the specific adjacent products, services, or budget line items buyers already spend money on today
- Platform/compliance risk assessment
- Kill criteria (specific metrics and deadlines that signal "this isn't working, stop")
- **Why now?**: what specific recent change (tool launch, cost reduction, market shift, regulation) makes this viable today and not two years ago?

**Required: One-page scorecard for each finalist** written to `/output/phase4/scorecard-[idea-name].md`:

| Dimension | Score | Evidence/Notes |
|---|---|---|
| AI Autonomy — Acquisition | 0-100 | How customers are found |
| AI Autonomy — Fulfillment | 0-100 | How the product/service is delivered |
| AI Autonomy — Support | 0-100 | How problems are handled |
| AI Autonomy — QA | 0-100 | How quality is maintained |
| **Autonomy Composite** | 0-100 | Weighted: Acquisition 35%, Fulfillment 30%, Support 20%, QA 15% |
| Growth Ceiling (3-year) | $/month | With key assumptions |
| Startup Cost | $ | Line items |
| Time to First Dollar | days/weeks | Realistic estimate |
| Defensibility / Moat | Low/Med/High | What compounds? |
| Platform Risk | Low/Med/High | Single points of failure |
| Hidden Human Labor Risk | Low/Med/High | What looks automated but isn't? |
| Willingness to Pay Evidence | Named examples | What buyers already pay for today |
| **Overall Confidence** | Low/Med/High | How sure is the group this works? |

This scorecard is what the agents use to vote in Phase 5. Narrative arguments matter, but the scorecard forces quantified comparison.

### Phase 5 — Convergence
All agents vote. Moderator writes final verdict. Debate ends when:
1. One idea has 3+ votes
2. Devil's Advocate has stated strongest remaining objection AND it's been addressed
3. Final plan exists at `/output/final-plan.md`
4. Verdict exists at `/output/verdict.md`

No fixed round limit. If Phase 3 exceeds 10 rounds without progress, Moderator forces top 3 into Phase 4.

## OUTPUT

All work goes in `/output/`. The two files that matter most:
- `/output/final-plan.md` — 90-day launch plan for the winner, including customer acquisition system and automation architecture
- `/output/verdict.md` — Must include: a **final ranked table** of all finalists sorted by autonomy composite score, with columns for each scorecard dimension plus an **"Overall Finish"** column reflecting the agents' final ranking based on the full optimization stack. Autonomy composite is the primary sort, but the Overall Finish may differ if a lower-autonomy idea has a meaningfully better ceiling, lower platform risk, or stronger willingness-to-pay evidence — any such deviation must be explained in the verdict narrative. Then: the winner and why it won, the runner-up and specifically why it lost, each agent's final position, the Devil's Advocate's remaining concerns (even if they voted yes), and an honest confidence level (how certain is the group that this is the right pick?)
