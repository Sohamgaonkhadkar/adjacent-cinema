# Adjacent M13.6.6 — Product-Locked Frontend Integration + M13.6.5 Reconciliation

**Priority:** P0. Execute in the latest Adjacent workspace; do not stop at a plan.

## 0. NON-NEGOTIABLE: preserve the original Adjacent idea

This task is a **frontend source correction and engineering reconciliation**, not a product pivot.

**Adjacent's original product remains:** a Qloo-powered cultural-intelligence decision agent for independent and repertory cinema programmers. It helps a programmer discover and justify non-obvious cultural programming hypotheses from a venue's location/context and recent programme, then turn a promising direction into a feasible, explainable programming experiment and a measurable Test Card.

The core journey remains:

1. Programmer gives cinema/venue context, city or area, and a small set of recent/relevant films.
2. Resolve films and cultural entities safely.
3. Query Qloo's real cultural-intelligence API and preserve response provenance.
4. Discover cross-domain cultural relationships and candidate programming opportunities.
5. Validate signal quality, explain why each opportunity appears, and assess geographic/practical feasibility.
6. Produce a specific, actionable **Programme Bet** and a **Test Card** defining the test and the outcomes to record.
7. Later, use honest, joined outcome data to learn what worked; do not claim attendance prediction before the data supports it.

**Do not pivot away from this concept.** Do not turn Adjacent into SUTRA, a geocoder, a survey/field-evidence tool, a generic dashboard/chatbot, a movie recommendation list, a ticketing/POS analytics product, or an attendance-prediction model. Do not remove Qloo or replace the original user journey with a new concept. The M13.6.5 findings require stronger evidence integrity and a better end-to-end experience—not a different product idea.

The exact frontend folder below is **frontend-only**. Its purpose is to supply the intended UI/UX, components, layout, styles, assets and interactions. It is not a new product specification or backend source of truth. Use it to improve the frontend for the existing Adjacent idea.

## 1. Correct frontend-only source

**Use this Google Drive folder:**
https://drive.google.com/drive/folders/1s8DVFZwQRCEFMcXprACESkKmYZUKi5bJ?usp=drive_link

**Do not use this previous, incorrect folder as the design reference:**
https://drive.google.com/drive/folders/1dIyX8LkpH4J30QmC_jXuSB-KqbC1i_Rw

The older folder led to a SUTRA/geocoder-style interface. That was a source-selection mistake, not a reason to change Adjacent's product definition.

### Fetch and inspect the frontend source

1. Download/inspect the correct folder recursively using available authenticated access or a supported folder-download method. Record the actual commands, access result, project structure and number of files.
2. Inspect only what is actually present: framework, app entry points, routes, components, design tokens, typography, colors, layout, icons, imagery, responsive behavior, interactions, package manager/lockfile and any mock data/API code.
3. Treat the folder as a **frontend implementation/reference only**. Do not assume it contains the backend, correct API contracts, database schema, product logic or an authoritative product definition. Reuse its intended visual language and useful frontend code while adapting UI labels and flows to Adjacent's locked original journey above.
4. Map the frontend files into the current Adjacent frontend before editing. Keep existing working backend/API contracts unless a tested integration change is necessary.
5. If download/access fails, state the exact error and what was attempted. Do not fall back to the old link or invent a UI while claiming it came from the folder.
6. Do not import `.env`, secrets, `node_modules`, build outputs, caches or databases from the source folder.

## 2. Previous M13.6.5 work — reconcile, do not overwrite

The M13.6.5 isolated patch was produced against an older source ZIP at Git HEAD `9ce72640097d1b557f4871132706cb8da4f38f40`. The later Arena transcript separately reports M13.6.4 at `8a0c527`. The patch is **not proof that the latest branch is fixed** and must not be applied blindly.

Available files to inspect/use if present:
- `Adjacent_M13_6_5_Code_Patch_2026-10-09.patch`
- `Adjacent_M13_6_5_Code_Patch_2026-10-09.zip`
- `Adjacent_M13_6_5_Integrity_Product_Readiness_Report_2026-10-09.md` / `.pdf` / `.docx`
- `Adjacent_M13_6_5_Integrity_Audit_Archived_DB_2026-10-09.json`
- `Adjacent_M13_6_5_Apply_Notes_2026-10-09.md`

The patch includes signal-quality classification, temporal feature-selection safeguards, removal of retrospective resolution-popularity fallback, frozen-prediction cutoff protection, leakage tests, normalized duplicate-screening candidate detection, truthful `data_status`/live-versus-fixture labelling, and frontend API/error-handling fixes.

Reported isolated test result: **431 passed, 4 skipped, 3 live-network tests deselected**; Python compilation and `git diff --check` passed. This was not a verification of the newest Arena workspace. Live Qloo checks and frontend build/typecheck were blocked in that environment. Re-run checks on the actual latest branch.

## 3. Keep the two database states separate

Do not mix the older archived ZIP counts with counts reported from M13.6.4.

### M13.6.4 Arena-reported state (must independently re-audit current DB)
- 308 planned films; 46 unresolved; 36 with non-empty tags; 226 with empty snapshots.
- The old “94.2% feature coverage” was invalid; snapshot-row existence is not usable signal.
- Reported usable temporal signal: 165 / 2,068 predictions (7.98%).
- 11 finalized outcomes, all `SOLD_OUT_OBSERVED`; no `AVAILABLE_NEAR_SHOWTIME` negatives.
- 0 / 11 outcome-linked predictions had actual prediction-time tag signal.
- Preserve the empty-snapshot recollection fix reported in M13.6.4.

