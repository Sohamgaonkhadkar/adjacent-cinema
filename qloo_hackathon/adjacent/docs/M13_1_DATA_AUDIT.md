# M13.1: Real Outcome Dataset Audit

**Date:** 2026-10-07
**Status:** COMPLETE

---

## PHASE 1: DATASET DISCOVERY

### Candidate Sources Audited

| # | Source | Type | Country | Granularity | Attendance? | License | Usable? |
|---|--------|------|---------|-------------|-------------|---------|---------|
| 1 | Kaggle Cinema Tickets | Screening-level sales | Unknown (anonymized) | Film × Cinema × Date | **YES** — tickets_sold, occu_perc, capacity | CC BY-NC-SA 4.0 | **BEST** |
| 2 | BFI Weekend Box Office | National box office | UK | Film-level (national) | Gross revenue only | Open (BFI) | NOT OUTCOME (no venue) |
| 3 | BFI Statistical Yearbook | Aggregate stats | UK | National/annual | Aggregate admissions | Open (BFI) | NOT OUTCOME (aggregate) |
| 4 | Cinema Context | Historical screenings | Netherlands | Venue × Film × Date | **NO** — metadata only | Open (LOD) | NOT OUTCOME LABEL SOURCE |
| 5 | Poland show-level (paper) | Screening-level | Poland | Film × Cinema × Date | **YES** — tickets_sold per show | Proprietary (unavailable) | UNAVAILABLE |
| 6 | LUMIERE (European Observatory) | Film admissions | 30 European markets | Film × Country | National admissions | Open | NOT OUTCOME (no venue) |
| 7 | UK Showtimes Scraper (Apify) | Showtimes | UK & Ireland | Film × Venue × Date | **PROXY** — sold_out flag | Commercial scraper | WEAK PROXY |
| 8 | Statista (UK Cinema Admissions) | National aggregate | UK | National/annual | Aggregate millions | Paywall | NOT OUTCOME (aggregate) |
| 9 | Omdia Cinema Database | Global box office | Global | National/quarterly | Aggregate | Commercial | UNUSABLE (paywall) |
| 10 | European Audiovisual Observatory | Continental stats | Europe | National/annual | Aggregate | Open | NOT OUTCOME (aggregate) |

---

### Detailed Assessment

#### SOURCE 1: Kaggle Cinema Tickets (BEST CANDIDATE)

- **URL:** https://www.kaggle.com/datasets/arashnic/cinema-ticket
- **Records:** 142,524 screening-level observations
- **Period:** Feb 2018 – Nov 2018 (8 months)
- **Venues:** Multiple cinemas, anonymized codes
- **Fields:** film_code, cinema_code, total_sales, tickets_sold, tickets_out, show_time, occu_perc, ticket_price, ticket_use, capacity, date, month, quarter, day
- **Target:** tickets_sold (count), occu_perc (occupancy rate)
- **License:** CC BY-NC-SA 4.0
- **Strengths:** Screening-level, real attendance, occupancy, capacity
- **Weaknesses:** Anonymized venues (no real names), anonymized films (codes not titles), 2018 only, unknown country, no genre metadata

**Outcome labels:** DIRECT OUTCOME (tickets_sold, occupancy_rate)

#### SOURCE 2: BFI Weekend Box Office

- **URL:** https://www.bfi.org.uk/industry-data-insights/weekend-box-office-figures
- **Records:** Weekly, top 15 + all UK releases
- **Period:** 2009–2026 (weekly)
- **Fields:** Film title, weekend gross, total gross, weeks on release
- **Target:** Box office gross (revenue, not attendance)
- **License:** Open (BFI)
- **Strengths:** UK-specific, long time series, film titles available
- **Weaknesses:** Film-level (no venue), national aggregate, revenue not attendance

**NOT AN OUTCOME LABEL SOURCE** for venue-level programming decisions.

#### SOURCE 4: Cinema Context

- **URL:** https://www.cinemacontext.nl/
- **Records:** 100,000+ screenings
- **Period:** 1895–present
- **Country:** Netherlands
- **Fields:** Venue, film, screening date, programme, capacity, IMDB links
- **Target:** **NONE** — no attendance, ticket sales, or occupancy data
- **License:** Open (Linked Open Data)
- **Strengths:** Rich metadata, venue-level, IMDB identifiers, historical depth
- **Weaknesses:** **NO OUTCOME DATA**

**NOT AN OUTCOME LABEL SOURCE.** Metadata only.

#### SOURCE 5: Poland Show-Level (Research Paper)

- **Paper:** "Forecasting Cinema Attendance at the Movie Show Level" (Baranowski et al., 2020)
- **Records:** 179,103 shows
- **Period:** Oct 2016 – Mar 2018 (19 months)
- **Venues:** 25 cinemas in 24 Polish cities
- **Target:** Attendance (tickets sold per show)
- **Availability:** **PROPRIETARY** — data from a private cinema network, not publicly released
- **Strengths:** Show-level, real attendance, multiple venues
- **Weaknesses:** Cannot access

#### SOURCE 7: UK & Ireland Cinema Showtimes Scraper

- **URL:** https://apify.com/kerlvision/uk-ireland-cinema-showtimes-scraper
- **Fields:** cinema, venue, film, show_time, show_format, sold_out, booking_url, film_genre, venue_city
- **Target:** sold_out (binary indicator)
- **Availability:** Requires Apify account, commercial scraping
- **Strengths:** UK-specific, venue-level, current data, sold_out flag
- **Weaknesses:** sold_out is a WEAK PROXY (not attendance count), requires ongoing scraping, commercial tool

**STRONG PROXY** for sold-out status, but not a direct attendance count.

---

## PHASE 2: LABEL HIERARCHY

| Priority | Target | Definition | Available in |
|----------|--------|------------|--------------|
| 1 | attendance_count | Number of people who attended | Kaggle (tickets_sold), Poland (proprietary) |
| 2 | occupancy_rate | attendance / capacity | Kaggle (occu_perc) |
| 3 | tickets_sold | Tickets sold (may include no-shows) | Kaggle |
| 4 | sell_through_rate | tickets_sold / capacity | Kaggle (derivable) |
| 5 | sold_out | Binary: all tickets sold | Apify scraper |
| 6 | booking_count | Number of bookings | Not found in public data |

**Primary target:** `tickets_sold` (from Kaggle Cinema Tickets)
**Secondary target:** `occu_perc` (occupancy rate, from Kaggle)

---

## PHASE 3: JOIN FEASIBILITY

### Kaggle → Qloo Join

| Join Key | Kaggle Has | Qloo Has | Feasibility |
|----------|-----------|----------|-------------|
| Film title | **NO** — film_code only | YES — entity name | **BLOCKED** |
| Film year | **NO** | YES | **BLOCKED** |
| Venue name | **NO** — cinema_code only | N/A | N/A |
| Film identifiers | **NO** — anonymized codes | YES — entity_id, IMDB | **BLOCKED** |
| Date | YES | N/A | OK |

**Critical problem:** Kaggle Cinema Tickets uses anonymized film_codes and cinema_codes. Without a mapping to real film titles, we cannot join to Qloo entities.

**Verdict:** JOIN NOT FEASIBLE without additional data or reverse-engineering the codes.

### BFI → Qloo Join

| Join Key | BFI Has | Qloo Has | Feasibility |
|----------|---------|----------|-------------|
| Film title | YES | YES | PARTIAL — fuzzy matching needed |
| Film year | Implied (release year) | YES | OK |
| Venue | **NO** | N/A | N/A |

**Problem:** BFI data is national aggregate (no venue). Cannot join to venue-level Qloo analysis.

**Verdict:** JOIN NOT USEFUL for venue-level decisions.

### Cinema Context → Qloo Join

| Join Key | CC Has | Qloo Has | Feasibility |
|----------|--------|----------|-------------|
| Film title | YES | YES | GOOD |
| IMDB ID | YES | YES | **EXCELLENT** |
| Venue | YES | N/A | N/A |
| Date | YES | N/A | N/A |

