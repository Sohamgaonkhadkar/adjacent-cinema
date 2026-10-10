# M13.2: Identifier Recovery

**Date:** 2026-10-07
**Status:** COMPLETE

---

## PHASE A: KAGGLE IDENTIFIER RECOVERY

### Search Conducted

| Source | Searched | Mapping Found |
|--------|----------|---------------|
| Kaggle dataset page | Data card, description | NO — codes described as "encoded anonymized locations" |
| Kaggle discussions (5 threads) | All 5 threads | NO — users ask about codes, no answer from creator |
| Kaggle notebooks (20) | EDA, XGBoost, forecasting | NO — all notebooks treat codes as opaque integers |
| GitHub repos using dataset | 5+ repos | NO — all use codes as categorical features |
| Creator profile (Möbius) | Profile, other datasets | NO — creator has not revealed source |
| Research papers citing dataset | 0 papers found | N/A |
| Community mappings | None found | N/A |

### Evidence About Dataset Origin

| Evidence | Finding |
|----------|---------|
| ticket_price range | 32–637 (local currency, likely Iranian Rial or Turkish Lira) |
| total_sales range | 20k–1.26B (consistent with Iranian Rial) |
| capacity range | 1–4,250 |
| Date range | Feb 2018 – Nov 2018 |
| film_code range | ~80 unique films |
| cinema_code range | ~20 unique cinemas |
| Related datasets on Kaggle | Persian Cinema dataset appears in related searches |
| Creator name | Möbius (no public identity) |

### Conclusion

**UNRESOLVED.** The Kaggle Cinema Tickets dataset uses intentionally anonymized identifiers. No public mapping exists. The dataset likely originates from an Iranian or Turkish cinema chain based on currency evidence. The anonymization is deliberate and irreversible without the original data provider.

### Identifier Recovery Status

| Field | Status | Coverage |
|-------|--------|----------|
| film_code → film_title | UNRESOLVED | 0% |
| film_code → year | UNRESOLVED | 0% |
| film_code → IMDB ID | UNRESOLVED | 0% |
| cinema_code → venue_name | UNRESOLVED | 0% |
| cinema_code → city | UNRESOLVED | 0% |

**Row-level join coverage: 0%**

The dataset cannot be joined to Qloo entities. Period.

---

## PHASE C: UK CINEMA PROXY DATA

### Publicly Available Signals

| Venue | Source | Signal | Data Available |
|-------|--------|--------|----------------|
| Prince Charles Cinema | princecharlescinema.com | sold_out flag | Film title, year, format, showtime, sold_out, booking URL |
| Genesis Cinema | genesiscinema.co.uk | showtime list | Film title, showtime (no explicit sold_out flag visible) |
| ICA Cinema | ica.art.org | showtime list | Film title, showtime, booking |
| Picturehouse Cinemas | picturehouses.com | sold_out (via booking) | Film title, showtime, availability |

### Prince Charles Cinema — Current Data Structure

```html
<span class="sold-out">Sold Out</span> <!-- or -->
<a href="/booking/...">Book</a>
```

**Extractable fields:**
- Film title (from page heading)
- Year, duration, country, rating, genre (from metadata)
- Director, cast (from credits)
- Showtime date and time
- Format (35mm, 4K, 70mm, DCP)
- Sold-out status ("Sold Out" vs "Book")
- Booking URL
- Film URL (contains film ID)

### Signal Classification

| Signal | Classification | Definition |
|--------|---------------|------------|
| sold_out = True | STRONG PROXY | "The venue's public booking system reported this screening as sold out" |
| sold_out = False | DESCRIPTIVE | "Tickets were available at time of observation" |
| Booking URL exists | DESCRIPTIVE | "Screening was listed for advance booking" |
| Showtime listed | DESCRIPTIVE | "Screening was scheduled" |

**CRITICAL: sold_out means "reported sold out by venue", NOT "attendance was high".**

A sold-out screening with 50 seats is different from a sold-out screening with 300 seats.

---

## JOIN FEASIBILITY: UK PROXY → QLOO

| Join Key | UK Proxy Has | Qloo Has | Feasibility |
|----------|-------------|----------|-------------|
| Film title | YES | YES | GOOD — exact or fuzzy match |
| Film year | YES | YES | GOOD |
| IMDB ID | NO (not on PCC page) | YES | UNAVAILABLE (would need IMDB lookup) |
| Venue name | YES | N/A | OK — for context |
| Date | YES | N/A | OK — for temporal split |

**Qloo resolution approach:**
1. Extract film title + year from Prince Charles website
2. Resolve via Adjacent's EntityResolver (/search with title + year)
3. Run Qloo pipeline on resolved entity
4. Store Qloo evidence alongside sold_out proxy

**Expected resolution rate:** ~70-80% (known films with IMDB IDs)

---

## RECOMMENDED BENCHMARK APPROACH

Since Kaggle is blocked, build a UK proxy benchmark:

1. Scrape Prince Charles Cinema showtimes (weekly snapshot)
2. Extract: film, showtime, format, sold_out
3. Resolve each film to Qloo entity
4. Run Adjacent pipeline → get cultural evidence scores
5. Store: film + Qloo evidence + sold_out proxy + venue context
6. After sufficient observations: test whether Qloo affinity predicts sold_out

**Timeline:** Need 3-6 months of weekly snapshots for meaningful data.

**Status:** NOT_YET_IMPLEMENTED — requires scraper development.

---

**Status:** COMPLETE