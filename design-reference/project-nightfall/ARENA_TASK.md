# Arena Task — Faithful Project Nightfall Frontend Port

**Current work branch:** `arena/nightfall-full-frontend-port`

**Task:** [GitHub issue #15](https://github.com/Sohamgaonkhadkar/adjacent-cinema/issues/15)

The original ZIP is already committed to `main` and the current working branch. Use the actual archive:
`design-reference/project-nightfall/archives/project-nightfall-frontend-reimagination (1).zip`

Do not ask the owner to upload the ZIP again, and do not merge the handoff or first-implementation PRs again. They are already merged.

## 1. Inspect and port the reference code

Integrity-test the archive, extract it to a temporary directory, and inspect its real source. Important paths:
- `src/App.tsx`, `src/index.css`
- `src/pages/Home.tsx`, `src/pages/Creator.tsx`, `src/pages/Cinema.tsx`, `src/pages/Sponsor.tsx`
- `src/components/Nav.tsx`, `src/components/Multiverse.tsx`, `src/components/PositioningArena.tsx`, `src/components/CulturalFingerprint.tsx`, `src/components/TestCard.tsx`, plus related components/data/utilities.

Port their actual component composition, layouts, styling, and interactions into the existing Next.js App Router product. Do not merely recolor old pages, create a separate Vite website, or copy prototype mock API/localStorage behavior into production flows.

## 2. Redesign all four routes visibly

- **Home `/`:** faithful Nightfall layout and an easy-to-find Multiverse preview/CTA.
- **Creator `/creator`:** seven-stage journey—Your film, Investigation, Cultural Fingerprint, Positioning Arena, Decision Brief, Test Card, Archive—with real intake/run/evidence context.
- **Cinema `/cinema`:** match ZIP composition while preserving Cinema, Programme, Cultural field, Opportunity, and Test.
- **FilmSponsor `/creator/sponsor`:** match ZIP composition while preserving Intake, Discovery, Evidence, Draft, Review, Approval, Export, and Outreach.

Make the typography, colors, spacing, grid, cards, navigation, image treatments, headers, and responsive behaviors consistent across the entire product, not just the homepage.

## 3. Ensure Cultural Multiverse is discoverable and works

- Home preview is visible without running an analysis; label it as concept/illustrative.
- Creator shows exactly one Positioning Arena instance for the completed current run.
- Verify `/creator?demo=fixture` starts a labelled fixture run and reveals the Arena once completed.
- Before a run, show a clear empty/instructional state and a fixture-demo action.
- Keep fixture/demo, measured/live Qloo, unknown, and blocked states distinct.
- Preserve ANCHOR, BRIDGE, FRONTIER, What-If Lab, Evidence Challenge, Decision Brief, and validated Freeze Decision behavior.
- No fake evidence, audience predictions, provider results, saved records, or success states.

## 4. Preserve backend and existing product behavior

Inspect and preserve the real API adapter, types, endpoints, persistence, Test Card edit/export, experiment/observation/evaluation lifecycle, Qloo provenance, Cinema workflow, and FilmSponsor approval/source-review rules. Implement backend changes if required for real functionality, following existing patterns and adding tests. Keep secrets server-side.

## 5. Visual acceptance and testing are mandatory

Compare the extracted source with the actual rendered Next.js preview on desktop and mobile for each of the four routes. Inspect screenshots/pages and fix concrete differences. Do not claim the pages match the ZIP solely because tests pass.

Run frontend typecheck, lint, all relevant tests, production build, route/render checks, backend Python 3.12 lifecycle tests, container build, and `git diff --check`. Report exactly which checks passed or remain blocked; fixture tests do not prove live Qloo behavior.

## 6. Deliverables and safety

Commit and push implementation changes on `arena/nightfall-full-frontend-port`. Open a new **draft PR into `main`**. Provide the latest READY preview URL and a route-by-route visual acceptance report.

Do not merge this follow-up PR, deploy to production, change production secrets, replace Next.js with Vite, force-push, or discard unrelated changes.

**Done means:** all four existing pages visibly and substantially match Project Nightfall, the Multiverse is easy to find and opens through the fixture-demo path, and real backend workflows still work.