### Older archived ZIP/database state (historical only)
- 312 `canonical_film` rows, a different denominator from the 308 planned films above.
- 231 feature rows: 208 popularity-only, 23 identity-only, zero valid tags/affinity.
- 2,175 prediction rows; 328 `NO_FEATURE` rows carried popularity with no feature timestamp.
- 90 prediction records created after their stated prediction cutoff.
- 96 normalized candidate duplicate-screening groups require review.
- 0 `outcome_measurement` rows; all 2,175 predictions were pending.

First inspect and audit the actual latest workspace/database. Do not report these historical counts as current, and do not overwrite source history to make them reconcile.

## 4. Work to execute

### A. Integrate correct frontend into the original product

- Start with `git status`, current HEAD/branch, workspace bytes and database path. Preserve uncommitted work. Make a safe branch/backup.
- Inspect the Drive frontend folder and current Adjacent frontend. Build a file-level mapping of source components/assets to target components before porting.
- Preserve the correct frontend's intended visual design and interactions as far as practical. Change only the content/navigation/workflow needed to make it serve Adjacent's original product.
- Connect the frontend to the **existing real Adjacent backend** and actual API contracts. Keep fixtures only as an explicit demo fallback. Do not fake a live Qloo result.
- The main happy path must remain: cinema/programme context → film/entity resolution → Qloo cultural evidence → explainable cultural adjacency/opportunities → feasibility/geography → Programme Bet → Test Card.
- Each result must distinguish live Qloo evidence, fixture/demo, unresolved entity, empty response, request failure, popularity-only/identity-only record and late/retrospective data. Popularity alone is not cultural affinity.
- Keep the UI understandable and polished; test responsive behavior. Do not add unrelated analytics screens just because the backend contains more data.

### B. Reconcile engineering changes safely

- Compare each M13.6.5 patch hunk to current source. Apply compatible changes, adapt changed areas by hand, and document applied/adapted/skipped hunks. Preserve M13.6.4 fixes.
- Ensure the actual production prediction path selects only schema-valid cultural signal retrieved no later than the prediction cutoff. A late snapshot must never make an old prediction appear informed.
- A feature row that has empty tags, only entity identity, or only retrospective resolution popularity must not count as usable cultural evidence.
- Freeze prediction-time evidence and provenance; later collection must not rewrite it.
- Empty API response, failed request, unresolved entity, no usable signal, stale/late signal, popularity-only and identity-only are separate statuses.
- Preserve empty-snapshot re-collection behavior and append-only audit provenance.
- Detect likely duplicate screenings safely; do not automatically merge ambiguous history or equate sold-out with attendance.

### C. Security and workspace limits

- Workspace must remain under **120,000,000 bytes**. Measure before and after. Do not delete required datasets or Git history to make room.
- Use an external/ephemeral dependency/build environment if necessary.
- Exclude secrets, `.env`, credentials, `node_modules`, `.next`, build output, caches and database copies from imported UI source and deliverables.
- Scan tracked files for accidentally committed secrets. Rotate any credential that may have escaped into an untrusted archive.

## 5. Acceptance checks — verify, do not merely claim

1. Correct frontend folder accessed: report actual structure and exact files used. Confirm it was treated as frontend-only.
2. Product continuity: demonstrate the original Qloo cultural-intelligence programming journey. No product pivot or SUTRA/geocoder vocabulary.
3. Visual parity: run the application and inspect screenshots at desktop and mobile/tablet sizes; fonts/assets load and routes/interactions work.
4. Golden path: fresh session from cinema/programme context to a traceable Programme Bet and measurable Test Card.
5. Failure paths: empty Qloo response, API timeout/error, unresolved title, popularity-only row, identity-only row, late feature, fixture/demo mode, missing required input, and post-stream final-fetch failure.
6. Data integrity: test the real production cutoff-selection/frozen-prediction path, no-future-feature leakage, empty-snapshot recollection, duplicate-candidate safety and outcome leakage. Re-run a read-only audit on the current DB and state all denominators.
7. Fresh checks: exact backend test, frontend lint/typecheck/build commands and outputs. Clearly distinguish passed, failed, skipped and blocked checks; never claim a live API test passed if credentials/network prevented it.
8. ML readiness remains `NOT_READY` unless real joined labels, adequate usable prediction-time signal, positive and negative examples, and a meaningful baseline evaluation justify changing it. Sold-out-only observations do not prove attendance prediction.
9. Report the final commit hash, files changed, patch reconciliation summary, workspace bytes before/after and secret-scan outcome. Commit only after verifying the actual latest workspace.

## 6. Execution order

1. Fetch and inspect the **correct frontend-only** Drive folder.
2. Inspect the latest actual Adjacent repo and DB; record baseline.
3. Lock the existing product definition and map the UI source files into it.
4. Integrate the UI while preserving the original product and real backend.
5. Reconcile the M13.6.5 patch with current M13.6.4 changes.
6. Run current DB audit, backend/frontend tests, visual QA and failure-path checks; fix failures.
7. Check secrets and workspace size; commit only after truthful verification.

## Final report required

Return actual evidence, not a plan: folder access outcome and file structure; screenshots; exact frontend files reused; confirmation the product concept stayed unchanged; backend endpoints/contracts used; files changed; M13.6.5 hunks applied/adapted/skipped; current DB counts; exact test/build commands and results; blockers; final commit hash and workspace bytes.

**The frontend folder is a design/code source for the UI only. The original Adjacent product idea and solution remain fixed. Improve that product; do not pivot away from it.**
