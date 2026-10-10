# Adjacent M13.6.5 — Signal Integrity, Product Evidence & Hackathon Readiness

**Review date:** 9 October 2026  
**Scope:** source snapshot audit, targeted backend/frontend fixes, product decision, external research, verification status  
**Disposition:** **NOT READY for supervised modelling; GO for a narrowly scoped, evidence-traceable cinema programming decision product**

---

## 1. Executive decision

Adjacent addresses a real and specific job: help an independent or repertory cinema programmer discover a non-obvious cultural programming direction, justify why it is worth testing, check practical constraints, and capture what happened. The appropriate promise is decision support and experiment design—not predicting ticket sales, attendance, or revenue.

The codebase is a substantial prototype with Qloo integration and an existing workflow for intake, entity resolution, taste signals, cross-domain candidate exploration, geographic evidence, Programme Bet, and Test Card. But **the current data cannot validate the core product claim**. The local source archive is not the same state as the latest M13.6.4 Arena transcript, the archived database has zero cultural-tag signal, prediction records show fallback/provenance defects, and many outcome rows are not outcome measurements at all.

### Decisions

| Question | Decision |
|---|---|
| Should Adjacent be scrapped? | **No.** Preserve the core pipeline and narrow the product story to cinema programming decisions. |
| Should model training start? | **No — NOT_READY.** There is no valid supervised dataset in the archived source state, and the M13.6.4 transcript also says NOT_READY. |
| Is the “attendance prediction” positioning defensible? | **No.** Affinity and popularity are not ticket intent, attendance, or willingness to pay. |
| What should be built next? | A verified golden path from a real programme input to a feasible, traceable Programme Bet and a measurable Test Card. |
| What are the submission-critical gaps? | Live/error-mode verification, true source provenance in the UI, working frontend/API deployment, safe repository packaging, and real practitioner feedback. |

**Recommended product promise:** “Adjacent helps an independent-cinema programmer develop and justify a non-obvious cultural programming hypothesis, turn it into a feasible small experiment, and record what happened.”

---

## 2. Scope and confidence: there are two different repository/data states

This review used the source ZIP extracted at Git HEAD `9ce72640097d1b557f4871132706cb8da4f38f40` (`M13.6: Prospective Temporal Qloo Signal Experiment`) and the M13.6.4 Arena transcript supplied in the conversation. The ZIP’s code does **not** contain the M13.6.4 commit `8a0c527` or the reported `m13_6_4_coverage_audit.py`; the transcript describes a later state. Their metrics are kept separate below rather than merged into one denominator.

The source archive contains a working-tree `.env` file with a non-empty Qloo API key. It is ignored by Git, but it was included in the ZIP package. This report and the code patch do not reproduce the key. **If this archive was shared outside a trusted environment, revoke/rotate that key and repackage without `.env`.**

### 2.1 What the M13.6.4 transcript reports (not independently reproduced from the ZIP)

| Metric | Transcript-reported value | Meaning / caveat |
|---|---:|---|
| Planned films | 308 | Transcript's planned-film denominator |
| No Qloo entity resolution | 46 / 308 | Unresolved films |
| Films with non-empty tags | 36 / 308 (11.7%) | The strongest evidence of a meaningful cultural feature in that report |
| Films with a snapshot row | 262 / 308 (85.1%) | Row existence is not feature coverage |
| Empty snapshots | 226 / 308 | Snapshot existence inflated the earlier “94.2% feature coverage” claim |
| Prediction rows with reported temporally eligible, non-empty tags | 165 / 2,068 (7.98%) | Transcript calculation; not recalculated against this archived ZIP |
| Temporally eligible snapshot rows regardless of usability | 1,525 / 2,068 (73.7%) | Eligibility alone does not mean usable cultural evidence |
| Final outcome rows | 11, all `SOLD_OUT_OBSERVED` | Positive-only label set; no `AVAILABLE_NEAR_SHOWTIME` negative class |
| Outcome-linked predictions with actual prediction-time tag signal | 0 / 11 | Cannot test whether signal explains outcome |
| Duplicate title noted | “The Devils” | HTML entity versus apostrophe representation |
| Transcript test result | 422 passed, 4 skipped | Reported by Arena; not reproduced against this archived source ZIP |

These transcript numbers justify keeping model readiness at **NOT_READY**. Eleven sold-out observations are not attendance labels, and all-positive outcomes cannot support a discrimination evaluation.

