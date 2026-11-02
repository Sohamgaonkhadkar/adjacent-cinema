# M14 — honest same-universe Qloo versus independent metadata study

**Created:** 2 November 2026. **Status:** code and a frozen exploratory catalog committed; **new live results are not included**. Do not describe this as an observed Qloo win.

## Why an additional experiment exists

- The October 29 **Impact Lab** withheld affinity over a *Qloo-discovered pool*, and changed **0/8** evaluable winners. That identifies no affinity-driven change in those fixed-pool results, but is *not* an independent no-Qloo baseline.
- Earlier M12.1 metadata comparisons used film-only candidate pools against cross-domain Qloo lists; domain expansion and film ranking were mixed.
- M12.3 attempted a 53-film common catalog but intersected it against Qloo's **discovered** results; the first preserved context records **zero common candidates**. Qloo did not directly score every catalog movie, so the attempted identical-universe ranking was non-evaluable in that context.
- The M13.11 Qloo-versus-LLM report was **fixture-based** for Qloo and the LLM-only arm was **blocked** without a key. It is not live incremental evidence.

## Design: isolate ranking from discovery

**Task:** Among the same twelve preselected film titles, which ones would a film programmer prioritize given three fixed programme films? The trial is deliberately **film-only**. It does not test cross-domain audience discovery or whether a programmed screening succeeds.

1. The independently authored, pre-existing film metadata catalog is locked in `data/benchmarks/common_universe_20261102.json`. It is a selected subset of the older M12.3 metadata catalog; it is **author curated and not independently externally audited**. This choice is exploratory, not blind to previous Adjacent work. It does not use Qloo to discover candidates.
2. `freeze_manifest()` normalizes title/year/genre/optional country/director and computes a SHA-256 digest **before querying Qloo**. Programme titles are forbidden from the candidate set; duplicate candidate identities and Qloo-derived catalog fields are rejected.
3. **Metadata-only arm:** for each candidate, max across seeds of `0.5 * genre-Jaccard + 0.2 * same nonempty country + 0.3 * same nonempty director`; sort descending, then by canonical film key. The constants are fixed rules for this exploratory experiment, **not learned performance weights**. When metadata is missing it contributes zero, not an invented match.
4. **Qloo arm:** after freeze, use the same strict, existing trusted `EntityResolver` to verify title/year/type (and IMDb ID if supplied). If *any* of the three seeds or twelve candidate identities cannot be verified, mark the whole trial `not_evaluable` and report resolution; do not shrink the independent catalog.
5. Only after complete verified resolution, score all twelve movie IDs in **one** Qloo `/v2/insights` context, using `signal.interests.entities` for seed IDs and `filter.results.entities` for locked candidate IDs. Sorting uses the returned within-context affinity scores and canonical film key, never cross-context raw affinity. Extra, missing, repeated, non-finite or out-of-range provider results fail the validity/coverage gate.
6. **Compare only if fully observed:** show metadata winner, Qloo winner, top-five overlap, tau-b and call ID. A changed rank is a *different ranking*, **not** a correct recommendation or improved outcomes. Otherwise record `blocked` or `not_evaluable` and report the full intended denominator (12).
7. A real incremental-value claim would still require prospectively registered, blinded programmer decisions or outcome labels on a cohort that neither ranking nor the catalog construction has seen. Do not tune weights, film selection or identity acceptance after looking at observed differences.

## Reproduce

From `qloo_hackathon/adjacent`:

```bash
python research/scripts/m14_common_universe_live.py \
  --manifest data/benchmarks/common_universe_20261102.json \
  --output /tmp/m14_preflight.json

QLOO_API_KEY=<use_your_secure_environment_secret> \
python research/scripts/m14_common_universe_live.py \
  --manifest data/benchmarks/common_universe_20261102.json \
  --output /tmp/m14_live.json --live
```

**Do not commit API keys or a live experiment artifact without examining its privacy and provenance.** The first command performs only metadata preflight, returns `blocked`, and makes zero Qloo calls; it is not a substitute for the second. The second may return `not_evaluable` for poor provider identity coverage, network failures, or an API contract issue; no fixture or synthetic score is substituted. Both write a machine-readable JSON record with the frozen catalog hash, status and denominator. The executable returns exit code 2 when `--live` produces no evaluable comparison.

## Scope / decision rubric

| Observation | Correct interpretation |
| --- | --- |
| Different full-universe Qloo and metadata winners | Demonstrated **ranking disagreement** on the pre-fixed 12 films, not better choices |
| Same full-universe winner | **No top-choice difference** on that task; lower ranks may still differ |
| One or more seed/candidate cannot be verified | **Not evaluable**; do not compare only intersecting films |
| One or more requested candidate has no returned affinity | **Not evaluable**; report scored n / 12 |
| No Qloo key | **Blocked**; metadata-only preflight is not a live study |
| Blinded real operator labels subsequently show improvement under comparable constraints | Candidate evidence of *usefulness*, subject to sample size, leakage, bias and provenance checks |

**Architectural boundary:** This is a research runner and pure comparison module. It does not modify the production ranker, Qloo gate, Cinema Mode, or public Impact Lab, and it does not add live API calls to a normal user journey. Production UX should only display this separate study if an actually observed and verified result is available, with its limitations retained.
