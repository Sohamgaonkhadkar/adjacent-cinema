# M13.1: Label Schema

**Date:** 2026-10-07

---

## CANONICAL OUTCOME SCHEMA

```
event_id:           string    Unique event identifier
venue_id:           string    Venue identifier
venue_name:         string    Human-readable venue name
city:               string    City name
event_date:         date      YYYY-MM-DD
film_or_event_id:   string    Film/event identifier
film_or_event_name: string    Human-readable name
domain:             enum      film | tv_show | artist | book | podcast
event_type:         enum      screening | themed_season | live_event | discussion
capacity:           int       Venue capacity (NULL if unavailable)
attendance:         int       Actual attendance (NULL if unavailable)
tickets_sold:       int       Tickets sold (NULL if unavailable)
occupancy_rate:     float     attendance / capacity (NULL if unavailable)
sell_through_rate:  float     tickets_sold / capacity (NULL if unavailable)
price:              float     Ticket price (NULL if unavailable)
programme_context_id: string  Link to Adjacent programme context
source_url:         string    Data source URL
source_dataset:     string    Dataset name
source_record_id:   string    Original record ID
join_status:        enum      VERIFIED | AMBIGUOUS | MISMATCH | UNRESOLVED
label_quality:      enum      DIRECT_OUTCOME | STRONG_PROXY | WEAK_PROXY | UNAVAILABLE
provenance:         string    How this record was obtained
```

---

## TARGET VARIABLE HIERARCHY

| Priority | Variable | Type | Definition | Source |
|----------|----------|------|------------|--------|
| 1 | attendance_count | int | People who attended | Kaggle, Poland |
| 2 | occupancy_rate | float | attendance / capacity | Kaggle |
| 3 | tickets_sold | int | Tickets sold | Kaggle |
| 4 | sell_through_rate | float | tickets_sold / capacity | Kaggle (derived) |
| 5 | sold_out | bool | All tickets sold | Apify |
| 6 | booking_count | int | Number of bookings | Not found |

**Do NOT mix these into one target.** Each represents a different measurement.

---

## JOIN STATUS DEFINITIONS

| Status | Definition |
|--------|-----------|
| VERIFIED | Exact match on stable identifier (IMDB ID, Qloo entity_id) |
| AMBIGUOUS | Multiple possible matches; requires disambiguation |
| MISMATCH | Identifier exists but doesn't match |
| UNRESOLVED | No identifier available for matching |

---

## WHAT NULL MEANS

NULL means **unavailable**, not zero.
- `attendance = NULL` → we don't know how many attended
- `attendance = 0` → nobody attended (different meaning)

**Do not estimate NULL values.**