### 2.2 What I measured in the archived source ZIP

The independent audit script opened the database with SQLite read-only mode. Database size was 3,248,128 bytes. No database mutation or backfill was performed.

| Archived DB table / condition | Measured count | Interpretation |
|---|---:|---|
| `canonical_film` | 312 | Canonical film rows in this snapshot; not the same denominator as transcript's 308 planned films |
| `film_resolution` | 618 | Multiple resolution states/rows exist at film-level history/context |
| `qloo_feature_snapshot` | 231 | Stored feature rows |
| Feature rows classified as `POPULARITY_ONLY` | 208 | Popularity is present, but no non-empty tag / finite affinity evidence exists |
| Feature rows classified as `IDENTITY_ONLY` | 23 | Entity identity exists, but no popularity or cultural signal exists |
| Feature rows with valid non-empty tags/affinity | **0** | Zero demonstrated cultural-tag/affinity signals in this snapshot |
| Feature-row provenance `resolution/search` | 231 / 231 | Stored feature table rows are from resolution/search provenance, not a demonstrated Insights cultural payload |
| `prediction_snapshot` | 2,175 | Prediction rows across 24h / 72h / 168h horizons |
| Rows marked `AVAILABLE_AT_PREDICTION_TIME` | 1,259 | Legacy status label; this does not prove cultural signal is present |
| Rows marked `NO_FEATURE` | 916 | Legacy feature status |
| `NO_FEATURE` rows with popularity but no Qloo feature timestamp | **328** | Direct evidence of the resolution-popularity fallback bug |
| Prediction records created after their prediction timestamp | **90** | These cannot be described as prospectively recorded predictions without a documented reconstruction protocol |
| `outcome_measurement` | **0** | No outcome measurement records in this archive |
| Prediction outcomes | 2,175 `PENDING` | No outcome-final rows in this database snapshot |
| Candidate normalized screening duplicate groups | **96** | Same venue/date/time/format and equivalent title after decoding/normalization; manual reconciliation required |
| Recorded screenings / screening snapshots | 763 / 4,667 | Scraped observation history exists, but it is not a substitute for actual ticket/attendance labels |

The first duplicate groups include titles represented both with HTML entities and apostrophes, such as `The Devil&#039;s Rejects` vs `The Devil's Rejects`, and `Ken Russell&#039;s The Devils: The Director&#039;s Cut` vs its apostrophe form. The fix prevents future duplicate creation where one unambiguous normalized match exists; it deliberately does **not** automatically merge existing historical rows.

### 2.3 Why the two states must not be merged

The later Arena transcript reports 290 snapshots / 36 tagged films / 11 outcome-final rows. The archived ZIP has 231 feature rows / 0 tagged features / 0 outcome measurements / all prediction rows pending. These are different versions of the project data. The code patch is based on the accessible source ZIP at `9ce7264`; the later `8a0c527` changes need to be reconciled/applied in the user's real workspace before calling the entire current workspace updated.

---

## 3. Engineering defects and fixes in the isolated patch

The following changes are implemented against the archived `9ce7264` source tree in an isolated temporary working copy. They have not been pushed to a connected remote repository or applied to a live Arena workspace.

