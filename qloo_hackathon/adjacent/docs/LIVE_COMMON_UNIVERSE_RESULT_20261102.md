# Observed M14 common-universe result — 2 November 2026

**Status: ONE EVALUABLE LIVE-QLOO RANKING DISAGREEMENT, NOT AN OUTCOME VALIDATION.**

Original CI evidence: [M14 live study run #41464154935](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/41464154935), job completed successfully on commit `95efba0891bb301affb167dcedaf9f2731051520`. [Run artifact #13149983300](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/41464154935/artifacts/13149983300) contains the generated JSON (30-day retention). The JSON report is preserved at [data/processed/m14_common_universe_live_20261102.json](../data/processed/m14_common_universe_live_20261102.json) so it does not disappear with the artifact. Method and preregistered-as-of-M14 exploratory catalog: [study design](COMMON_UNIVERSE_STUDY_20261102.md) and [locked manifest](../data/benchmarks/common_universe_20261102.json).

| Measurement | Observed |
| --- | --- |
| Programme | The Thing (1982), The Shining (1980), Suspiria (1977) |
| Independent film candidate universe | 12 titles, defined in the manifest before the new Qloo calls |
| Catalogue digest SHA-256 | `e092dc220023b6e8f29e295a11cc5547d05f632d4aa8f3128840a4bfcd4879b9` |
| Verified seed films | **3/3** |
| Verified and scored candidate films | **12/12** |
| Scoring | Single Qloo movie scoring context, call `m14-common-universe-c016` |
| Metadata-only top recommendation | **The Witch (2015)** |
| Qloo-signal top recommendation | **Videodrome (1983)** |
| Changed winner? | **Yes** |
| Shared top-five films | **2/5** (The Witch, Hereditary) |
| Kendall tau-b | **0.0303** (34 concordant, 32 discordant pairs out of 66) |
| Independent operator/outcome benefit demonstrated? | **No** |

The experiment verifies that **Qloo scores reorder the same twelve films significantly relative to a genre/country/director metadata heuristic**. Neither candidate selection nor metadata ranking used Qloo discovery, and the Qloo ranking was computed using one common scoring context rather than by filtering a separately retrieved results list. This fills a *methodological* gap in the older M12.3 film experiment, which lacked common retrieved films in its first context.

## Interpretations we can and cannot make

**Supported:** Both methods received exactly the same twelve candidates. Strict title/year/type checks passed 15/15 identities, and Qloo returned affinity scores for 12/12 candidates. The observed winners differ; tau-b is near zero. This is one observed live provider comparison with a complete denominator and preserved provenance.

**Not supported:** That Qloo is more accurate, better at predicting bookings, improves cultural programming, lifts ticket sales, or outperforms alternatives generally. The metadata comparator is deliberately elementary and the candidate selection was author-curated, not blind to previous work. This single example could be atypical. Ranking disagreement is not an impact metric.

The October 29 fixed-Qloo-cohort Impact Lab still shows **0/8 winner changes when affinity was withheld**. These two findings do **not** contradict: M14 scores fixed *movies* directly against programme seeds and compares to an independent metadata score, whereas Impact Lab compares *cohorts already discovered and admitted using Qloo* and uses other Qloo-derived ordering keys.

## Next quality gate

1. Predeclare a **larger set of film programme briefs**, include regional-language and non-horror cases and retain every failure. Hold a non-Qloo candidate catalog fixed before executing provider calls.
2. Have venue programmers make **blinded, independent judgements** for both ranked lists under the same programming constraints; predeclare rubric and failure criteria.
3. Aggregate programme-level paired results and uncertainty, including coverage denominators and disagreement rates. Add observed attendance outcomes only when genuinely available before the recommendation, and avoid leakage.

Do not infer a hackathon placement or a business-lift figure from this result.
