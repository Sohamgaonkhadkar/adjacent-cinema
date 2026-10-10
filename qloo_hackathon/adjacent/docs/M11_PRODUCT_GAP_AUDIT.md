# M11: Product-Specification Gap Audit

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report audits the current M7/M10.2 implementation against the frozen Adjacent product specification and identifies the highest-risk gaps.

---

## Current Implementation Status

### What Exists (M7)

1. ✅ Entity resolution via `/search` with title+year verification
2. ✅ Taste DNA via `/v2/insights` with `filter.type=urn:tag`
3. ✅ Candidate expansion via `/v2/insights` with 5 fixed domains
4. ✅ Cohort construction (tag clusters, domain groups, singletons)
5. ✅ Cohort ranking with one-scoring-call-per-context rule
6. ✅ Evidence gate (verdicts, thresholds, insufficiency messages)
7. ✅ Programme Bet (basic — wraps top-ranked cohort)
8. ✅ Geography (heatmap via `/v2/insights`)
9. ✅ Test Card (falsification conditions)
10. ✅ Provenance ledger
11. ✅ Agent orchestrator with budget

### What Exists (M10.2)

1. ✅ Qloo resolution benchmarks (historical + modern)
2. ✅ Trusted resolver with IMDb ID matching
3. ✅ Verified match rate: 93.4% on curated modern benchmark

---

## Gap Analysis

### Gap 1: AGENTIC DOMAIN SELECTION

**Current:** Fixed 5 domains (`urn:entity:artist`, `urn:entity:movie`, `urn:entity:tv_show`, `urn:entity:book`, `urn:entity:brand`)

**Required:** Dynamic, deterministic, auditable domain selection based on Taste DNA

**Risk:** HIGH — The agent always queries the same 5 domains regardless of the programme's cultural profile. A film programme should not always query brands if the taste profile suggests art, music, or destinations.

**Fix:** Implement `select_domains()` that inspects tag families and chooses domains with explicit reasons.

### Gap 2: INPUT + RESOLUTION CONTRACT

**Current:** Resolver accepts `title`, optional `year`, optional `imdb_id`. Resolution via `/search` with year verification.

**Required:** Accept city, cinema name, film title, optional year, optional IMDb ID. Handle VERIFIED, AMBIGUOUS, MISMATCH, UNRESOLVED states correctly.

**Risk:** MODERATE — The resolver exists but the UI/API contract is not fully specified. Ambiguity handling exists but disambiguation path is not implemented.

**Fix:** Formalize the input contract and implement disambiguation path.

### Gap 3: REAL TWO-SIDED PROGRAMME BET

**Current:** Programme Bet wraps the top-ranked cohort with prose. No actual two-sided scoring.

**Required:** Evaluate both (A) cultural compatibility with existing programme AND (B) evidence of reaching the adjacent cohort.

**Risk:** HIGH — The current Programme Bet is a prose wrapper, not a genuine decision layer. It doesn't actually score both sides.

**Fix:** Implement two-sided scoring using Qloo insights for both compatibility and reach.

### Gap 4: EVIDENCE + EXPORT LAYER

**Current:** Provenance ledger exists. Rendered text output exists. JSON export exists but is minimal.

**Required:** Full evidence trace, Qloo call IDs, data status, stop reason, Copy as JSON action.

**Risk:** MODERATE — The provenance ledger is strong but the frontend doesn't expose all evidence. The JSON export exists but may not be complete.

**Fix:** Verify JSON export completeness and add frontend evidence display.

---

## Gap Priority

| Gap | Risk | Priority | Effort |
|-----|------|----------|--------|
| Domain Selection | HIGH | 1 | Medium |
| Two-Sided Programme Bet | HIGH | 2 | Medium |
| Input + Resolution Contract | MODERATE | 3 | Low |
| Evidence + Export Layer | MODERATE | 4 | Low |

---

## Recommendations

1. **Implement dynamic domain selection** — Highest risk, most visible gap
2. **Upgrade Programme Bet** — Second highest risk, core product value
3. **Formalize input contract** — Moderate risk, enables real workflows
4. **Verify evidence export** — Lower risk, trust layer

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE