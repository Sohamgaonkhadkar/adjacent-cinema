# M13.3: Proxy Validation Report

**Date:** 2026-10-07

---

## PROXY DEFINITION

### SOLD_OUT (STRONG PROXY)

**Definition:** "Venue's public booking system reported no tickets remaining."

**What it IS:**
- Binary proxy for demand ≥ capacity
- Observable, verifiable, publicly documented
- Based on venue's own system

**What it is NOT:**
- NOT attendance (some sold-out events have no-shows)
- NOT quality (sold out ≠ good)
- NOT universal (different venues have different systems)

**Strengths:**
- Observable (anyone can check)
- Verifiable (venue's own system)
- Consistent (same venue, same system)
- Timely (real-time availability)

**Weaknesses:**
- Binary (no "how sold out")
- Venue-specific (different thresholds)
- Temporal (sold out at T≠sold out at T+1)
- Incomplete (not all venues expose)

### AVAILABLE (DESCRIPTIVE ONLY)

**Definition:** "Tickets were available at time of observation."

**What it IS:**
- Descriptor of ticket state
- NOT a proxy for low demand (could be 90% sold)

**What it is NOT:**
- NOT evidence of low interest
- NOT evidence of poor quality

---

## PROXY QUALITY ASSESSMENT

| Criterion | SOLD_OUT | AVAILABLE |
|-----------|----------|-----------|
| Observable | ✅ Yes | ✅ Yes |
| Verifiable | ✅ Yes | ✅ Yes |
| Consistent | ✅ Same venue system | ✅ Same venue system |
| Timely | ✅ Real-time | ✅ Real-time |
| Binary | ⚠️ Yes (no gradient) | ⚠️ Yes |
| Venue-specific | ⚠️ Yes | ⚠️ Yes |

---

## FIRST PROXY OBSERVATIONS

| Metric | Value |
|--------|-------|
| Total screenings | 667 |
| SOLD_OUT (STRONG_PROXY) | 20 (3.0%) |
| AVAILABLE (DESCRIPTIVE_ONLY) | 647 (97.0%) |
| UNKNOWN | 0 |

**Note:** 3.0% sold-out rate is reasonable for a repertory cinema showing niche content.

---

## ML READINESS

**Status:** NOT_ML_READY

**Why:** First collection. Need:
- 3-6 months of temporal data
- Multiple observations per film
- State change observations (Book → Sold Out)

**After sufficient data:**
- Evaluate: Does Qloo affinity correlate with sold_out rate?
- If yes: Proxy validated
- If no: Negative result (also valuable)

---

## COMPARISON WITH M13.2 ASSESSMENT

| M13.2 Conclusion | M13.3 Status |
|------------------|--------------|
| PCC exposes sold_out | ✅ Verified (20 sold out) |
| PCC has booking URLs | ✅ Verified (all 667) |
| PCC has film metadata | ✅ Verified (title, year, format) |
| PCC is scrapable | ✅ Verified (stable HTML) |
| First collection needed | ✅ Done (667 screenings) |
| Temporal tracking needed | ⏳ In progress (weekly collection) |

---

**Status:** Proxy VALIDATED as observable. First data collected. Awaiting temporal data for signal evaluation.