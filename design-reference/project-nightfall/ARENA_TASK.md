# Arena implementation task — Project Nightfall

**Owner instruction:** Continue the Adjacent Cinema implementation using the Project Nightfall Cultural Multiverse / Positioning Arena design as the reference. Do this as an additive port into the existing Next.js product, not as a replacement application.

## Source availability — do not assume

The prototype ZIP was inspected in the project-owner session, but the archive bytes and full extracted source tree have not been committed to this repository. The sibling README records this honestly. Do not look for or attempt to decode incomplete archive fragments. If the project owner attaches the ZIP to the Arena session, inspect its actual source and then continue. Otherwise, continue only with the grounded design/behavior inventory below and note which details could not be source-verified.

## Implement on the current production architecture

1. Inspect the current Next.js routes and existing UI before editing. Preserve the current app rather than creating a parallel Vite app.
2. Add a Cultural Multiverse preview to the homepage and add a Positioning Arena section to Creator Studio, positioned after Cultural Fingerprint and before Decision Brief.
3. Present three clearly differentiated strategic lenses:
   - **Anchor:** strongest supported direction
   - **Bridge:** evidence-backed link between cultural worlds
   - **Frontier:** more exploratory, with uncertainty shown explicitly
4. Add a What-If Lab with adjustable priorities; visibly distinguish a suggested option from the user's selected option. An “Apply” action must change preview state only, not claim a real experiment has been run.
5. Include an Evidence Challenge interaction where every displayed evidence item can be traced to actual returned source data. If no valid evidence exists, show an honest empty/blocked state.
6. Keep Freeze Decision disabled or marked preview-only until there is a real backend contract for persisted strategy snapshots and experiment linkage.
7. Keep sample concept-film content isolated from the current user's intake and current film state. Do not silently substitute the illustrative “Salt Light” sample for user input.
8. Preserve the Creator seven-stage flow, Cinema Mode chapters (Cinema, Programme, Cultural field, Opportunity, Test), and FilmSponsor eight-stage workflow and approval prerequisites.

## Backend/data rules

- Reuse `frontend/lib/api.ts` and `frontend/types/adjacent.ts`; first inspect them and the actual backend before deciding whether a new contract exists.
- Do not invent API endpoints or send browser requests directly to Render around the adapter.
- Do not put Qloo keys or other provider secrets in client code.
- Do not fabricate Qloo-backed evidence, confidence, scores, audience outcomes, experiment records, observations, exports, or success toasts.
- Distinguish **live**, **fixture**, **concept preview**, and **blocked** states clearly.
- Keep the prototype's localStorage/mock API behavior out of the real production workflows.
- Do not run a production deploy until the existing app builds and relevant flows have been validated.

## Acceptance checklist

- [ ] Existing routes `/`, `/creator`, `/cinema`, and `/creator/sponsor` continue working.
- [ ] Existing Creator Studio analysis, Test Card export/edit, archive, experiment/observation history, and YouTube status behaviors remain intact.
- [ ] Positioning Arena is visibly labeled illustrative/concept-only unless real evidence is contractually available.
- [ ] What-If controls only modify local preview state; suggested and selected strategies remain distinct.
- [ ] Freeze Decision cannot imply persisted state until persistence is implemented and tested.
- [ ] Cinema Mode navigation and FilmSponsor stage gating are preserved.
- [ ] Type-check/build/tests run successfully; report any unverified checks honestly.
- [ ] No production deployment is triggered as part of this design-reference handoff.

## Related handoff

See [README.md](./README.md) and [issue #12](https://github.com/Sohamgaonkhadkar/adjacent-cinema/issues/12). Keep PR #13 in draft until the integration and validation checklist is complete.
