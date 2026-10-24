# Cultural Multiverse / Positioning Arena

## Scope

The Positioning Arena is a deterministic, browser-side interpretation of **one completed Creator run**. It reads only the run's existing result and trace, makes no new Qloo request, and preserves the original Test Card. It can show one, two, or three strategies; unsupported positions remain visible as unavailable with a reason.

The strategy/type contract and pure engine are in `frontend/lib/positioningArena.ts`; the minimal Creator integration is `frontend/components/PositioningArena.tsx` and `frontend/app/creator/page.tsx`.

## Evidence eligibility and provenance

A candidate cohort must be in the run's ranked cohort list, carry an existing `strong` or `moderate` evidence verdict, have a finite 0–1 mean affinity, and contain at least two finite, trace-linked members with affinity at or above Qloo's existing Medium threshold (0.5). If present, the cohort score call ID must agree with the members' call ID and the run trace. Rejected/unranked groups, unresolved IDs, missing scores, and untraced calls are not promoted into strategies.

Measured runs require source film inputs marked `VERIFIED`; fixture runs may use only IDs already present in the fixture response and remain `fixture` throughout. A fixture walkthrough is never represented as a live Qloo result. Each strategy carries only returned entity IDs/names, cohort IDs, validated call IDs, and response-backed scores/tags/attributions. The backend's attribution validation remains the authority for seed IDs and score bounds; the client rechecks status, verified source identity, finite 0–1 values, and trace references before using attribution to connect candidates.

## Strategy selection rules — `cultural-positioning-v1`

1. **ANCHOR** — the first eligible cohort in the completed run's existing cohort order. The current ranker sorts by evidence verdict, novelty proxy, qualifying-member breadth and then affinity only as a within-context tiebreak. The brief names the selected cohort's returned members and call. This is the existing deterministic rank, not a claim of globally highest affinity across domains.
2. **BRIDGE** — the first deterministic pair of eligible cohorts from distinct entity domains that has either (a) an exact Qloo-returned tag ID shared by members in both groups or (b) validated per-seed Qloo attribution to the same verified source-film entity in both groups. At least one candidate must differ from the anchor's candidate set. If neither returned relationship exists, BRIDGE abstains; matching words or labels are never enough. Attribution weights from different calls are not compared.
3. **FRONTIER** — among other eligible cohorts in the anchor's **same source `context_id`**, select the cohort with the highest existing novelty proxy, but only if its proxy is present, greater than the anchor's, and its candidate set differs. The minimum evidence requirement is the same strong/moderate verdict and at least two trace-linked members clearing Medium. No higher-proxy alternative means abstention.

The existing novelty proxy is `1 - median Qloo popularity` for a cohort, as implemented in `backend/app/domain/scoring.py`. It is neither a calibrated novelty measure nor a measure of effectiveness or success.

## What-If formula — `weighted-ordinal-preference-v1`

Changing priorities reorders the fixed strategy objects and never mutates candidate evidence. Fit and novelty values are ranked only among cohorts in the same Qloo domain/scoring context. Fit ranks higher mean affinity first within that context; exploration ranks higher existing novelty proxy first within that context. Equal source values share an ordinal preference. Breadth counts the distinct returned Qloo entity domains in a strategy.

For each available strategy, for each supported nonzero-weight dimension `d`, `ordinal_d` is the normalized ordinal position in `[0,1]` within the relevant comparison group (`1` is preferred; ties share a position). The displayed preference index is:

`sum(policy_weight_d × ordinal_d) / sum(policy_weight_d for supported dimensions)`

Unsupported dimensions are omitted from the denominator and their reason is displayed. If no weighted dimensions are supported, the deterministic source-rank/strategy-ID tie-break is used. The sliders accept integer weights from 0 to 100 and do not need to sum to 100.

This is an operator-defined **preference index**, not a calibrated prediction, probability, affinity score, audience-size estimate, causal counterfactual, or prediction of audience behaviour. Cross-context affinity and novelty values are never compared or averaged.

## Evidence Challenge and brief

Each available strategy shows source-input resolution state, evidence cohort/entity IDs, provider call IDs, member attribution states (`returned`, `missing`, `unsupported`, `not_requested`), unresolved references, and limitations. It offers one observation that could support and one that could contradict the hypothesis. These checks validate structure and provenance; they cannot prove that every sentence is semantically entailed by source evidence.

The deterministic brief names returned cultural entities and the verified source film references available in the run. Its falsifiable hypothesis refers to a creator-selected primary action measure and pre-set decision rule; the UI proposes a comparison protocol and fixed observation window but invents no outcome threshold, sample size, audience count, or result. Missing or non-comparable records remain inconclusive.

## Freeze into existing experiment lifecycle

Saving a selected strategy adds `source_bet.cultural_multiverse_snapshot` to the existing experiment record. The versioned snapshot contains the originating run ID, original Test Card, all strategy alternatives (including explicit unavailable states), selected strategy, source data status, policy values/formula version/order, source entity/cohort/call references, limitations and exact edited comparison/measure/decision/window fields. The existing repository persists `source_bet` as JSON and does not need a schema migration. Observations and evaluations stay append-only and do not change this snapshot. A missing snapshot key in a legacy experiment is handled as “not recorded”; the rest of that experiment remains readable.

A saved plan does not mean a test ran. Fixture data remains fixture in the saved snapshot, and future outcomes must come from actual appended observations.

## Production readiness

The repository's documented public-demo guard requires both owner-controlled `ADJACENT_PUBLIC_LIVE=1` and a backend-only `QLOO_API_KEY` for anonymous live Creator requests. `ADJACENT_PUBLIC_DEMO=1` alone permits the fixture flow and leaves shared experiment writes disabled. Repository documentation reports that live Qloo and hosted deployment were not verified, and the read-only GitHub deployments query returned no deployment records. The current production host's environment/health could not be inspected from this sandbox; therefore the hosted judge path remains **unverified and must be treated as blocked** until an authorized owner checks the deployed backend health (without exposing key material) and completes a bounded live Creator run. Do not enable public live calls from this feature branch.
