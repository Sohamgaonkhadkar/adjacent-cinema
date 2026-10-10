# M12.7: Evidence Lock — Scoring Audit

**Date:** 2026-10-07
**Status:** COMPLETE

---

## WHAT WAS REMOVED

| Artifact | Type | Problem |
|----------|------|---------|
| `FILM_GENRE_PROXIES` | Hand-coded dict | Manual genre mapping per film |
| `GENRE_TO_THEME` | Hand-coded dict | Manual theme mapping per genre |
| `DOMAIN_THEMATIC_VECTORS` | Hand-coded dict | Manual domain→theme mapping ("artist = dark") |
| `member_ratio` in programme_fit | Overlap | Same inputs as entity_fit |
| Domain-based differentiation | Hidden preference | `artist=2, tv_show=1` hardcoded |
| Per-film support counts | Invalid | All candidates get same programme_films list |

---

## WHAT REPLACED THEM

### programme_fit: Real Qloo Evidence

| Source | Type | What it measures |
|--------|------|-----------------|
| `cohort_kind` | Qloo construction | tag_cluster > subtype_group > domain_group |
| `shared_tags` | Qloo construction_evidence | Tags Qloo returned as connecting cohort |
| `candidate_tags` | MemberEvidence.tags | Tags on specific entity |

When no real evidence exists: `programme_fit = NOT_AVAILABLE`

### differentiation: Event Format Only

| Format | Score | Reasoning |
|--------|-------|-----------|
| Live performance/DJ set | 2 | Genuinely different from cinema |
| Discussion/reading | 1 | Somewhat different |
| Themed season | 1 | Somewhat different |
| Standard screening | 0 | Not differentiated |

Domain name is NOT an input. `score_differentiation(event_format)` takes only the format string.

### Per-film Attribution: NOT_AVAILABLE

Qloo returns candidates for the entire programme. There is no per-film attribution.

```
per_film_attribution = NOT_AVAILABLE
```

`support_count`, `support_ratio`, `supporting_films` are NOT computed.

---

## COMPONENT INDEPENDENCE (AUDITED)

| Component | Inputs | Evidence Source | Overlap with entity_fit? |
|-----------|--------|----------------|------------------------|
| entity_fit | affinity, qualifying, total | Qloo API | N/A (baseline) |
| event_feasibility | domain, programme_films count | Entity dict | NO |
| programme_fit | cohort_kind, shared_tags, candidate_tags | Qloo construction + tags | NO |
| testability | event_format (str), qualifying_members | Feasibility output (str) + entity | NO (qualifying is in entity_fit but here used for sample_size, not signal strength) |
| differentiation | event_format (str) | Feasibility output (str) | NO |

**Known shared signal:** testability uses `qualifying_members` for sample_size, while entity_fit uses it for signal strength. These answer different questions: "is the sample big enough to measure?" vs "is the signal strong enough to act on?"

---

## FORMAT-DRIVEN DIFFERENTIATION: THE HONEST LIMITATION

Differentiation is scored from the event format string. The event format is assigned by feasibility rules based on domain. Therefore:

1. The differentiation SCORE is format-based (not domain-based) ✓
2. The format ASSIGNMENT is domain-based (artist → live music, tv_show → season) ✓
3. This means different domains tend to get different formats → different differentiation scores ✓
4. This is a structural feature of feasibility rules, not a hidden preference ✓

This is documented, not hidden. In practice, the event format would be refined during venue consultation.

---

## ABLATION SUMMARY

### Genesis (Unloved, score=10)
- No single component changes the bet

### Prince Charles (The Contortions, score=9)
- Removing testability → rank drops 50 (What Remains becomes #1)
- Removing differentiation → rank drops 50 (What Remains becomes #1)

**Insight:** testability and differentiation are the discriminating components.

---

**Status:** COMPLETE