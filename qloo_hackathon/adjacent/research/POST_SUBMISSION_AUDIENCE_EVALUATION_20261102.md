# Post-submission research: what Qloo adds, and what it does not (2 Nov 2026)

> **Research branch only.** This study happened after the Qloo Agentic Hackathon submission cutoff (30 October 2026). It is **not part of the frozen Devpost submission**, does not update the production app, and must never be described as an experiment performed before submission. The official rules restrict changes to submitted material after the deadline. The goal is to improve the evidence and guide later product work, not to retroactively edit a judged entry.

## Executive finding

**Qloo changes and diversifies a movie ranking; this study does not show improved historical audience liking.** On a fixed 12-film horror candidate universe, a previously measured Qloo ranking had a different #1 from an author-curated metadata heuristic. We subsequently evaluated agreement with independent historical MovieLens-32M rating observations. On the strict primary cohort, the metadata baseline performed better; on the two-seed sensitivity cohort, the ranking difference was statistically inconclusive.

The independent **labels** are MovieLens ratings, but it is **not established** whether MovieLens or related information was available to Qloo during training. Neither historical user preference nor diversity is evidence of cinema ticket sales, audience attendance, sponsorship revenue, or real-world causal improvement.

## Frozen rankings (before ratings evaluation)

From `data/processed/m14_common_universe_live_20261102.json` and `data/benchmarks/common_universe_20261102.json`: programme seeds **The Thing (1982), The Shining (1980), Suspiria (1977)**. Shared candidate set: 12 films. All 12 Qloo scores measured in one scoring context on 2 November 2026. Metadata rank #1 **The Witch**; Qloo #1 **Videodrome**; top-five overlap **2/5**. The film set was manually curated by the author; it is not an independent blind prospective evaluation.

## Independent historical rating proxy (MovieLens 32M)

- **Data:** GroupLens MovieLens 32M, 32,000,204 anonymized historical ratings from users through 12 October 2023. The benchmark script downloads the published dataset and does not commit or redistribute raw ratings. Only aggregate statistics are saved. GroupLens does not endorse this research; commercial use requires prior permission.
- **Title linkage:** Case- and punctuation-normalized exact film titles with movie year ±1; equal-distance ambiguous matches rejected. **11/12 candidates** and **3/3 programme seeds** matched; **The Babadook** did not match the external catalogue, and was not silently substituted.
- **Outcome proxy:** Among individuals who rated at least two different candidates *differently*, fraction of unequal-rated film pairs ordered in the same direction by the frozen ranking. Each user has equal weight. Seed preference is defined as rating ≥4.0; no provider score is used to choose the audience. User-level paired bootstrap uses 1,000 replicates with a deterministic seed.

| Cohort | Users | Qloo accuracy | Metadata accuracy | Qloo minus metadata | 95% paired bootstrap CI |
| --- | ---: | ---: | ---: | ---: | --- |
| **Primary:** ≥1 liked programme seed | 5,929 | **48.00%** | **52.56%** | **−4.56 pp** | −6.12 to −3.00 pp |
| **Sensitivity:** ≥2 liked programme seeds | 2,500 | **50.52%** | **51.26%** | **−0.74 pp** | −3.29 to +1.78 pp |
| Context only: any candidate co-rater | 9,721 | 46.04% | 53.71% | −7.67 pp | −9.15 to −6.33 pp |

**Interpretation:** For this particular author-curated pool and observed historical user comparisons, the fixed Qloo rank did not outperform the genre/country/director heuristic. The larger negative primary-cohort result is not explained away by the stricter inconclusive result. These accuracy estimates are also selection-biased because user ratings exist only for films people chose to rate. No held-out prospective user exposure experiment was run.

**Reproducibility:** Run `research/scripts/m15_movielens_audience.py` on the original `ml-32m.zip`. The frozen ranks are never optimized against the labels. [One-off green GitHub Actions run](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/41478229452) and its [aggregate JSON artifact](https://github.com/Sohamgaonkhadkar/adjacent-cinema/actions/runs/41478229452/artifacts/13157968673). Retention of the Actions artifact is limited.

## Exploratory cultural breadth (not pre-registered)

After observing the rating result, we examined *why* a film programmer might still choose the Qloo ranking for **cultural exploration rather than maximizing retrospective liking**. This is explicitly **post-hoc** and not an independent validation. Apply `research/scripts/m15_diversity_proxy.py` to the same frozen 12-film metadata and top-five ranks.

| Top-five selection | Qloo | Metadata baseline |
| --- | --- | --- |
| Countries represented | **3** (Canada, UK, USA) | **1** (USA) |
| Unique directors | **5** | **4** |
| Mean pairwise Jaccard of genre tags | **0.517** | **0.717** |

The lower genre similarity and broader country coverage indicate a more varied top-five *under these metadata definitions*. They **do not prove** greater attendance, novelty *perceived by users*, satisfaction, improved funding odds, or generalization to other programmes. The hand-collected metadata and single example limit reliability.

## Actionable product learning (for future work; not a retroactive hackathon claim)

1. Preserve two clearly distinct objectives: **Explore cultural adjacencies** (coverage/diversity hypothesis) and **Predict preference** (rating accuracy hypothesis); do not imply the first automatically optimizes the second.
2. Test blind cinema-programmer judgments for programming **novelty, contextual fit and plausibility**, with both rank lists anonymized and counterbalanced, plus explicit criteria and sample size.
3. Use the existing Audience Pulse/Test Card lifecycle to run a prospective randomized programme/marketing experiment with consent and actual, independently collected observations. Do not call the hypothetical experiment an observed result.
4. Report adverse results as first-class evidence, and repeat on other *pre-specified*, independently selected film programmes. Do not select samples based on which Qloo comparison wins.

## Research citation and conditions

F. Maxwell Harper and Joseph A. Konstan (2015). *The MovieLens Datasets: History and Context.* ACM Transactions on Interactive Intelligent Systems 5(4), 19:1–19:19. DOI: 10.1145/2827872. Dataset documentation: https://files.grouplens.org/datasets/movielens/ml-32m-README.html. Research use only subject to the GroupLens license; neither the University of Minnesota nor GroupLens endorses this work.
