# Adjacent — backend

Audience-development decision support for programmed cultural venues (starting
with independent / arthouse cinemas).

A venue supplies its recent programme and its city. Adjacent characterises the
programme's cultural taste using the Qloo taste graph, discovers adjacent
audience cohorts it does not currently reach, locates where those cohorts
concentrate geographically, and proposes a testable programming/outreach
hypothesis — with every number traceable to a Qloo response.

**Design constraints that are not negotiable:**
programme-level analysis only · no PII · no invented Qloo scores · no claim that
Qloo predicts attendance or conversion · every rendered number has provenance ·
"insufficient evidence" is a first-class output, not an error state.

> **Status (4 Oct 2026).** Day 1 (backend foundation), **Milestone 1 (the fixture
> spine)** and **Milestone 2 (the explicit agent orchestrator)** are done. A run is
> driven by a state machine — INIT → PLAN → RESOLVE → ANALYSE → EXPAND → RANK →
> EVALUATE → STOP — over typed tools, with a budget, canonical stop reasons, and an
> orchestration trace separate from the Qloo trace. All of it on fixtures: no API
> key, no network call, no LLM. **Still absent by design:** the map/geography step,
> the programme bet, the audience layer, live Qloo mode, any LLM. See
> `FEATURES_NOT_BUILDING.md`.

---

## Everything works without an API key

The test suite, the probe (dry-run) and the whole fixture-backed chain run with
`QLOO_API_KEY` unset. That is deliberate: 5½ days of the plan are key-independent.

```bash
make setup              # pip install -e ".[dev]"
make test               # 128 tests, no key needed
make lint               # ruff
make probe              # writes docs/API_NOTES.md + docs/api_probe_results.json
make run                # uvicorn on :8000
make mock-run           # end-to-end fixture run through the API surface
make milestone-1        # fixture spine (now agent-driven), strong scenario
make milestone-1-sparse # fixture spine (now agent-driven), insufficiency scenario
```

The Milestone 1 commands are the same as:

```bash
cd backend
python -m app.cli run --fixture fixtures/portland_strong.json --mock
python -m app.cli run --fixture fixtures/insufficient_evidence.json --mock
```

`make milestone-1` ends `stop_reason = complete`; `make milestone-1-sparse` ends
`stop_reason = insufficiency` and prints *"I do not have enough Qloo evidence to
name an adjacent audience for this programme."* Both exit 0 — a refusal is the
product working, not a failure. Captured output for both runs lives in
`docs/milestone_1_strong.txt` and `docs/milestone_1_sparse.txt`.

## With a key

```bash
cp .env.example .env         # then put the key in it; .env is gitignored
export QLOO_API_KEY=...
make probe-live              # the same suite against the real API
```

The client sends `X-Api-Key` as a **header** to
`https://hackathon.api.qloo.com`. Staging and production both return 401 for a
hackathon key — that is not a symptom of a bad key. The key is never placed in a
query string and is redacted from every trace row.

## Layout

```
backend/app/config.py          settings from env; redacted view; never logs the key
backend/app/agent/             the explicit state machine (state, orchestrator, budget, stop, tools)
backend/app/cli.py             python -m app.cli run --fixture … --mock
backend/app/domain/cohorts.py  candidate construction (shared tag → subtype → domain)
backend/app/domain/ledger.py   the provenance ledger: no number without a source
backend/app/domain/reasons.py  machine-readable rejection / exclusion codes
backend/app/domain/scoring.py  the single logical build_and_rank_cohorts operation
backend/app/evidence.py        the evidence gate + the exact insufficiency messages
backend/app/runner.py          the Milestone 1 pipeline + its rendered output
backend/app/main.py            /health and /debug/* only (no product routes yet)
backend/app/qloo/client.py     the ONLY place an HTTP request to Qloo is built
backend/app/qloo/params.py     strict allowlist; UNVERIFIED params cannot be sent silently
backend/app/qloo/models.py     typed responses (tags, entities, heatmap) + provision 
backend/app/qloo/mock.py       fixture-backed client, same interface
backend/app/qloo/trace.py      provenance for every call, with redaction
backend/tests/fixtures/        two synthetic scenarios (strong / insufficient evidence)
docs/milestone_1_*.txt         captured output of both Milestone 1 commands
scripts/qloo_probe.py          probes A–H (+B2/C2/G2) → docs/API_NOTES.md
docs/API_NOTES.md              what we OBSERVED, vs what the docs imply
FEATURES_NOT_BUILDING.md       the frozen scope guard
```

