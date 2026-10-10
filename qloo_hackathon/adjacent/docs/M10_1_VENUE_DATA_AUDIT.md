# M10.1: Venue Data Audit

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report audits the M9 corpus venue data integrity.

**Key Finding:** The M9 corpus has 10 unique venue_ids mapping to 10 distinct Cinema Context venues. Each venue_id maps to exactly one venue_name and one city. The corpus is internally valid.

---

## M9 Corpus Venue Analysis

### Total Records

- **Total screenings:** 20,628
- **Unique venue_ids:** 10
- **Unique venue_names:** 9 (two venues share the name "Luxor")

### Venue ID → Venue Name Mapping

| Venue ID | Venue Name | City | Status |
|----------|------------|------|--------|
| B000018 | Nöggerath | Amsterdam | ✅ VERIFIED |
| B000027 | Rialto | Amsterdam | ✅ VERIFIED |
| B000118 | Apollo | Den Haag | ✅ VERIFIED |
| B000153 | Olympia | Den Haag | ✅ VERIFIED |
| B000170 | Thalia | Den Haag | ✅ VERIFIED |
| B000693 | Luxor | Leiden | ✅ VERIFIED |
| B000924 | Luxor | Rotterdam | ✅ VERIFIED |
| B000940 | Prinses Theater | Rotterdam | ✅ VERIFIED |
| B001057 | Flora | Utrecht | ✅ VERIFIED |
| B001062 | Rembrandt | Utrecht | ✅ VERIFIED |

### Venue ID → City Mapping

| Venue ID | City | Status |
|----------|------|--------|
| B000018 | Amsterdam | ✅ VERIFIED |
| B000027 | Amsterdam | ✅ VERIFIED |
| B000118 | Den Haag | ✅ VERIFIED |
| B000153 | Den Haag | ✅ VERIFIED |
| B000170 | Den Haag | ✅ VERIFIED |
| B000693 | Leiden | ✅ VERIFIED |
| B000924 | Rotterdam | ✅ VERIFIED |
| B000940 | Rotterdam | ✅ VERIFIED |
| B001057 | Utrecht | ✅ VERIFIED |
| B001062 | Utrecht | ✅ VERIFIED |

---

## Uniqueness Checks

### 1. venue_id → venue_name uniqueness

**Result:** ✅ PASS

Each venue_id maps to exactly one venue_name:
- B000018 → Nöggerath
- B000027 → Rialto
- B000118 → Apollo
- B000153 → Olympia
- B000170 → Thalia
- B000693 → Luxor (Leiden)
- B000924 → Luxor (Rotterdam)
- B000940 → Prinses Theater
- B001057 → Flora
- B001062 → Rembrandt

### 2. venue_id → city uniqueness

**Result:** ✅ PASS

Each venue_id maps to exactly one city.

### 3. Duplicate venue records

**Result:** ✅ PASS

No duplicate venue records found. Each venue_id appears exactly once in the venue mapping.

### 4. Screening counts by venue

| Venue Name | Screenings | Films |
|------------|------------|-------|
| Luxor (combined) | 3,985 | 2,795 |
| Olympia | 2,551 | 2,372 |
| Prinses Theater | 2,389 | 2,181 |
| Flora | 2,083 | 1,773 |
| Thalia | 2,058 | 1,850 |
| Nöggerath | 2,055 | 1,677 |
| Apollo | 1,961 | 1,581 |
| Rialto | 1,798 | 1,003 |
| Rembrandt | 1,748 | 1,562 |

**Note:** "Luxor" appears as two venues (Leiden and Rotterdam). The combined count is 3,985 screenings.

---

## Comparison with M10 Venue Validation

### M10 Venue Validation (INVALID)

The M10 venue_identity_validation.csv had WRONG venue IDs:

| Venue Name | M10 ID (WRONG) | Correct ID |
|------------|----------------|------------|
| Rialto | B000023 | B000027 |
| Flora | B000077 | B001057 |
| Olympia | B000094 | B000153 |
| Nöggerath | B000069 | B000018 |
| Apollo | B000011 | B000118 |
| Rembrandt | B000094 | B001062 |
| Prinses Theater | B000023 | B000940 |
| Thalia | B000094 | B000170 |
| Luxor (Leiden) | B000077 | B000693 |
| Luxor (Rotterdam) | B000094 | B000924 |

**Status:** ❌ INVALID — IDs were manually assigned and incorrect

### M10.1 Venue Validation (CORRECT)

The M10.1 venue_identity_validation.csv has CORRECT venue IDs from Cinema Context SPARQL:

| Venue Name | Correct ID | Source |
|------------|------------|--------|
| Rialto | B000027 | Cinema Context SPARQL |
| Flora | B001057 | Cinema Context SPARQL |
| Olympia | B000153 | Cinema Context SPARQL |
| Nöggerath | B000018 | Cinema Context SPARQL |
| Apollo | B000118 | Cinema Context SPARQL |
| Rembrandt | B001062 | Cinema Context SPARQL |
| Prinses Theater | B000940 | Cinema Context SPARQL |
| Thalia | B000170 | Cinema Context SPARQL |
| Luxor (Leiden) | B000693 | Cinema Context SPARQL |
| Luxor (Rotterdam) | B000924 | Cinema Context SPARQL |

**Status:** ✅ VERIFIED — IDs from authoritative source

---

## Internal Validity Check

### Question: Are the 20,628 records genuinely distributed across ten distinct Cinema Context venue identities?

**Answer:** ✅ YES

**Evidence:**

1. **10 unique venue_ids** in the corpus
2. **Each venue_id maps to exactly one venue_name** (no duplicates)
3. **Each venue_id maps to exactly one city** (no duplicates)
4. **Venue IDs match Cinema Context SPARQL results** (verified)
5. **Screening counts are reasonable** (1,748 to 3,985 per venue)
6. **No impossible venue/name combinations** found

**Conclusion:** The 20,628 records are genuinely distributed across 10 distinct Cinema Context venues. The corpus is internally valid.

---

## Recommendations

### For M10.1

1. **Use correct venue IDs** from Cinema Context SPARQL
2. **Do not use M10 venue validation** (had wrong IDs)
3. **Use M10.1 venue validation** (correct IDs)

### For Future Milestones

1. **Never manually assign venue IDs** — always query authoritative source
2. **Verify venue_id → venue_name uniqueness** — one ID → one name
3. **Document source of venue IDs** — SPARQL query, timestamp, etc.

---

## Conclusion

The M9 corpus is internally valid:
- ✅ 10 unique venue_ids
- ✅ Each venue_id maps to exactly one venue_name
- ✅ Each venue_id maps to exactly one city
- ✅ Venue IDs match Cinema Context SPARQL results
- ✅ No duplicate or impossible venue records

**Status:** The 20,628 records are genuinely distributed across 10 distinct Cinema Context venues.

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE