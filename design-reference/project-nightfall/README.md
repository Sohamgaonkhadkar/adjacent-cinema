# Project Nightfall — Frontend Design Reference

This folder is the handoff point for the Cultural Multiverse / Positioning Arena reimagination of Adjacent Cinema.

## Archive status

The original prototype ZIP has been inspected locally, but the ZIP bytes and complete extracted source tree are **not yet present in this GitHub folder**. No incomplete base64 fragments are kept here. Do not assume a bundle is available to decode.

The project owner can attach the original archive to the implementation session. Once available, add the real ZIP or its extracted source files beneath this directory and verify the archive/source checksums before proceeding.

## What the prototype contains

- Homepage Cultural Multiverse preview
- PositioningArena component in the Creator Studio journey after Cultural Fingerprint and before Decision Brief
- Three positioning lenses: Anchor, Bridge, and Frontier
- What-If Lab with suggestion vs. selected strategy and “Apply to preview”
- Evidence Challenge and a design-only Freeze Decision preview
- Seven-stage Creator journey
- Five Cinema Mode chapters: Cinema, Programme, Cultural field, Opportunity, Test
- Eight-stage FilmSponsor workflow
- An explicit illustrative-data / not-live-Qloo status banner

## Production integration rule

The supplied ZIP is a standalone Vite/React prototype. The current production project uses Next.js App Router and established backend contracts. Port the relevant visuals and interaction patterns into the existing Next.js app; **do not replace production with the standalone Vite app, its hash router, localStorage model, or mocked API behavior.**

Keep the concept isolated from real analysis and experiments. Do not invent Qloo evidence, calculated scores, audience outcomes, saved experiments, observations, or success states. Freeze Decision must remain disabled or explicitly preview-only until an actual backend snapshot/persistence contract and experiment linkage exist.

## Existing routes and behavior to preserve

- `/`
- `/creator`
- `/cinema`
- `/creator/sponsor`

Use frontend/lib/api.ts and frontend/types/adjacent.ts for existing backend integration. Do not invent endpoints, call Render directly from browser code, or expose provider secrets in the client. Preserve Creator Studio intake/analysis/Test Card/archive workflows, Cinema context, and FilmSponsor approval prerequisites.

## Arena's active task

See [ARENA_TASK.md](./ARENA_TASK.md) and GitHub [issue #12](https://github.com/Sohamgaonkhadkar/adjacent-cinema/issues/12). The task is to port the design safely into the existing application and run checks before any production deployment.

## Validation

The standalone prototype build was not verified in this handoff. Run repository tests/type checks and inspect the updated pages before merging or deploying. The design handoff PR remains a draft until the implementation and checks are complete.
