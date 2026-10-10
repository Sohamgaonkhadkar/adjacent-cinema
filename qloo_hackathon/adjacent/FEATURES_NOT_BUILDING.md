# FEATURES NOT BUILDING

**Status: FROZEN on Day 1 (4 October 2026).**

This file is a scope guard, not a wish list. Every item below has been considered
and deliberately refused. The failure mode it prevents is specific: arriving at
day 20 with nine half-features and a broken demo. If a future conversation
proposes any of these, the answer is in this file, with the reason.

Deadline: **30 October 2026**. The MVP is defined in
`../ADJACENT_PRODUCT_AND_EXECUTION_PLAN.md` (Parts 6 and 16). Anything not in
that MVP list is out of scope until the MVP is deployed and the video is recorded.

---

## Not building now

| ❌ Refused | Reason |
|---|---|
| **Polished chatbot UI** | The agent's *decisions* are the product. A chat window hides them behind prose, which also happens to be the easiest way to look like an LLM wrapper. The interface is a decision document, not a conversation. |
| **Generic recommendation feed** | Wrong user entirely. We do not recommend things to people; we characterise a programme and locate a cohort. A feed would put us in the most crowded lane in this hackathon cycle. |
| **Mobile app** | The user is at a desk with a booking grid and a spreadsheet. No mobile-specific job to be done. |
| **CRM / ticketing integration** | Requires partnerships, procurement and PII handling — and the product's entire premise is that it needs *no* first-party data. |
| **Individual audience profiling** | The product is programme-level by design. Person-level profiling would break the privacy stance, the data model, and the honesty story in one move. |
| **PII storage** | We have no user accounts and no customer records. Zero PII is a design property we can state in writing, which no competitor in this sector's tooling can. |
| **Conversion prediction** | Qloo cannot support it. Any number we produced would be invented, and inventing one is the fastest way to lose the room with judges who work at Qloo. |
| **Attendance prediction** | Same as above. We produce a falsifiable hypothesis, never a forecast. |
| **Automated advertising / campaign execution** | Different product, different data, and it would make us responsible for spend we cannot justify. The Test Card hands the decision to a human. |
| **Live external catalogue integrations** | Distributor availability has no public API. The Test Card states that availability is not checked, which is honest and costs nothing. |
| **Multi-city analytics** | One city, done properly, is the MVP. Multi-city is a dashboard nobody asked for. |
| **Season-over-season analytics** | Interesting, unbuildable before code freeze, and it invites a comparison we cannot validate. V2 at the earliest. |
| **Trend monitoring** | `/v2/trending` is a 2-call enhancement at best. It does not change the decision, so it does not ship in the MVP. |
| **Advanced audience catalogue** | `/v2/audiences` is a lookup, not a ranker, and cross-audience score comparison is invalid (scores are normalised per query). It ships as a labelled secondary layer in V1 *if* the catalogue proves rich enough — never as the mechanism. |
| **Model training / fine-tuning** | Nothing here needs it. A hosted LLM does two narrow text jobs (parse, render prose from typed results) and has no path to producing a fact. |
| **"Predictive" anything** | The refusal is the differentiator. We say so out loud. |

## Refused during Day 1 specifically

| ❌ Refused | Reason |
|---|---|
| Agent orchestration / ranking engine | Day 1 proves the client contract. Build the ranking once probe D has told us which ranking is valid. |
| PostgreSQL | Not needed yet. Adding a database before there is data to persist is how the first day disappears. |
| LangGraph or any agent framework | The agent is a small explicit state machine; a framework would obscure the trace, which is a submission differentiator. |
| Redis | A Postgres table (later) covers caching until proven otherwise. |
| Frontend of any kind | Not one hour on UI until the client contract and the probe results are done. The only "UI" allowed on Day 1 is `/debug/*`. |
| The map | Blocked behind probe E (real per-city heatmap coverage). |
| Branding, logo, landing page, colour palette | Zero effect on judging criteria, large effect on time. |
| `take`/`page` on `/entities` | Not in the documentation we verified. We do not send unverified parameters, so we do not expose them. |
| Any parameter not in `app/qloo/params.py` | Qloo silently ignores unknown parameters, so a typo returns an empty result set that looks like "no data". The validator raises instead. |

