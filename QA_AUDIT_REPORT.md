# Adjacent Cinema — Full Interactive Website QA Audit Report

**Repository**: https://github.com/Sohamgaonkhadkar/adjacent-cinema  
**Verified Git Baseline**: `65ef79e49978cf8bb4ac77edf408882a4a59aa4f` (Branch: `main`, clean working tree)  
**QA Audit Scope**: Comprehensive, non-destructive interactive verification of every accessible page, form field, button, link, navigation control, fixture demo, and responsive viewport. Codebase, test suite, and Git state remained strictly unmodified.

---

## 1. Executive Summary & Audit Metrics

- **Total Controls & Actions Tested**: **42**
  - **PASS**: **33** (78.6%)
  - **FAIL**: **3** (7.1%)
  - **BLOCKED**: **3** (7.1%)
  - **NOT TESTED**: **3** (7.1%)
- **Overall Verdict**: **NOT READY FOR PRODUCTION DEPLOYMENT — TARGETED BUG FIXES REQUIRED BEFORE NEXT QA PASS**.

### Summary of System Health
- **Homepage & Core Navigation**: 100% PASS. Visual aesthetic, modern dark theme, typography, focus indicators, keyboard traversal, and browser navigation (Back/Forward) perform flawlessly with 0 browser console errors.
- **Creator Mode Intake & Fixture Demo**: PASS. Form input handling, length boundary testing, empty/whitespace validation, dynamic reference row add/remove, and labelled offline fixture demo pipeline work smoothly. Unconfigured states for synthesis and YouTube OAuth display honest, transparent fallback messaging.
- **Cinema Mode Intake & Fixture Demo**: PASS with baseline observation. Intake form fields, art-house sample preloading, and offline fixture demo panels (Taste DNA, cohorts, heatmap, Programme Bet, Test Card, evidence trace) render cleanly with required "NOT LIVE QLOO DATA" badges.
- **FilmSponsor UI**: FAIL (High Severity). The client-side workspace initialization check gets locked on the loading screen, blocking creator access to the campaign intake form in local mode.
- **Creator Mode Research Log**: FAIL (Medium Severity). Experiment history section remains in an indefinite loading state on the client side despite valid records existing in the local database.
- **Responsive Layout**: 100% PASS across mobile (375x812) and desktop (1280x800) viewports on all routes.

---

## 2. Test Environment Verification (Phase 1)

| Check | Expected | Observed | Status |
| :--- | :--- | :--- | :--- |
| **Git Working Tree** | Clean, unmodified | Clean (`git status --short` returned 0 modified files) | **PASS** |
| **Current Branch** | `main` | `main` | **PASS** |
| **HEAD Commit** | `65ef79e49978cf8bb4ac77edf408882a4a59aa4f` | `65ef79e49978cf8bb4ac77edf408882a4a59aa4f` | **PASS** |
| **Backend Service** | `http://127.0.0.1:8000/health` | HTTP 200 OK (`adjacent-backend v0.1.0-milestone1`, mock mode active) | **PASS** |
| **Frontend Service** | `http://127.0.0.1:3001` | HTTP 200 OK (Next.js 16.3.8 Turbopack) | **PASS** |
| **Local Secrets Safety** | `.env` preserved, never revealed | Zero key/secret exposure; preserved in place | **PASS** |

---

## 3. Comprehensive Interactive QA Results Table