| Area | Defect found | Patch / safeguard |
|---|---|---|
| Signal semantics | Snapshot-row existence was treated as usable feature coverage, despite empty tags or popularity-only rows | New `backend/app/domain/qloo_signal.py` classifies `CULTURAL_SIGNAL`, `POPULARITY_ONLY`, `IDENTITY_ONLY`, `EMPTY_SNAPSHOT`, and `INVALID_SIGNAL_SCHEMA` separately |
| Tag validation | Non-empty malformed values could be treated as signal; numeric checks could mishandle zero | Tags are shape-checked; finite affinity is treated as valid even when exactly zero; boolean/string numbers are rejected |
| Temporal feature selection | A later empty row could mask an older meaningful row; ISO timestamps with offsets were not guaranteed to compare chronologically | Shared UTC-normalized selector ignores invalid timestamps and allows latest meaningful pre-cutoff row to be selected |
| Popularity fallback | Prediction creation/canonicalization could fall back to `film_resolution.qloo_popularity` even when no valid time-eligible Qloo feature existed | Removed resolution-popularity fallback from prediction snapshot builder and canonicalization path |
| Frozen prediction payload | Frozen rows did not preserve the full signal payload/status/provenance | Added migration-backed fields for signal status, affinity, candidate tags, and feature provenance |
| Prediction immutability | A `PENDING` prediction row could be updated after its prediction timestamp, until an outcome was finalized | Existing rows become immutable at the prediction cutoff, even while outcome remains `PENDING` |
| Leakage audit | Audit checked feature retrieval timestamps but not whether the prediction record itself was created after its cutoff | Added `snapshot_created_after_prediction_timestamp` and invalid-temporal timestamp checks |
| Screening identity | Display-only title encoding differences created new observation IDs | Normalizes HTML entities, Unicode apostrophes/dashes, compatibility characters and whitespace; fails closed if multiple historical normalized matches exist |
| Frontend mode honesty | Several UI strings asserted “live Qloo” independent of the result's actual data mode | Backend result now carries `data_status`; UI distinguishes measured API evidence and fixture demo evidence |
| Frontend local API path | API client called `/run`, but Next.js only rewrote `/api/*` to FastAPI | Default API base changed to `/api`; external deployments can set `NEXT_PUBLIC_API_URL` |
| Frontend completion errors | If final `getRun()` failed after SSE completion, the UI could get stuck | Added stream cleanup and explicit final-fetch error handling |

### New files

- `backend/app/domain/qloo_signal.py` — shared signal classification / temporal selection rules.
- `backend/tests/test_m13_6_5_signal_integrity.py` — regression cases for tag validity, numeric signal semantics, cutoff selection, resolution-popularity fallback, cutoff immutability, duplicate title representation, and retrospective row detection.
- `backend/tests/test_m13_6_5_frontend_status.py` — proves the response includes source mode.
- `research/scripts/m13_6_5_integrity_audit.py` — read-only SQLite audit for feature substance, time safety, outcomes and normalized screening collisions.

### Not fixed / still blocked

1. The archive does not contain the later M13.6.4 `m13_6_3_feature_capture.py` collector update. The transcript states the empty-row retry guard was fixed at `8a0c527`, but I could not patch that specific collector source because it is absent from the accessible ZIP.
2. The database has no attempt ledger, so an absent feature row cannot reliably distinguish “not yet attempted”, “API request failed”, “valid empty response”, “unresolved entity”, or “skipped by policy”. Do not label all absence as a Qloo API failure.
3. Existing 96 duplicate screening groups are surfaced for manual reconciliation; the patch does not automatically merge history or rewrite labels.
4. The web-facing product flow cannot be live-verified here. The frontend dependencies are not present and offline npm installation fails because a package is missing from cache. The three live-Qloo integration tests also fail to reach the network in this environment, so they remain unverified, not code-level passes.
5. The source archive's `.env` packaging issue still needs to be fixed at the source-archive/export workflow. The patch ZIP excludes `.env`.

---

## 4. Product research and strategic decision

### 4.1 The problem is real, but it is a programming decision—not a sales forecast

The Independent Cinema Office's audience-development resources emphasize understanding existing and target audiences, involving audiences, testing approaches, and adapting over time. Their programming guidance also stresses audience involvement, inclusion, practical screening rights/formats, distributor relationships, and programme fit [S9–S12]. BFI sources provide formal audience research and industry data resources [S13–S14]. Those sources support the need for more evidence-aware programming decisions; they do not prove Adjacent improves attendance.

The product should answer:

> **“Given our recent programme, what culturally adjacent programme/event is worth testing next, and what evidence and constraints make it a defensible bet?”**

It should not answer “what does our local audience want?” as an asserted fact from cultural-affinity data.

### 4.2 Qloo is a fit for exploration and cultural adjacency

The official Qloo API is parameter-driven: calls combine entities, tags, demographics, audience and location signals with category filters. The documented API supports cross-category discovery, entity/tag lookup, locality-aware insights, demographic insight, comparison and trends [S1–S3]. Qloo describes the broader capability as cultural enrichment and connections across categories [S4–S6]. This makes Qloo useful as a *hypothesis-generation layer* when a venue lacks enough first-party history to explore non-obvious connections.

However, **cultural affinity is not ticket purchase intent**. The current DB's 208 popularity-only rows are not a defensible substitute for Qloo cultural affinity, and neither popularity nor affinity should be translated directly into a demand forecast without actual joined outcomes.

### 4.3 Competitor implications

