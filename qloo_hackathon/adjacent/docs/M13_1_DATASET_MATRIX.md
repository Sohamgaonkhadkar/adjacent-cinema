# M13.1: Dataset Matrix

**Date:** 2026-10-07

---

## OUTCOME LABEL AVAILABILITY

| Source | Target | Granularity | Venue-level | Joinable to Qloo | Records | Access |
|--------|--------|-------------|-------------|-----------------|---------|--------|
| Kaggle Cinema Tickets | tickets_sold, occupancy | Screening | YES (anonymized) | **NO** (codes only) | 142,524 | Open |
| BFI Weekend Box Office | Gross revenue | Film (national) | NO | Partial (film title) | Weekly | Open |
| Cinema Context | **NONE** | Screening | YES | YES (IMDB) | 100k+ | Open |
| Poland show-level | Attendance | Screening | YES | Unknown | 179,103 | **Proprietary** |
| LUMIERE | National admissions | Film (national) | NO | Partial | 69k+ titles | Open |
| Apify Scraper | sold_out (binary) | Screening | YES | YES (film title) | Ongoing | Commercial |

---

## CLASSIFICATION

### DIRECT OUTCOME SOURCES
- Kaggle Cinema Tickets (tickets_sold, occu_perc)
- Poland show-level (attendance) — UNAVAILABLE

### STRONG PROXY SOURCES
- Apify sold_out flag

### WEAK PROXY SOURCES
- BFI gross revenue (national, not venue-level)

### NOT OUTCOME LABEL SOURCES
- Cinema Context (metadata only — no attendance)
- BFI Statistical Yearbook (aggregate)
- LUMIERE (national aggregate)
- Statista (aggregate, paywall)

---

## BEST AVAILABLE OPTION

**Kaggle Cinema Tickets** is the only publicly accessible dataset with:
- Screening-level granularity
- Real attendance counts
- Occupancy rates
- Capacity data
- Multiple venues

**Fatal limitation:** Anonymized film_codes and cinema_codes prevent joining to Qloo entities.

---

## QLOO RESOLUTION FEASIBILITY

| Source | Film title | IMDB ID | Year | Qloo resolution |
|--------|-----------|---------|------|----------------|
| Kaggle | ❌ (code only) | ❌ | ❌ | NOT POSSIBLE |
| BFI | ✅ | ❌ | ✅ | PARTIAL (fuzzy) |
| Cinema Context | ✅ | ✅ | ✅ | EXCELLENT |
| Apify | ✅ | ❌ | ✅ | GOOD |

**Best join path:** Cinema Context (IMDB IDs → Qloo entities), but Cinema Context has NO outcome data.

**Best outcome path:** Kaggle Cinema Tickets, but cannot join to Qloo.

**These two paths currently do not intersect.**