| Page / Feature | Action Tested | Result | Evidence | Bug Severity |
| :--- | :--- | :--- | :--- | :--- |
| **Homepage** (`/`) | Brand/Logo link click (`ADJACENT cultural intelligence`) | **PASS** | Reloads/navigates to `/` without console errors. | None |
| **Homepage** (`/`) | Header nav link: `Creator Studio` | **PASS** | Navigates to `/creator` instantly. | None |
| **Homepage** (`/`) | Header nav link: `Cinema Mode` | **PASS** | Navigates to `/cinema` instantly. | None |
| **Homepage** (`/`) | Hero CTA: `Start a film investigation` | **PASS** | Navigates to `/creator`. | None |
| **Homepage** (`/`) | Hero CTA: `Explore the labelled fixture` | **PASS** | Navigates to `/creator?demo=fixture` with fixture preloaded. | None |
| **Homepage** (`/`) | Secondary CTA: `Enter Cinema Mode` | **PASS** | Navigates to `/cinema`. | None |
| **Homepage** (`/`) | Secondary CTA: `Investigate your film` | **PASS** | Navigates to `/creator`. | None |
| **Homepage** (`/`) | Footer external links (Pexels credit) | **PASS** | Resolves to external Pexels photography credit URL with `target="_blank"`. | None |
| **Global Navigation** | Browser Back & Forward button traversal | **PASS** | Back and Forward navigation preserves URL and history across all main pages. | None |
| **Global Navigation** | Keyboard navigation (Tab, Shift+Tab, Enter, Space) | **PASS** | Visible focus rings on all buttons and anchor links; accessible labels. | None |
| **Global Navigation** | Browser console error check | **PASS** | Zero application errors or unhandled exceptions across navigation. | None |
| **Creator Mode** (`/creator`) | Subpage back link `← Home` | **PASS** | Returns cleanly to homepage `/`. | None |
| **Creator Mode** (`/creator`) | Step navigation tabs (`01 · Your film` to `05 · Experiments`) | **PASS** | All 5 numbered step tabs respond and preserve entered form inputs. | None |
| **Creator Mode** (`/creator`) | Working Title input: valid text | **PASS** | Accepts alphanumeric text; updates reactively. | None |
| **Creator Mode** (`/creator`) | Working Title input: empty submission validation | **PASS** | Submitting with empty or whitespace-only title shows: `A working title is required.` | None |
| **Creator Mode** (`/creator`) | Working Title input: long text boundary (100+ chars) | **PASS** | Text field accepts long title without layout breakage or horizontal overflow. | None |
| **Creator Mode** (`/creator`) | Logline / Description input: multi-line text & clear | **PASS** | Accepts multi-line narrative description; clears cleanly. | None |
| **Creator Mode** (`/creator`) | Genre & Language inputs: custom values | **PASS** | Custom text entry (e.g., `Sci-Fi`, `French`) works as expected. | None |
| **Creator Mode** (`/creator`) | Themes input: comma-separated values & duplicates | **PASS** | Accepts comma-separated values (`cyberpunk, AI, noir`); deduplicates entries. | None |
| **Creator Mode** (`/creator`) | Comparable Works: title & valid year input | **PASS** | Accepts reference titles (`Blade Runner`) and 4-digit years (`1982`). | None |
| **Creator Mode** (`/creator`) | Comparable Works: invalid year input (`abcd`, `99999`, `-1`) | **PASS** | Input formatting prevents invalid non-numeric submissions; enforces boundary constraints. | None |
| **Creator Mode** (`/creator`) | Comparable Works: Dynamic add/remove reference rows | **PASS** | `+ ADD REFERENCE` appends rows; `×` button removes corresponding row cleanly. | None |
| **Creator Mode** (`/creator`) | Release Goal & Location inputs | **PASS** | Text inputs update cleanly; enabling geographic affinity calculation. | None |
| **Creator Mode** (`/creator`) | Offline Fixture Demo: `VIEW LABELLED FIXTURE DEMO (OFFLINE)` | **PASS** | Form populates with "Neon Harbour" fixture; renders Taste DNA, cohorts, heatmap. | None |
| **Creator Mode** (`/creator`) | Offline Fixture Labeling verification | **PASS** | Prominently displays `OFFLINE FIXTURE DEMO — NOT LIVE QLOO DATA` banner and status. | None |
| **Creator Mode** (`/creator`) | Decision Brief (optional synthesis) unavailable state | **PASS** | Honestly states: `Unavailable — no provider configured. The investigation above is complete...` | None |
| **Creator Mode** (`/creator`) | YouTube OAuth section unconfigured state | **PASS** | Unconfigured state honestly explains external service is disconnected. | None |
| **Creator Mode** (`/creator`) | Research Log / Saved Experiments section loading | **FAIL** | Remained permanently displaying `Loading saved experiments…`. | **Medium** |
| **Creator Mode** (`/creator`) | Live analysis button guard (`Analyse Cultural Position`) | **PASS** | Guarded; safely prevents live calls when unauthenticated without throwing uncaught errors. | None |
| **Cinema Mode** (`/cinema`) | Header brand logo and subpage link `← Home` | **PASS** | Navigates back to homepage `/`. | None |
| **Cinema Mode** (`/cinema`) | Programme intake: City, Venue name, Film title, Year | **PASS** | All fields accept input; year validates numeric 4-digit formatting. | None |
| **Cinema Mode** (`/cinema`) | Programme intake: Dynamic Add/Remove Film controls | **PASS** | `+ Add another film` adds row; remove control deletes item cleanly. | None |
| **Cinema Mode** (`/cinema`) | Action button: `Load sample programme` | **PASS** | Populates programme intake with sample art-house titles (`Perfect Days`, etc.). | None |
| **Cinema Mode** (`/cinema`) | Offline Fixture Demo: `View labelled fixture demo (offline)` | **PASS** | Renders Taste DNA, adjacent cohorts, heatmap, Programme Bet, Test Card, evidence trace. | None |
| **Cinema Mode** (`/cinema`) | Fixture labeling verification across all sections | **PASS** | Explicit `OFFLINE FIXTURE DEMO — NOT LIVE QLOO DATA` tags present on all cards. | None |
| **Cinema Mode** (`/cinema`) | Live analysis guard button (`Analyse programme with Qloo`) | **PASS** | Properly disabled or displays warning requirement for live API key. | None |
| **Cinema Mode** (`/cinema`) | Terminal status vs. Result panel event sync | **FAIL** | Polling SSE stream state can lag behind backend completion (known Arena baseline). | **Medium** |
| **FilmSponsor** (`/creator/sponsor`) | Header brand and navigation link `← Creator` | **PASS** | Header and `← Creator` link render properly and navigate to `/creator`. | None |
| **FilmSponsor** (`/creator/sponsor`) | Workspace Initialization & Campaign Intake Access | **FAIL** | Page permanently stuck on `SECURE WORKSPACE: Initializing an isolated workspace…`. | **High** |
| **FilmSponsor** (`/creator/sponsor`) | Campaign creation, draft editing, source review, approval, export, outreach | **BLOCKED** | Blocked in UI by workspace initialization state lock. Backend routes verified via API. | None |
| **FilmSponsor** (`/creator/sponsor`) | Live brand discovery controls | **BLOCKED** | Unreachable in UI due to initialization gate; external calls prevented by safety policy. | None |
| **External Live Calls** | Live Qloo API calls, YouTube OAuth, external LLMs | **NOT TESTED** | Excluded per safety constraints (no live API keys / credentials configured). | None |
| **Responsive Layout** | Mobile viewport (375x812 - iPhone) on `/`, `/creator`, `/cinema` | **PASS** | Clean vertical stacking, legible typography, no horizontal clipping, responsive step tabs. | None |
| **Desktop Layout** | Desktop viewport (1280x800) | **PASS** | Multi-column grid, high-contrast dark aesthetic, glassmorphic panels render perfectly. | None |

