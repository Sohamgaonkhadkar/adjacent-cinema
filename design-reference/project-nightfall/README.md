# Project Nightfall — Frontend Design Reference

This folder contains the original Project Nightfall Vite/React prototype archive for the Cultural Multiverse / Positioning Arena redesign of Adjacent Cinema.

## Verified archive

The original ZIP is present in this repository at:

`design-reference/project-nightfall/archives/project-nightfall-frontend-reimagination (1).zip`

It was merged into `main` in commit `17e52aef46ebce3dc6a262da5868518710065829`. Fetch the file from the repository and run an archive integrity test before extraction. Preserve the original archive; do not recreate it from snippets or replace it with a generated approximation.

## Required use

Read and port the actual source from the ZIP, especially:
- `src/App.tsx` and `src/index.css`
- `src/pages/Home.tsx`, `src/pages/Creator.tsx`, `src/pages/Cinema.tsx`, and `src/pages/Sponsor.tsx`
- `src/components/Nav.tsx`, `src/components/Multiverse.tsx`, `src/components/PositioningArena.tsx`, `src/components/CulturalFingerprint.tsx`, `src/components/TestCard.tsx`, and related components/utilities.

The objective is a genuine page-by-page visual and interaction port into the existing Next.js application, not only a homepage update or a standalone demo.

## Design and feature inventory

- Homepage Cultural Multiverse preview
- Positioning Arena between Cultural Fingerprint and Decision Brief in Creator Studio
- Three positioning lenses: Anchor, Bridge, and Frontier
- What-If Lab with suggested vs. selected strategy and preview-only application
- Evidence Challenge, a Positioning/Decision Brief, and Freeze Decision
- Seven-stage Creator journey
- Five Cinema Mode chapters: Cinema, Programme, Cultural field, Opportunity, Test
- Eight-stage FilmSponsor workflow
- Explicit illustrative-data / not-live-Qloo labels

## Production integration rules

The prototype is a standalone Vite/React app. The existing product uses Next.js App Router and established backend contracts. Port/adapt its visuals, component hierarchy, and interactions into the existing application; **do not replace the production app with Vite, its hash router, localStorage model, or mock API behavior.**

Preserve `frontend/lib/api.ts`, `frontend/types/adjacent.ts`, existing backend integration, real analysis context, experiment lifecycle, and FilmSponsor source-review/approval requirements. Never invent Qloo evidence, scores, audience outcomes, experiments, observations, or success states. Clearly distinguish measured/live, fixture, concept preview, and blocked states.

## Existing routes to redesign and preserve

- `/`
- `/creator`
- `/cinema`
- `/creator/sponsor`

The Multiverse must be easy to find on Home. Creator must show one Positioning Arena for a completed real or explicitly labelled fixture run, and `/creator?demo=fixture` must be tested. Empty states must explain how to view the feature without pretending an analysis has completed.

## Active follow-up task

See [issue #15](https://github.com/Sohamgaonkhadkar/adjacent-cinema/issues/15). The work branch is `arena/nightfall-full-frontend-port`. Compare the actual extracted ZIP with rendered Next.js pages at desktop and mobile sizes; green build/test results alone do not establish visual fidelity.

Do not merge the follow-up implementation PR or deploy to production until visual acceptance and relevant frontend/backend tests pass.
