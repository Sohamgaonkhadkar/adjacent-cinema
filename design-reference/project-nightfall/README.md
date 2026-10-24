# Project Nightfall — Frontend Design Reference

This directory is reserved for the standalone frontend reimagination ZIP supplied for Adjacent Cinema.

## Current status

The supplied archive was reviewed in the project-owner conversation. Its main design changes include:

- Cultural Multiverse preview on the homepage
- Positioning Arena component intended for Creator Studio
- Creator journey with seven sections
- Cinema Mode chapter navigation
- FilmSponsor eight-stage workflow
- Explicit illustrative-data labeling
- What-If Lab with a suggestion and “Apply to preview” action

**The ZIP archive itself has not been committed to this directory yet.** Do not treat this README as the actual source archive. Add the original ZIP or its extracted source files here when available.

## Important integration rule

The archive is a standalone Vite/React prototype. The production project uses Next.js App Router and existing backend API contracts. Use the prototype as a design reference and port components into the existing application. Do not replace the production app with the Vite router, local storage, or mock API behaviors.

## Integration task

See GitHub issue [#12 — Integrate Project Nightfall frontend design into existing Next.js product safely](https://github.com/Sohamgaonkhadkar/adjacent-cinema/issues/12).

The original current routes must continue to work:

- `/`
- `/creator`
- `/cinema`
- `/creator/sponsor`

The Positioning Arena is a concept preview until a real backend strategy-engine and snapshot contract exists. No fabricated Qloo evidence, strategy scores, saved experiments, observations, or success states.
