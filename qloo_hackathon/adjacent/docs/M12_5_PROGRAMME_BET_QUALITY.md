# M12.5: Programme Bet Quality Lock

**Date:** 2026-10-07
**Status:** SUPERSEDED BY M12.6 — programme_fit was not genuinely independent (used only affinity)

---

## SCORING SYSTEM

### Components (total = 10 points)

| Component | Criteria | Points |
|-----------|----------|--------|
| **entity_fit** | affinity ≥ 0.85 AND members ≥ 30 → 2 | 0-2 |
| **event_feasibility** | concrete format AND venue-compatible AND not vague → 2 | 0-2 |
| **programme_fit** | affinity ≥ 0.8 AND overlap ≥ 1 AND relationship → 2 | 0-2 |
| **testability** | concrete format AND measurable AND venue-doable → 2 | 0-2 |
| **differentiation** | genuinely different from cinema (not free point) → 2 | 0-2 |

### Classification

| Total | Classification |
|-------|----------------|
| ≥ 8 | STRONG |
| 6-7 | PLAUSIBLE |
| 4-5 | WEAK |
| ≤ 3 | REJECT |

### Programme Fit (deterministic)
- `programme_genre_overlap`: shared genres with programme
- `programme_theme_signal`: thematic overlap
- `domain_relationship`: affinity scores from programme films

### Programme Bet Selection
- Score ≥ 8 AND event feasibility = 2
- Highest total, tiebreak: different domain, highest affinity, highest members

### Falsifiable Hypothesis
- ONE specific direction
- ONE concrete experiment
- ONE reason
- ONE falsifiable hypothesis with success criterion

---

## RESULTS

### Genesis Cinema
```
200 raw → 153 evidence → 98 feasibility → 51 STRONG, 47 PLAUSIBLE, 102 REJECT
Programme Bet: Unloved (artist) — score=10, affinity=0.901
```

### Prince Charles Cinema
```
150 raw → 150 evidence → 100 feasibility → 50 STRONG, 50 PLAUSIBLE, 50 REJECT
Programme Bet: What Remains (tv_show) — score=9, affinity=0.960
```

### Cross-Context
- **Same entity:** False
- **Same domain:** False

---

## WHAT'S GENUINELY NEW vs M12.4

| Component | M12.4 | M12.5 |
|-----------|-------|-------|
| Scoring | 5 components (programmability, testability, specificity, feasibility, differentiation) | 5 components (entity_fit, event_feasibility, programme_fit, testability, differentiation) |
| Programme fit | Domain-driven | Entity-specific: supporting_films, support_count, support_ratio |
| Feasibility | Vague partnerships OK | Reject: vague, impossible rights, no concrete format, single weak film |
| Programme Bet | ONE direction + ONE experiment + ONE reason | + ONE falsifiable hypothesis with success criterion |
| Genesis | 180 STRONG, Bet=What Remains | 51 STRONG, Bet=Unloved (artist) |
| Prince Charles | 136 STRONG, Bet=What Remains | 50 STRONG, Bet=What Remains (tv_show) |
| Same entity | True | False |
| Same domain | True | False |

---

## KEY IMPROVEMENTS

1. **Discriminative filters:** 102 REJECT for Genesis, 50 REJECT for Prince Charles
2. **Different entities:** Genesis=Unloved, Prince Charles=What Remains
3. **Different domains:** artist vs tv_show
4. **Falsifiable hypothesis:** Each Programme Bet has success criterion and falsification
5. **No free points:** Differentiation requires genuine novelty, not just "non-film"

---

**Status:** COMPLETE