**But:** Cinema Context has NO outcome data (attendance/tickets).

**Verdict:** GOOD JOIN but NO TARGET VARIABLE.

---

## PHASE 4: CANONICAL OUTCOME SCHEMA

```json
{
  "event_id": "string — unique event identifier",
  "venue_id": "string — venue identifier",
  "venue_name": "string — human-readable venue name",
  "city": "string — city name",
  "event_date": "YYYY-MM-DD",
  "film_or_event_id": "string — film/event identifier",
  "film_or_event_name": "string — human-readable name",
  "domain": "film | tv_show | artist | book | podcast",
  "event_type": "screening | themed_season | live_event | discussion",
  "capacity": "integer — venue capacity (NULL if unavailable)",
  "attendance": "integer — actual attendance (NULL if unavailable)",
  "tickets_sold": "integer — tickets sold (NULL if unavailable)",
  "occupancy_rate": "float — attendance/capacity (NULL if unavailable)",
  "sell_through_rate": "float — tickets_sold/capacity (NULL if unavailable)",
  "price": "float — ticket price (NULL if unavailable)",
  "programme_context_id": "string — link to Adjacent programme context",
  "source_url": "string — data source URL",
  "source_dataset": "string — dataset name",
  "source_record_id": "string — original record ID",
  "join_status": "VERIFIED | AMBIGUOUS | MISMATCH | UNRESOLVED",
  "label_quality": "DIRECT_OUTCOME | STRONG_PROXY | WEAK_PROXY | UNAVAILABLE",
  "provenance": "string — how this record was obtained"
}
```

---

## ML READINESS ASSESSMENT

### Minimum Requirements

| Requirement | Status | Assessment |
|-------------|--------|------------|
| Real outcome labels | **PARTIAL** — Kaggle has tickets_sold but anonymized | ⚠️ |
| Stable event identifiers | **NO** — Kaggle uses anonymized codes | ❌ |
| Reproducible entity resolution | **NO** — cannot resolve film_code → Qloo entity | ❌ |
| Enough observations | **YES** — 142,524 rows in Kaggle | ✅ |
| Meaningful outcome variation | **YES** — occupancy ranges 0% to 100% | ✅ |
| No synthetic labels | **YES** — Kaggle data is real | ✅ |
| No target leakage | **POSSIBLE** — with temporal split | ✅ |
| Temporal train/test split | **YES** — 8 months of data | ✅ |
| Venue-level leakage control | **UNKNOWN** — anonymized venues | ⚠️ |

### Classification

**NOT_ML_READY**

**Reason:** The only publicly available dataset with real screening-level attendance (Kaggle Cinema Tickets) uses anonymized identifiers that cannot be joined to Qloo entities. We cannot connect cultural opportunity signals to actual outcomes.

### What Would Make It ML_READY

1. A dataset with real film titles + screening-level attendance + venue names
2. OR access to the Poland show-level dataset (proprietary)
3. OR a cinema chain partnership providing de-identified data with film titles
4. OR scraping sold_out data from UK independent cinemas (weak proxy only)

---

## MOST IMPORTANT RESEARCH QUESTION ANSWER

**D. There is currently insufficient real data to validate whether Qloo affinity predicts attendance.**

The available data has a fundamental join problem: the best outcome dataset (Kaggle) uses anonymized codes that prevent connection to Qloo entities. All other public datasets lack venue-level attendance data.

This is a genuine limitation, not a failure of the system. The Adjacent decision layer correctly identifies cultural opportunities using Qloo evidence. Whether those opportunities translate to attendance requires empirical data that is not currently publicly available at the required granularity.

---

## RECOMMENDED NEXT STEPS

1. **Short-term:** Use sold_out scraping (Apify) as a weak proxy for UK independent cinemas
2. **Medium-term:** Partner with a UK independent cinema chain for de-identified screening data
3. **Long-term:** Build a prospective data collection framework: record Adjacent recommendations → track actual outcomes

---

**Status:** COMPLETE