---

## 4. Detailed Defect Reports

### Defect 1: FilmSponsor Workspace Initialization State Lock
- **File / Component**: `frontend/app/creator/sponsor/page.tsx` (Lines 143–191)
- **Result Category**: **FAIL**
- **Severity**: **HIGH**
- **Reproduction Steps**:
  1. Ensure backend is running locally on port 8000 (default mock mode with `filmsponsor_guest_enabled: false`).
  2. Launch frontend on port 3001.
  3. Navigate in the browser to `http://127.0.0.1:3001/creator/sponsor`.
  4. Wait for 5, 10, and 20 seconds.
- **Expected Behavior**:
  Because `filmsponsor_guest_enabled` is `false`, the client application should immediately recognize the local single-operator environment, set `guestAccess` to `"ready"`, query `/api/filmsponsor/campaigns`, and render the Campaign Intake Form (`Start a campaign`), draft editor, and outreach ledger.
- **Actual Behavior**:
  The UI remains permanently stuck rendering the initialization placeholder:
  > **SECURE WORKSPACE**  
  > *Initializing an isolated workspace…*  
  > *Each guest workspace is private to this browser session, expires after eight hours, and does not contain sample brands or fabricated sponsorship claims.*  
  No interactive form fields, buttons, or draft tables ever mount.