- **CineScope** explicitly markets cinema programming analytics based on each venue's own POS ticket data, performance against its own building baseline, presales, schedules and box-office context [S18]. Adjacent cannot claim all data-driven programming analytics as unique. The stronger distinction is **cross-domain culture-led hypothesis discovery for future programming, including when the venue has limited first-party POS history**, coupled with a Test Card that lets the programmer validate the hypothesis.
- **Veezi** focuses on cinema operations: pre-loaded film catalogue, scheduling/programming, ticketing/POS and reports [S15–S16]. Adjacent should complement operational systems rather than replace scheduling or box-office tooling.
- **Eventive** combines independent-cinema/festival ticketing, pass management, audience data, marketing and reporting [S17 plus S19–S20]. Adjacent should give an operator an exportable decision brief and measurement plan, not recreate these operational systems.

The integration story is upstream: Adjacent proposes a carefully sourced experiment; the venue's existing ticketing/POS system measures the outcome.

### 4.4 Recommended product scope (deliberate narrow pivot)

**Target user:** programmer/curator at an independent or repertory cinema who wants to test a themed screening, event, cross-domain collaboration, double bill or new cultural entry point.

**Do in the MVP:**

1. Ingest the venue/city and recent films, with explicit unresolved titles and manual correction.
2. Show what actually resolved and which signals came from which Qloo call.
3. Explore cross-domain cultural associations without labelling an entity group as a guaranteed audience segment.
4. Turn one association into a specific programming hypothesis (e.g., film + contextual event format), with the evidence chain and counter-hypothesis.
5. Gate on what is known vs unknown: screening rights, available format, running time, distributor, budget, staffing, schedule/capacity and location fit.
6. Create a Test Card with target audience hypothesis, primary measure, observation window, competing explanation, stop/falsification condition, and outcome-capture fields.
7. Export the card and preserve source IDs, timestamps, query configuration, and explicit live/demo status.

**Do not claim/build yet:** attendance prediction, revenue lift prediction, ML ranking trained on current data, demographic stereotyping, automatic rights-clearance, or automatic merging of historical screening/outcome records.

---

## 5. The golden path and trustworthy output contract

### Proposed user journey

1. **Programme intake** — venue, city, 3–10 recent titles, optional year/identifier, stated programming goal.
2. **Resolution review** — show match certainty/ambiguity and let the programmer correct a bad match before proceeding.
3. **Taste evidence** — show returned Qloo tags/affinities only when present; list empty, failed, unresolved and skipped states separately.
4. **Cross-domain discovery** — explore relevant categories. Every result carries a Qloo entity ID, source call ID, actual affinity/popularity fields, retrieval timestamp and any available explainability. Do not synthesize absent scores.
5. **Programming translation** — connect the strongest justified association to a plausible screening/event format. The domain association is evidence; the suggested event is a hypothesis.
6. **Feasibility gate** — known / unknown / blocked status for rights, format, date, cost, capacity and team workload.
7. **Programme Bet** — hypothesis, primary evidence, why now, alternative direction and explicit falsification condition.
8. **Test Card + export** — measure a predefined outcome rather than silently collecting only sold-out statuses.
9. **Outcome review** — join ticketing and attendance data through a stable screening ID, preserving source/observation time and capacity.

### Output rules

- Distinguish **feature row exists**, **usable numerical metadata exists**, and **cultural signal exists**.
- A valid cultural signal in this patch means a non-empty schema-valid tag list or finite affinity; popularity is shown separately as `POPULARITY_ONLY`.
- A snapshot with empty tags is not successful “feature coverage”. API failure, valid empty response and unresolved entity must not be conflated.
- Every score must cite its actual query/call and timestamp. If no score is returned, render “not available”, not `0` and not a model guess.
- Sold out means sold out observed, not exact admissions. “Not sold out” is not automatically a negative-demand label.
- A retrospective reconstruction must be labelled retrospective. It must not be described as a live prediction recorded at that historical cutoff.
- A demo/fixture must be visibly labelled; do not put “live Qloo” in the footer if mode is not measured.

---

## 6. Data quality and model-readiness gate

### Why the model gate fails

The available evidence fails independently on signal coverage, outcome class balance, target semantics, provenance and prospectivity. In the transcript's later state, the reported 11 outcomes are all positive sold-out proxies and zero outcome-linked predictions have usable prediction-time signal. In the accessible ZIP state, the `outcome_measurement` table is empty, all 2,175 prediction rows are pending, and 90 prediction records were actually created after their supposed prediction timestamp. Neither data state supports supervised evaluation.

