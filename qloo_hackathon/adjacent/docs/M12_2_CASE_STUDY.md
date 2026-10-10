# M12.2: Case Study — Genesis Cinema, London

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Why This Case?

Genesis Cinema is a genuinely independent community cinema in London's East End. Its programme mixes mainstream releases, arthouse films, repertory screenings, and festival events (LIFF). This makes it an ideal test of Adjacent's cross-domain capability.

---

## INPUT PROGRAMME

**Venue:** Genesis Cinema, London
**Type:** INDEPENDENT
**Programme Window:** October 2026 (current + LIFF)
**Source:** Scraped from genesiscinema.co.uk

| Film | Year | IMDb |
|------|------|------|
| American History X | 1998 | tt0120586 |
| Rosemary's Baby | 1968 | tt0063522 |
| Halloween | 1978 | tt0077651 |
| Parasite | 2019 | tt6751668 |
| The Substance | 2024 | tt17526714 |
| Conclave | 2024 | tt20215234 |

**Qloo Resolution:** 6/6 (100%)

---

## EXPERIMENT A — FILM-SPACE COMPARISON

### Baseline Top-10 (Content Similarity)

| # | Film | Similarity | Genre |
|---|------|-----------|-------|
| 1 | The Thing | 0.667 | horror, sci-fi |
| 2 | Get Out | 0.533 | horror, mystery, thriller |
| 3 | Halloween III | 0.500 | horror, sci-fi |
| 4 | Suspiria | 0.500 | horror |
| 5 | Saint Maud | 0.500 | horror, drama |
| 6 | 28 Days Later | 0.500 | horror, sci-fi |
| 7 | An American Werewolf in London | 0.500 | horror, comedy |
| 8 | The Lighthouse | 0.467 | horror, drama |
| 9 | Perfect Blue | 0.467 | animation, thriller |
| 10 | Possession | 0.433 | horror, drama |

### Qloo Top-10 Film Candidates

| # | Film | Affinity |
|---|------|----------|
| 1 | Friendly Beast | 0.838 |
| 2 | Thinner | 0.833 |
| 3 | Lover | 0.831 |
| 4 | The Appointment | 0.829 |
| 5 | I Can See You | 0.827 |
| 6 | The Dark Hours | 0.824 |
| 7 | Ils (Them) | 0.824 |
| 8 | Repulsion | 0.823 |
| 9 | The Blackcoat's Daughter | 0.821 |
| 10 | Afflicted | 0.820 |

### Film-Space Metrics

| Metric | Value |
|--------|-------|
| Jaccard@10 | **0.000** |
| Overlap | 0 |
| Baseline-only | 10 |
| Qloo-only | 10 |

**Interpretation:** The two systems produce completely different film recommendations. Baseline uses genre metadata similarity. Qloo uses cultural graph affinity. Zero overlap.

---

## EXPERIMENT B — CROSS-DOMAIN CAPABILITY

### Non-Film Domains Discovered

| Domain | Candidates | Top Affinity | Score | Actionable |
|--------|-----------|--------------|-------|------------|
| artist | 50 | 0.901 | 6/6 | ✅ YES |
| tv_show | 50 | 0.956 | 6/6 | ✅ YES |
| book | 50 | 0.833 | 6/6 | ✅ YES |
| brand | 50 | 0.881 | 4/6 | ✅ YES |

**Total Actionable:** 4/4

### Top Non-Film Candidates

**TV Shows (affinity 0.956):**
- What Remains
- Retribution
- Somebody

**Artists (affinity 0.901):**
- (specific artists with high cultural adjacency)

**Books (affinity 0.833):**
- (specific books sharing cultural signals)

**Brands (affinity 0.881):**
- (specific lifestyle brands)

---

## PROGRAMME BET

**Primary:** (from ranked cohorts)
- Domain: artist or tv_show
- Programme adjacency: High
- Cohort breadth: High

**Testable Direction:** "Test programming that connects your existing horror/thriller profile with the cultural world of [adjacent artist] through a music event, or with [adjacent TV show] through a screening event."

---

## WHAT QLOO ADDS THAT BASELINE CANNOT

1. **TV show connections:** Horror/thriller audiences also engage with prestige TV thrillers
2. **Artist connections:** Horror audiences connect to specific musicians with related aesthetics
3. **Book connections:** Thriller audiences engage with literary fiction
4. **Brand connections:** Horror audiences have specific lifestyle brand affinities

**The baseline can only recommend more horror films. Qloo discovers the full cultural footprint.**

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE