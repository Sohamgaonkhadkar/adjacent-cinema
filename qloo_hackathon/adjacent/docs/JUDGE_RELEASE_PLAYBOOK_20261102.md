# Adjacent Cinema — judge demo and release gate (2 November 2026)

**Use only observed claims.** The project delivers an end-to-end **Creator Studio → Cinema Mode → FilmSponsor** decision-support journey, with source-labeled Qloo signals, bounded agent operations, explainability, human review, and experiments. An independently generated live Qloo scoring study on 2 November measured 12/12 shared movies and found a different winner from a metadata heuristic; it **did not prove better recommendations or business lift**.

## 90-second judge route

1. **0–10s · Opening:** Open [Adjacent Cinema](https://adjacent-cinema.vercel.app/). Explain: *"Independent cinemas and filmmakers need defensible cultural adjacency decisions, not another chatbot recommendation."* The home screen has explicit Creator and Cinema demo entry points.
2. **10–35s · Creator Studio:** Choose **Creator demo · fixture**, which links to `/creator?demo=fixture`. The sample is labelled **fixture / not live Qloo**. Move from the Cultural Fingerprint through ANCHOR/BRIDGE/FRONTIER positioning, inspect supporting evidence and missing information, then show the proposed Test Card with a falsifiable decision.
3. **35–60s · Cinema Mode:** Choose **Cinema demo · fixture** at `/cinema?demo=fixture`. See a completed film-programme run, the Programme Bet, evidence/trace, and the Decision Challenge. **Impact Lab is a fixed-Qloo-pool sensitivity check**: not a non-Qloo evaluation. Withheld affinity changed 0/8 winners in the 29 October measured study.
4. **60–80s · FilmSponsor:** Open `/creator/sponsor`. Explain discovery → brand evidence → creator-written proposal → official-source review → approval-gated export → outreach record. **Do not claim automated sending, sponsorship deals, ROI, or that a sponsor was obtained.** Live sponsor guest workflow needs separate browser acceptance; if access fails, describe the tested code path rather than demonstrating invented brands.
5. **80–90s · Distinction and close:** Point to the dated [real 12/12 movie study](LIVE_COMMON_UNIVERSE_RESULT_20261102.md): same fixed movie set, metadata winner **The Witch**, live Qloo winner **Videodrome**, top-five overlap **2/5**, tau-b **0.0303**. Phrase it as *"different and inspectable recommendations; effectiveness still requires external evaluation."*

## Operational stop/go before the demo

- **PASS (GitHub Actions, 2 Nov):** `/`, `/creator`, `/cinema`, `/creator/sponsor` returned HTTP 200 with baseline security header. The proxied `/api/health` returned HTTP 200 with `mode=public_demo`, fixture available, live Creator available and FilmSponsor guest mode enabled. [Initial successful production run](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/41471725957).
- **PASS (same run):** `POST /api/run/demo` completed successfully; returned `data_status=fixture` with 15 trace records.
- **Not implied by these checks:** client-side rendering and visual layout in the deployed browser, actual live Creator analysis, FilmSponsor guest session/campaign write path today, brand-specific evidence, third-party systems, or attendance lift.
- **Current branch:** Adds a separate one-click Cinema fixture shortcut and reruns the production smoke with both Cinema and Creator fixture endpoints; a branch deployment is not proof the merged Vercel release is updated. Verify the new CTA on production after Vercel deploys main.
- **Safety:** Never display provider secrets, raw credentials or personal campaign data. Never let a fixture or a synthetic demonstration become a claimed real Qloo measurement. Do not re-run the live 12/12 study just to obtain a preferred winner.

## Fallbacks under judge-time pressure

If backend sleeps, use the already-visible connection status/retry UX. If the live Creator call fails or the public-run quota blocks a request, use the **explicit** labelled fixture demo. If a film cannot be resolved, show the insufficiency state instead of altering title/year to make an arbitrary match. If FilmSponsor guest flow is unavailable, explain the approval workflow from the interface but do not claim it was exercised. The demo cannot prove actual sponsorship success or audience attendance.

## Source-of-truth links

- [Repository and CI](https://github.com/Sohamgaonkhadkar/adjacent-cinema)
- [Impact Lab audit](IMPACT_LAB_COMPETITOR_AUDIT_20261102.md)
- [Live same-universe experiment and limitations](LIVE_COMMON_UNIVERSE_RESULT_20261102.md)
- [Production operational checklist](NEXT_LIVE_CHECKLIST.md)