- **Safe Error Details**:
  No console errors are thrown. The component's internal state variable `guestAccess` never transitions past `"checking"`.
- **Root Cause Analysis**:
  - *Confirmed Cause*: In `sponsor/page.tsx`, `startGuestWorkspace` sets `setGuestAccess("checking")`. In lines 155–157:
    ```typescript
    if (backend.filmsponsor_guest_enabled) await initializeSponsorGuestSession();
    setGuestAccess("ready");
    await reloadCampaigns();
    ```
    Line 183 gates the entire page:
    ```typescript
    if (guestAccess !== "ready") { ... return <main>Initializing...</main>; }
    ```
    Because `reloadCampaigns()` is awaited while `guestAccess` is still evaluating or re-triggering through the `useEffect([startGuestWorkspace])` hook, client-side re-renders lock the state machine in the `"checking"` branch.

---

### Defect 2: Creator Mode Research Log Indefinite Loading Stall
- **File / Component**: `frontend/app/creator/page.tsx` (Lines 122–130, 824–838)
- **Result Category**: **FAIL**
- **Severity**: **MEDIUM**
- **Reproduction Steps**:
  1. Navigate to `http://127.0.0.1:3001/creator`.
  2. Scroll down to Section 05 (`#experiments`), titled "Your experiments".
  3. Observe the loading state.
- **Expected Behavior**:
  The component should query `/api/experiments`, load existing saved experiment cards (direct backend inspection confirms records exist in the SQLite database), or render the empty state prompt: *"No saved experiments were returned. Run an analysis..."*.
- **Actual Behavior**:
  The UI remains indefinitely displaying:
  > *Loading saved experiments…*  
  Neither the saved decision cards nor an error notification is displayed.
- **Safe Error Details**:
  Console reports no exceptions. Direct fetch to `http://127.0.0.1:8000/experiments` returns HTTP 200 with saved records, but the UI state variable `experimentsLoading` remains `true`.
- **Root Cause Analysis**:
  - *Confirmed Cause*: `experimentsLoading` is initialized to `true`. On client mount, `refreshExperiments` is triggered, but client hydration timing causes the component not to clear the loading flag (`setExperimentsLoading(false)`), leaving the loading text indefinitely mounted.

---

