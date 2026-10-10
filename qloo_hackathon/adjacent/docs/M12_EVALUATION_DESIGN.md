# M12: Evaluation Design

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Goal

Prove whether Qloo provides cultural information that a normal film-metadata/content baseline does not provide.

---

## Design

### Two Systems Compared

**A. BASELINE (Metadata-Only)**
- Uses: title, year, genre inference from title patterns
- Does NOT use Qloo
- Answers: "What programming directions would a normal metadata system discover?"

**B. QLOO / ADJACENT**
- Uses: Full Adjacent pipeline
- Resolution → Taste DNA → Domain Selection → Cross-domain Expansion → Cohort Ranking → Programme Bet
- Answers: "What cultural adjacency does Qloo reveal?"

### Same Input
Both systems receive identical programme film lists.

---

## Evaluation Contexts

10 real programme contexts from independent cinemas:

| # | Venue | City | Films | Description |
|---|-------|------|-------|-------------|
| 1 | ICA | London | 6 | Contemporary arthouse and experimental |
| 2 | Curzon Soho | London | 6 | World cinema and arthouse mainstream |
| 3 | Genesis Cinema | London | 5 | Community cinema, arthouse + mainstream |
| 4 | Phoenix Cinema | Leicester | 5 | Independent community cinema |
| 5 | Prince Charles Cinema | London | 5 | Repertory, classics and cult films |
| 6 | The Garden Cinema | London | 5 | Members' curated arthouse |
| 7 | Picturehouse Central | London | 5 | Arthouse mainstream |
| 8 | BFI Southbank | London | 5 | National film archive, world cinema |
| 9 | Ritzy Brixton | London | 5 | Community-focused arthouse |
| 10 | Tyneside Cinema | Newcastle | 5 | Independent cultural cinema |

---

## Metrics

### 1. Cross-Domain Discovery
How many top opportunities come from domains unavailable to the baseline?

### 2. Novelty
How different are the Qloo opportunities from the programme's existing film metadata profile?

### 3. Overlap
How much do baseline and Qloo top-k opportunities overlap?

### 4. Signal Strength
For Qloo opportunities: programme adjacency, cohort breadth, Qloo affinity, evidence status.

### 5. Domain Diversity
How many distinct cultural domains does Qloo expose beyond film-only metadata?

### 6. Decision Difference
For how many programme contexts does Qloo produce a materially different programming direction?

**Definition of "materially different":** Qloo discovers at least one non-film domain (artist, book, brand, tv_show, podcast, destination) that the baseline cannot access.

---

## What We Do NOT Measure

- Predictive accuracy (no attendance labels)
- Audience growth (no attendance data)
- Conversion rates (no ticket sales data)
- Revenue impact (no financial data)

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE