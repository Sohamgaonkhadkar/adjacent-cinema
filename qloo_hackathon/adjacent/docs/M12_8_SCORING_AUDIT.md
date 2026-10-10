# M12.8: Scoring Audit

**Date:** 2026-10-07
**Status:** COMPLETE

---

## AUDIT: WHAT IS OBSERVED vs DERIVED vs POLICY vs UNKNOWN

### OBSERVED (returned directly by Qloo)

| Field | Source | Description |
|-------|--------|-------------|
| affinity | Qloo API | Cultural affinity score (0-1) |
| popularity | Qloo API | Entity popularity (0-1) |
| qualifying_members | Qloo cohort | Members above Medium band |
| total_members | Qloo cohort | Total cohort members |
| band | Qloo API | Official affinity band |
| tags | MemberEvidence.tags | Qloo tag URNs on entity |
| cohort_kind | CandidateCohort.kind | How cohort was constructed |
| shared_tags | construction_evidence | Tags connecting cohort |
| construction_reason | CandidateCohort | Why cohort exists |

### DERIVED (mathematical normalization of observed fields)

| Field | Formula | Note |
|-------|---------|------|
| qloo_evidence_score | 0.6*affinity + 0.2*popularity + 0.2*qualifying_ratio | Weights are policy |
| qualifying_ratio | qualifying_members / total_members | Simple ratio |

### POLICY (our product/venue rules)

| Field | What it is | Why it's policy |
|-------|-----------|----------------|
| Evidence weights | 0.6 / 0.2 / 0.2 | We chose these weights |
| Experiment format | domain → event type | Our venue format rules |
| Event feasibility | domain → feasibility | Our operational assumptions |
| Testability | format keywords | Our measurement heuristics |
| Differentiation | format novelty | Our novelty assessment |

### UNKNOWN (not available from Qloo)

| Field | Status |
|-------|--------|
| per_film_attribution | NOT_AVAILABLE — Qloo doesn't provide per-film output |
| success_thresholds | TBD — requires venue baseline data |

---

## AUDIT: COMPONENT-BY-COMPONENT

### qloo_evidence_score (Layer A)

| Aspect | Status |
|--------|--------|
| Uses domain? | NO |
| Uses event format? | NO |
| Uses testability? | NO |
| Uses differentiation? | NO |
| Uses cohort_kind? | NO |
| Uses shared_tags? | NO |
| Uses hand-coded mappings? | NO |
| Inputs | affinity, popularity, qualifying_ratio |
| Source | All observed Qloo fields |
| Weights | Product policy (documented) |

### Experiment format (Layer B)

| Aspect | Status |
|--------|--------|
| Affects ranking? | NO |
| Uses domain? | YES (for format assignment) |
| Labelled as | Product policy |
| Purpose | Operational proposal for venue |

### programme_fit_evidence (descriptive)

| Aspect | Status |
|--------|--------|
| Scored? | NO (descriptive only) |
| Contains | cohort_kind, shared_tags, candidate_tags |
| Labelled as | Descriptive Qloo evidence |
| Quality assessment | Explicitly labelled "PRODUCT POLICY" |

---

## AUDIT: M12.5 → M12.8 EVOLUTION

| Aspect | M12.5 | M12.6 | M12.7 | M12.8 |
|--------|-------|-------|-------|-------|
| Ranking inputs | affinity, feasibility, programme_fit, testability, differentiation | Same + programme_direction | Same - hand-coded themes | affinity, popularity, qualifying_ratio ONLY |
| Domain in ranking | Indirect (via format) | Indirect (via format) | Indirect (via format) | ZERO |
| Hand-coded mappings | Genre proxies | Film genre proxies | REMOVED | REMOVED |
| programme_fit | affinity threshold | film metadata | Qloo tags | Descriptive only |
| differentiation | domain-based | domain-based | format-based | REMOVED from ranking |
| Artist dominance | Yes (180/180 STRONG) | Yes (score=10) | Yes (score=10) | NO (tv_shows dominate) |
| Winner (Genesis) | What Remains | Unloved | Unloved | Tomorrow |
| Winner (PCC) | What Remains | What Remains | The Contortions | Devil in Ohio |

---

## CRITICAL FINDING

**Previous artist dominance was caused by format policy, not Qloo evidence.**

In M12.5-M12.7:
- Artists got differentiation=2 (live music format)
- TV shows got differentiation=1 (season format)
- This +1 advantage was enough to overcome artists' lower affinity

In M12.8 (pure evidence):
- TV shows have avg affinity 0.949 vs artists' 0.901
- Without the format-based differentiation bonus, TV shows rank higher
- Artists are not structurally disadvantaged — they simply have lower Qloo affinity for these programmes

---

**Status:** COMPLETE