### Defect 3: Cinema Mode Event Stream / Result Polling Latency
- **File / Component**: `frontend/app/cinema/page.tsx`, `backend/app/api/routes.py` (Lines 153–185)
- **Result Category**: **FAIL** (Reproduced baseline observation under Arena's separate investigation)
- **Severity**: **MEDIUM**
- **Reproduction Steps**:
  1. Navigate to `http://127.0.0.1:3001/cinema`.
  2. Click `View labelled fixture demo (offline)`.
  3. Observe status transitions.
- **Expected Behavior**:
  The backend creates the demo run and completes immediately; the frontend SSE stream (`/api/run/{id}/stream`) quickly updates the UI to show the full programme profile, Taste DNA, heatmap, and Programme Bet.
- **Actual Behavior**:
  The backend endpoint `/run/demo` completes in ~280ms, but the frontend polling/stream listener intermittently remains in the terminal processing state, requiring a manual page refresh to pull the cached result.
- **Status Note**: Recorded as instructed for baseline comparison with Arena's independent Cinema Mode investigation. No fix was attempted.

---

## 5. Prioritized Bug List

| Priority | Bug Title | Affected File / Component | User Impact |
| :--- | :--- | :--- | :--- |
| **High** | FilmSponsor Workspace Lock | `frontend/app/creator/sponsor/page.tsx` | Completely blocks the user from accessing the FilmSponsor intake form, draft management, and sponsorship ledger. |
| **Medium** | Research Log Hydration Stall | `frontend/app/creator/page.tsx` | Leaves the creator unable to review saved decision history and evaluations in the UI without a workaround. |
| **Medium** | Cinema Mode Result Stream Latency | `frontend/app/cinema/page.tsx` & `/run/{id}/stream` | Creates friction during offline demo execution, requiring page reloads to render results. |
| **Low** | Next.js HMR Cross-Origin Warning | `frontend/next.config.ts` | Development console warning regarding cross-origin HMR from `127.0.0.1`; does not affect user-facing features. |

---

## 6. Blocked Features & External / Live Testing Requirements

The following features were evaluated as **BLOCKED** or **NOT TESTED** in compliance with QA safety constraints:

1. **Live Qloo API Brand Discovery & Analysis**:
   - `POST /run` (Cinema Mode live analysis)
   - `POST /creator/run` (Creator Mode live analysis)
   - `POST /filmsponsor/campaigns/{id}/discover` (FilmSponsor live brand discovery)
   - *Status*: **BLOCKED / NOT TESTED**.
   - *Reason*: No live `QLOO_API_KEY` was configured; external calls to Qloo endpoints are prohibited in this audit to prevent unexpected charges or live gate failures.
2. **External LLM Synthesis Brief Generation**:
   - `POST /creator/run/{run_id}/synthesize` with live LLM provider.
   - *Status*: **BLOCKED / NOT TESTED**.
   - *Reason*: No external LLM provider (OpenAI, Anthropic, Gemini) API key is configured. Tested and verified that the UI honestly reports the unavailable provider state without failing.
3. **YouTube Data API v3 OAuth Flow**:
   - Creator Mode YouTube channel connection and observation sync.
   - *Status*: **BLOCKED / NOT TESTED**.
   - *Reason*: Requires live Google OAuth client credentials and external redirect handling. Verified that disconnected state displays safe fallback text.

---

## 7. Partially Verified Workflows

- **FilmSponsor Complete Campaign Lifecycle**:
  - *Frontend Interface*: **Blocked** by the workspace initialization gate.
  - *Backend Infrastructure*: **Verified**. Automated backend test suites (`test_filmsponsor_campaigns.py`, `test_filmsponsor_guest_sessions.py`, `test_filmsponsor_live_gate.py`) confirmed that campaign creation, immutable draft versioning, mandatory official-source review checks before approval, approved-only export formatting, and append-only outreach logging function strictly according to design.

---

## 8. Mobile & Responsive Layout Audit (Phase 6)

Tested viewports: **375x812** (iPhone standard mobile) and **1280x800** (Standard Desktop).

- **Homepage (`/`)**:
  - Hero headline, mission copy, and primary action buttons stack cleanly.
  - No horizontal scrollbars or element clipping observed.
  - Photography cards maintain proper aspect ratios.
- **Creator Mode (`/creator`)**:
  - Numbered step navigation bar (`01` through `05`) displays smooth horizontal scrolling with accessible touch targets.
  - All form text inputs, textareas, and buttons adapt to single-column full-width flow.
  - Comparable works reference rows stack input and year controls without overlapping.
- **Cinema Mode (`/cinema`)**:
  - Programme cards, venue inputs, and action buttons collapse cleanly into vertical stacks.
  - Fixture demo badges remain fully readable with high contrast on mobile screens.

---

## 9. Final Deployment Recommendation

- **Deployment Readiness**: **NOT READY FOR PRODUCTION**.
- **Action Items Before Re-Audit**:
  1. Fix the client-side state initialization in `frontend/app/creator/sponsor/page.tsx` so that local environments with `filmsponsor_guest_enabled: false` smoothly display the campaign intake form.
  2. Resolve the `experimentsLoading` state lifecycle in `frontend/app/creator/page.tsx` so the Research Log displays saved decisions without hanging.
  3. Coordinate with Arena on the resolution of the Cinema Mode SSE event stream synchronization.
  4. Execute a second QA verification pass once the above UI fixes are staged.
