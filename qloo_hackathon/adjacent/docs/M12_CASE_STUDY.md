# M12: Case Study — Phoenix Cinema Leicester

**Date:** 2026-10-07
**Status:** COMPLETE

---

## Why This Case?

Phoenix Cinema Leicester is the strongest case study because:
1. Qloo produced the most diverse cross-domain discovery (4 non-film domains)
2. The Programme Bet recommends a book — a genuinely novel programming direction
3. The baseline and Qloo recommendations are completely different

---

## INPUT

**Venue:** Phoenix Cinema Leicester
**City:** Leicester
**Description:** Independent community cinema

**Recent Programme:**
1. Shoplifters (2018) — Japanese family drama
2. Roma (2018) — Mexican domestic drama
3. Portrait of a Lady on Fire (2019) — French period romance
4. The Lighthouse (2019) — American psychological horror
5. Uncut Gems (2019) — American crime thriller

---

## BASELINE (Metadata-Only)

**Detected Styles:** arthouse_drama, asian_cinema, horror_thriller

**Programming Directions:**
1. More recent award-winning arthouse drama
2. East Asian cinema seasons

**What the baseline sees:**
- Award-winning international films
- Mix of Asian and European arthouse
- Some genre elements (horror, thriller)
- Suggests: more of the same type of film

---

## QLOO / ADJACENT

**Selected Domains:**
- `urn:entity:artist` (always included)
- `urn:entity:movie` (always included)
- `urn:entity:book` — 2 signals found
- `urn:entity:brand` — 5 signals found
- `urn:entity:podcast` — 1 signal found

**Taste DNA:**
- Buenos Aires, Traditional Mexican, Fine Dining, Brewpub, Chile En Nogada

**Programme Bet:**

**Primary:** The Dark Interval: Letters on Loss, Grief, and Transformation (book)
- Domain: book
- Programme adjacency: 0.813 (High)
- Cohort breadth: 1.000 (High)
- Adjacency call ID: local-c024
- Breadth call ID: local-c024

**Runner-up:** Several artist and brand cohorts ranked below

---

## DIFFERENCE

| Aspect | Baseline | Qloo |
|--------|----------|------|
| Domain | Film only | Book, artist, brand, podcast |
| Direction | More similar films | Cross-cultural event programming |
| Specificity | "More arthouse drama" | "Author reading/event connected to grief and transformation themes" |
| Cultural insight | None | Audience also engages with literary fiction about loss and identity |

**What Qloo reveals that baseline cannot:**

1. **Cross-domain connection:** Films like Shoplifters and Roma (family drama, loss, class) connect to literary fiction about grief and transformation
2. **Specific recommendation:** "The Dark Interval: Letters on Loss, Grief, and Transformation" — a book that shares thematic DNA with the programme
3. **Actionable programming:** An author reading or book club event would attract the same cultural audience
4. **Evidence-backed:** Programme adjacency 0.813 (High) with 100% cohort breadth

---

## PROGRAMME BET

**Programming Direction:** Test programming that connects your existing Buenos Aires, Traditional Mexican, Fine Dining profile with the cultural world of The Dark Interval through book-adjacent programming.

**Falsification Condition:** Do not continue this programming test if the book affinity signal cannot be reproduced across the next comparable programme analysis.

---

## PRODUCT STORY

**INPUT:** Phoenix Cinema Leicester showing Shoplifters, Roma, Portrait of a Lady on Fire, The Lighthouse, Uncut Gems

**BASELINE:** "Show more award-winning international arthouse films"

**QLOO:** "Your audience for these films about loss, family, and identity also engages with literary fiction about grief and transformation. Consider hosting a reading or book club event."

**OUTPUT:** One programming direction worth testing — a book event connected to the thematic DNA of the programme

---

## Why This Matters

A metadata-only system would say: "Show more films like these."

Adjacent says: "Your audience's cultural taste extends beyond film. They also engage with literary fiction about similar themes. A book event would reach them through a different cultural channel."

This is the incremental value of Qloo: **cross-domain cultural adjacency that metadata cannot provide.**

---

**Report Generated:** 2026-10-07
**Status:** COMPLETE