## Refused during Milestone 1 specifically

| ❌ Refused | Reason |
|---|---|
| The geography step (heatmap, rings, districts) | Milestone 1 proves the decision path — cohorts, ranking, gate, provenance. Geography is the next milestone and depends on probe E for real city coverage. |
| The programme bet (runner-up, two-sided score, Test Card) | It needs the cohort ranking to be demonstrably trustworthy first. Building it now would produce a bet with no provenance discipline behind it. |
| The audience layer (`/v2/audiences`) | A lookup, not a ranker, and cross-audience comparison is invalid (per-query normalisation). Secondary layer at best. |
| Any LLM prose | Every sentence in the CLI output is rendered from typed results by deterministic code. Nothing in the milestone needs a model, and a model must never write provenance or a reason code. |
| Live Qloo mode | Blocked: no key in this environment, and the ranking path depends on probe D (`filter.results.entities`), which has not been verified against the real API. A run without `--mock` exits 2 with that explanation rather than pretending. |
| Fuzzy title matching / `/search` resolution | Milestone 1 resolves only explicit ids and `external.<family>.ids`. Guessing a title match would create a fact Qloo did not return. Search-based resolution is a later, separately-tested step. |
| Postgres cache, Redis, SSE streaming | No data to persist yet, no stream to stream. The fixture run takes under a second. |
| Frontend, map rendering, share links | Not one hour on UI until the live ranking is verified. |
| The two-sided score (existing audience x target cohort) | Needs a second scored context per cohort and a decision about comparing normalisations. Not in this milestone. |
| Multi-venue / multi-tenant runs | One venue, one programme, one city — the beachhead. |

## Refused during Milestone 2 specifically

| ❌ Refused | Reason |
|---|---|
| An LLM anywhere in the loop | The agent is a control system, and this milestone exists to prove the control system before any probabilistic text is introduced. The plan's two LLM jobs (parse messy input, render prose from typed results) are later, narrow, and neither is needed while input is structured and output is rendered from typed results. |
| LangGraph / any agent framework | The value of the state machine is that transitions, budget refusals and stop reasons are all visible in our own code. A framework would hide exactly the thing the submission depends on. |
| Geography: heatmap, MapLibre, neighbourhood naming, city coverage, venue pins | Depends on live Qloo validation (probe E) for real city coverage. Belongs to the geography milestone. |
| The programme bet, the test card, the two-sided score | Needs the ranked cohorts and the geography step to be trustworthy first. |
| The audience layer (`/v2/audiences`), trend checks | Not tools this milestone needs; `/v2/audiences` is a lookup, not a ranker. |
| PostgreSQL, Redis, any persistence of runs | Nothing must survive a restart yet. A run is seconds long and lives in one process. |
| A second Qloo client, a second runner, a second ranking path | `run_fixture()` calls the orchestrator, the orchestrator calls the Milestone-1 step functions. One pipeline, one client, one ranker. |
| A new probe, or marking live Qloo behaviour as verified | `scripts/qloo_probe.py` is unchanged and still waiting for a key. Nothing becomes "verified" without executing it against Qloo. |
| Retries-by-reasoning, self-correction loops, "the agent decides to try again" | Failure handling is typed and explicit: `insufficiency`, `error`, `budget_exhausted`, `invalid_input`. A loop that re-reasons is a loop that can stall, which is risk R8. |

## The rule that decides future arguments

> **If a feature does not (a) require Qloo, (b) change a decision the programmer
> makes, and (c) fit inside the phases already planned, it does not get built
> before 30 October.**

Cut order if the build runs late: trend check → season comparison → audience
lens → shareable link → runner-up card. **Never cut:** provenance, the evidence
gate, or the insufficiency messages.