## The agent (Milestone 2) — control flow you can read

`backend/app/agent/` is an explicit state machine, not a framework and not an LLM.
One loop, five named steps, every transition recorded:

```
INIT → PLAN → RESOLVE → EVALUATE → PLAN → ANALYSE → EVALUATE → PLAN → EXPAND
     → EVALUATE → PLAN → RANK → EVALUATE → PLAN → STOP
```

| Piece | File | What it decides |
|---|---|---|
| `AdjacentState` | `agent/state.py` | the one record of a run: input, artefacts, control state, transitions |
| `AgentOrchestrator` | `agent/orchestrator.py` | PLAN (which phase) → SELECT (which tool) → ACT (one bounded action) → EVALUATE (gate + ceilings) → STOP |
| `Budget` | `agent/budget.py` | 14 steps, 24 Qloo calls, 90 s wall clock; refuses *before* an action it cannot afford |
| `StopReason` | `agent/stop.py` | `complete`, `insufficiency`, `budget_exhausted`, `invalid_input`, `error`, `timeout` |
| Tools | `agent/tools.py` | `resolve_programme`, `get_taste_profile`, `expand_candidates`, `rank_cohorts`, `assess_evidence` |

Two distinctions the machine exists to preserve:

* **insufficiency ≠ error.** "Qloo has nothing on this programme" is a finding and
  ends in `insufficiency` with the product's exact sentence. "Qloo returned a 503"
  ends in `error`. They are never reported as each other.
* **budget_exhausted ≠ insufficiency.** Running out of steps or calls is an
  operational limit; the run says so (`budget_exhausted`) instead of quietly
  presenting a partial answer as a complete one.

The orchestrator owns no domain logic and no HTTP. It holds five tools and a
runtime; `runner.FixturePipeline` implements those tools over the Milestone-1 step
functions *unchanged*, which is what keeps `run_fixture()` and the CLI identical.
A run leaves three separate records: the **orchestration trace**, the **Qloo
trace**, and the **provenance ledger**.

```bash
python -m app.cli run --fixture fixtures/portland_strong.json --mock --show-agent-trace
```

## Milestone 1 — what the fixture spine guarantees

**One normalisation context per comparison.** Qloo affinity is normalised per
query, so scores from two queries are not comparable. The ranker therefore scores
every candidate cohort in a domain from **one** call
(`filter.results.entities` = every candidate in that domain), and records the whole
thing as **one** logical trace operation, `build_and_rank_cohorts`. Ordering uses
band strength → novelty proxy → qualifying-member count; mean affinity is only ever
a within-context tiebreaker, and a guard sets `cross_context_tiebreak_used` if two
normalisations would ever have to be compared. Tests:
`backend/tests/test_cohort_ranking_single_normalisation.py`.

**Every displayed number has a declared source.** The renderer cannot format a
number on its own: it must go through `app/domain/ledger.py` with either a Qloo
`call_id`, `file:<fixture>`, or `input:`. A number citing a call with no trace row
is reported as unverified rather than printed quietly. The strong run reports 129
numbers — 100 backed by a Qloo-call trace row, 29 derived from the fixture file or
the run's own bookkeeping — and 0 unverified.

**Rejections are codes, not prose.** `app/domain/reasons.py` defines the
machine-readable rejection codes (`insufficient_members` → `insufficient_affinity`
→ `weak_evidence`) and exclusion codes (`below_medium`, `oversaturated`,
`no_affinity_returned`, `not_returned_by_context`). A rejected cohort is printed
with its members and its evidence, never hidden.

**What the fixture run does not prove** is printed with every run: the mock does
not apply `filter.popularity.*`, it returns every id present in the fixture branch,
and it contains no backfill results. Real behaviour is probe D in
`docs/API_NOTES.md`.

## Two files worth reading first

* **`docs/API_NOTES.md`** — the probe report. It states plainly whether it has
  been executed against the real API, and every unresolved parameter question
  with the work it blocks.
* **`FEATURES_NOT_BUILDING.md`** — the refusal list, committed on day one.

## Data status

Fixture files declare in-band that they are synthetic. Every response object
carries `source` (`qloo` | `mock`) and `data_status` (`measured` | `fixture`), so
fixture data cannot be mistaken for measured Qloo output in a log, a payload or a
UI.

No personal data is stored anywhere. No CRM, ticketing or mailing-list
integration exists or is planned.
