# M12.7: Evidence Lock

**Date:** 2026-10-07
**Status:** SUPERSEDED BY M12.8 — event format was still indirectly domain-based (domain→format→differentiation); programme_fit had hand-coded semantic weights (tag_cluster=2); testability used synthetic keyword heuristics

---

## HAND-CODED BIAS REMOVED

| What | Why removed |
|------|------------|
| FILM_GENRE_PROXIES | Manual genre dict per film |
| GENRE_TO_THEME | Manual theme dict per genre |
| DOMAIN_THEMATIC_VECTORS | "artist = dark, book = literary" |
| member_ratio in programme_fit | Overlaps entity_fit inputs |
| Domain-based differentiation scores | "artist=2, tv_show=1" hardcoded |
| Per-film support counts | All candidates get same list — invalid attribution |

---

## REAL EVIDENCE NOW USED

### programme_fit
- `cohort_kind` from Qloo (tag_cluster, subtype_group, domain_group)
- `shared_tags` from Qloo construction_evidence
- `candidate_tags` from MemberEvidence.tags
- `NOT_AVAILABLE` when no real evidence exists

### differentiation
- Scored from event format string only
- Domain name is NOT an input
- `score_differentiation(format)` — no domain parameter

### per-film attribution
- Marked `NOT_AVAILABLE`
- Qloo does not provide per-film output attribution

---

## RESULTS

| Context | STRONG | PLAUSIBLE | REJECT | Programme Bet |
|---------|--------|-----------|--------|---------------|
| Genesis | 98 | 52 | 50 | Unloved (artist) |
| Prince Charles | 100 | 0 | 50 | The Contortions (artist) |

**Cross-context:** Same domain (artist), different entity.

---

## WHY BOTH ARE ARTISTS

Both contexts have horror programmes. Qloo returns artist cohorts with tag_cluster construction (5 shared tags). Artists get differentiation=2 because the event format "Live music performance/DJ set + film screening" contains a live performance component.

TV shows get differentiation=1 because "Themed film screening season" is an extended programming format.

This is a FORMAT difference, not a DOMAIN preference. The format assignment is domain-based (feasibility rules), but the differentiation SCORE is purely format-based. This is documented, not hidden.

---

## ABLATION

### Genesis (Unloved, score=10)
- No single component changes the bet

### Prince Charles (The Contortions, score=9)
- testability → rank changes by 50
- differentiation → rank changes by 50

---

## TESTS

21 tests:
- No hand-coded domain preference in scoring
- programme_fit uses real Qloo evidence (tags, cohort kind)
- Differentiation is format-driven, not domain-driven
- programme_fit = NOT_AVAILABLE when evidence is missing
- member_ratio not in programme_fit
- Per-film attribution = NOT_AVAILABLE
- Two domains with identical evidence get same programme_fit
- Artist not automatically favored over other domains
- Removing domain thematic vectors doesn't break evaluation

---

## DOCUMENTATION

- `M12_7_EVIDENCE_LOCK.md` — This file
- `M12_7_SCORING_AUDIT.md` — Detailed component audit
- `M12_7_FINAL_REPORT.md` — Final report with gate questions

---

## REAL LIMITATION (EXPLICITLY STATED)

> "Qloo's current returned cohort structure does not provide reliable per-output attribution to individual programme films. Therefore Adjacent does not claim per-film causal attribution of a candidate opportunity."

> "Programme-fit evidence is based only on observable returned Qloo metadata/tags and deterministic programme metadata. Hand-coded semantic domain assumptions are excluded from the primary score."

---

**Status:** COMPLETE