### Requirements before reopening modelling

1. Use a proper screening/event key and deterministic joins from schedule → prediction snapshot → ticketing/attendance outcome. Audit collisions before any training.
2. Store real outcome measurements separately: tickets sold, capacity, occupancy/admissions, timestamp, provenance, source, and label quality when available. Keep sold-out observation as a proxy, not attendance.
3. Establish a genuine prospective cohort: prediction row exists by its cutoff, feature retrieval timestamp is no later than the cutoff, and its feature payload is frozen at that time.
4. Track collection attempts, including request success/failure, valid empty response, entity resolution, retrieval time, and response schema. Don’t let an empty result block retry forever; don’t overwrite history.
5. Need more than one label class, enough joined examples, and enough actual non-empty cultural signal to compare a baseline against a signal-aware ranking in a held-out time split.
6. Report coverage per denominator and horizon, with explicit counts for unresolved/empty/error/metadata-only/cultural-signal/late rows. Never compress these into one headline percentage.

**Until those gates pass, do not train XGBoost, learn-to-rank, or any other supervised model.** Deterministic evidence ranking and controlled programmer feedback are the sensible next steps.

---

## 7. Verification results

### Backend

- **123 targeted tests passed** across the new M13.6.5 tests and the M13.6 / M13.4 / M13.5 regression suites after adding source-status and timestamp-integrity checks.
- **Final full backend suite (excluding three live-network tests): 431 passed, 4 skipped, 3 deselected** in 11.80 seconds. The deselected tests are `test_live_search_resolves_known_films`, `test_live_filter_results_entities_contract`, and `test_live_explainability_provenance`; outbound DNS/network access failed in this environment, so those live-Qloo paths remain unverified.
- Python compilation passed for the edited backend modules and research scripts. `git diff --check` passed after the final source edits.
- The archived DB audit completed read-only; the recorded source DB was not migrated or modified.

### Frontend

- The default API URL now matches the existing Next.js `/api/*` rewrite.
- Result source mode is available from the backend and shown in the frontend without assuming a fixture is live Qloo.
- Completion and final-run-fetch error paths were tightened.
- **Next.js build/typecheck not verified.** The frontend's `node_modules` are absent; `npm ci --offline` failed because the lockfile's `undici-types` tarball was not in local cache. There was no network install or build, and no Qloo request was attempted.

### Workspace / packaging

- Original source archive's uncompressed repo was about 94 MB, below the reported 120,000,000-byte ceiling. The patch package contains only changed/new files and excludes the database, Git history and `.env`.
- The user should reconcile this patch with the later M13.6.4 `8a0c527` work in the real workspace before overwriting any of the later source files.

---

## 8. Hackathon readiness and next sequence

The official Qloo Agentic Hackathon deadline is **30 October 2026, 11:45 p.m. EDT**. Rules require a working Qloo-integrated application that runs as shown, a functional demo, a public repository and a visible open-source licence. The four second-stage criteria are equally weighted: Technological Implementation, Design, Potential Impact and Quality of the Idea [S7–S8]. The UI alone is not a submission; a live, stable and truthful journey is required.

| Priority | Next milestone | Acceptance conditions |
|---|---|---|
| P0 | Reconcile source versions + secret cleanup | Rebase the patch onto current M13.6.4 source; re-run audit; remove `.env` from packaging and rotate key if exposed |
| P0 | Signal integrity & outcome capture | Counts reconcile; signal states distinct; no resolution-popularity fallback; cutoff immutability proven; duplicates reviewed; outcome join documented |
| P0 | Golden path live + truthful fixture fallback | One input completes through Test Card; live/error/empty/unresolved states render accurately; every result has source provenance; UI build succeeds |
| P1 | Programme feasibility | Rights/format/availability/cost fields marked known/unknown/blocked; recommendations do not overclaim local demand |
| P1 | Practitioner validation | 3–5 programmer/operator conversations; record actual statements separately from product inference; revise scope based on evidence |
| P1 | Pilot measurement | Predeclare outcome, observation window, capacity/ticket source, baseline and falsification condition |
| P2 | Submission package | Public repository, license visible in repository About, hosted demo, resettable sample scenario, short walkthrough, architecture/data-provenance note, limitations, verified setup instructions |

### Suggested two-minute demonstration

1. Enter a venue/city and 5–6 representative programme titles.
2. Show resolution of each title and explicitly call out any unresolved or ambiguous item.
3. Show one non-obvious cross-domain cultural link from an actual Qloo response with query/source provenance.
4. Turn it into one programme idea plus a runner-up and explain the evidence and uncertainty.
5. Pass the idea through the feasibility checklist.
6. Produce a Test Card with a measurable success condition and falsification condition.
7. Close by showing how a real screening/ticketing outcome would be captured and why Adjacent is not claiming to predict attendance.

---

## 9. Source list

The following are public sources checked for the product and hackathon review. The product/engineering metrics in Sections 2 and 7 come from the supplied project materials or the local source/database audit, not from these external web pages.

- **[S1] Qloo, Insights API overview** — API is parameter-driven; lists recommendations, demographic insights, location and supporting lookup/trend APIs. https://github.com/qloo/docs-public/blob/main/reference/api-overview.md
- **[S2] Qloo, Insights API deep dive** — filters, cross-category entity types, location filters and tag/interest parameters. https://github.com/qloo/docs-public/blob/main/reference/insights-api-deep-dive.md
- **[S3] Qloo public API documentation** — API reference and use case guide index. https://github.com/qloo/docs-public
- **[S4] Qloo, Capabilities** — cultural enrichment, taste intelligence, cross-domain discovery and locality intelligence. https://www.qloo.com/capabilities
- **[S5] Qloo, Recommendations** — recommendation/personalization capability examples. https://www.qloo.com/capabilities/recommendations
- **[S6] Qloo, Audience Intelligence** — audience-intelligence positioning and use cases. https://www.qloo.com/capabilities/audience-intelligence
- **[S7] Qloo Agentic Hackathon, official rules** — submission requirements, eligibility and judging weights. https://qloo.devpost.com/rules
- **[S8] Qloo Agentic Hackathon, Devpost home** — deadline and judging criteria. https://qloo.devpost.com/
- **[S9] Independent Cinema Office, How to develop audiences for independent cinemas** — current/target audiences, testing and adapting strategies. https://www.independentcinemaoffice.org.uk/advice-support/how-to-develop-audiences-for-independent-cinemas/
- **[S10] Independent Cinema Office, Understanding audiences** — audience diversity and avoiding simple audience stereotypes. https://www.independentcinemaoffice.org.uk/advice-support/how-to-start-a-cinema/understanding-audiences/
- **[S11] Independent Cinema Office, Programming community cinema** — audience involvement, diversity/inclusion and programme feedback. https://www.independentcinemaoffice.org.uk/advice-support/screening-films-in-community-cinemas/programming/
- **[S12] Independent Cinema Office, Introductory guide to programming** — booking rights/formats, distributor and repertory-programming constraints. https://www.independentcinemaoffice.org.uk/advice-support/programming-2/
- **[S13] British Film Institute, Industry data and insights** — industry research, statistics and market intelligence. https://www.bfi.org.uk/industry-data-insights
- **[S14] British Film Institute, Audiences research** — published research on engagement with cinema, streaming and broadcast. https://www.bfi.org.uk/industry-data-insights/reports/audiences
- **[S15] Veezi, Film Programming** — film catalogue and screening schedule operations. https://veezi.com/features/film-programming
- **[S16] Veezi, Reporting** — box-office, operational, marketing and loyalty reporting. https://www.veezi.com/features/reporting
- **[S17] Eventive, independent cinema platform** — ticketing, passes, audience data, marketing, streaming and reports. https://eventive.org/
- **[S18] CineScope, Programming Analytics** — POS-based film-performance benchmarking, scheduling, presales and programming analysis. https://cinescope.org/programming
- **[S19] Eventive for Film Festivals** — integrated ticketing, member management, audience data and film guide. https://eventive.org/film-festivals
- **[S20] Eventive for Arthouse Cinemas** — programming support and note that event platform does not grant screening-rights approval. https://help.eventive.org/en/articles/4924819-eventive-for-arthouse-cinemas

---

## 10. Bottom line

Keep Adjacent, but keep the claim narrow. Its advantage can be the bridge from Qloo cultural adjacency to a programmer's **testable and operationally feasible decision**, not a claim that cultural affinity predicts ticket sales. The archive currently proves implementation work, not product impact. Fix signal lineage, reconcile the M13.6.4 branch, validate one complete live journey, and collect practitioner/outcome evidence before expanding architecture or training models.
