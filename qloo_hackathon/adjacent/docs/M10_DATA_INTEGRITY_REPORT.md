# M10: Data Integrity Report

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report documents the data integrity issues found in M9 and the corrections made in M10.

**Key Issues Found:**
1. Hardcoded API key in source code
2. Invalid Qloo validation methodology
3. Missing film year data
4. Weak provenance tracking
5. Generated film IDs instead of stable identities

---

## Issue 1: Security — Hardcoded API Key

### Problem

The M9 Qloo validation script contained a hardcoded API key:

```python
QLOO_API_KEY = '<REDACTED - was hardcoded key>'
```

### Impact

- Key exposed in source code
- Key committed to git history
- Key may be compromised

### Resolution

1. Removed hardcoded key from `research/scripts/qloo_validation.py`
2. Updated script to load key from environment variable only
3. Added validation that key is set before running
4. Documented that key should be treated as compromised

### Status: ✅ RESOLVED

---

## Issue 2: Invalid Qloo Validation

### Problem

M9 Qloo validation claimed 100% hit rate based on flawed methodology:

- Only checked if Qloo returned a result
- Did not verify the result was the correct historical film
- Did not check year, IMDb ID, or other verification signals

### Evidence

Sample of mismatches from M9 validation:

| Historical Film | Qloo Entity | Issue |
|-----------------|-------------|-------|
| Work (1915) | Dirty Work | Different film |
| Golem, Le (1936) | The Limehouse Golem | 2016 film, not 1936 |
| Calino et le petit restaurant très bien (1913) | The Good, the Bad and the Ugly | Completely different |
| Satan Opium (1915) | The Omen | Completely different |

### Resolution

1. Marked M9 Qloo validation as INVALID
2. Built trusted film identity resolution (M10)
3. Tested 100 films with proper verification
4. Actual verified coverage: 2% (not 100%)

### Status: ✅ RESOLVED

---

## Issue 3: Missing Film Year

### Problem

The M9 dataset had `film_year` largely empty. The field was not populated from the source data.

### Impact

- Cannot verify film identity
- Cannot distinguish between films with same title
- Cannot do temporal analysis

### Resolution

1. Extract year from film title (e.g., "Film Name (1936)")
2. Use Qloo's `release_year` field for verification
3. Use IMDb/Wikidata for enrichment (if available)
4. Record source and provenance for each year value

### Status: ⚠️ PARTIALLY RESOLVED

- Year extraction from title implemented
- Qloo year verification implemented
- Full enrichment with IMDb/Wikidata pending

---

## Issue 4: Weak Provenance Tracking

### Problem

The M9 dataset used a generated `source_hash` derived from selected field values. This is not a proper source-document checksum.

### Impact

- Cannot reproduce data from source
- Cannot verify data integrity
- Cannot track transformations

### Resolution

1. Created proper provenance manifest:
   - Source: Cinema Context (University of Amsterdam)
   - Source URL: https://data.create.humanities.uva.nl/sparql
   - Retrieval timestamp
   - Query used
   - Query parameters
   - Parser version
   - Transformation version

2. Documented in `data/manifests/independent_cinema_programmes_2026-10-06_manifest.json`

### Status: ✅ RESOLVED

---

## Issue 5: Generated Film IDs

### Problem

The M9 dataset used generated row-specific `film_id` values (e.g., `CC-B000069-0`). These are not stable external identifiers.

### Impact

- Cannot link to external databases
- Cannot deduplicate across datasets
- Cannot track film identity

### Resolution

1. Created `data/processed/film_qloo_resolution.parquet` with proper identity fields:
   - `source_film_id`: Original film identifier from source
   - `film_title`: Film title
   - `film_year`: Film year (extracted from title)
   - `external_ids`: Dict of external IDs (IMDb, Wikidata)
   - `qloo_entity_id`: Qloo entity ID (if resolved)
   - `qloo_entity_name`: Qloo entity name
   - `qloo_entity_year`: Qloo entity year
   - `resolution_method`: How the resolution was done
   - `resolution_status`: VERIFIED/AMBIGUOUS/MISMATCH/UNRESOLVED
   - `confidence`: Confidence score (0.0-1.0)
   - `evidence`: List of evidence for resolution

### Status: ✅ RESOLVED

---

## Issue 6: Venue Identity Validation

### Problem

The M9 venue list and comments contained inconsistencies. Venue identities were not validated against authoritative sources.

### Impact

- Cannot verify venue locations
- Cannot link to external venue databases
- Cannot do geographic analysis

### Resolution

1. Created `data/venue_identity_validation.csv` with proper validation:
   - `venue_id`: Cinema Context venue ID
   - `venue_name`: Venue name
   - `city`: City
   - `country`: Country
   - `source_uri`: Cinema Context URI
   - `identity_status`: VERIFIED/AMBIGUOUS/UNRESOLVED
   - `evidence`: Evidence for identity
   - `notes`: Additional notes

2. All venues validated against Cinema Context SPARQL endpoint

### Status: ✅ RESOLVED

---

## Summary of Corrections

| Issue | M9 Status | M10 Status | Impact |
|-------|-----------|------------|--------|
| API Key Security | ❌ Hardcoded | ✅ Environment variable | Security |
| Qloo Validation | ❌ Invalid (100% claim) | ✅ Corrected (2% actual) | Accuracy |
| Film Year | ❌ Empty | ⚠️ Partially resolved | Data quality |
| Provenance | ❌ Weak | ✅ Proper manifest | Reproducibility |
| Film IDs | ❌ Generated | ✅ Stable identity | Data quality |
| Venue Identity | ❌ Unvalidated | ✅ Validated | Accuracy |

---

## Recommendations

### For Future Milestones

1. **Never hardcode API keys** — always use environment variables
2. **Always verify entity resolution** — don't assume fuzzy matches are correct
3. **Require evidence for claims** — document proof for every assertion
4. **Track provenance properly** — source, timestamp, query, parser version
5. **Use stable identifiers** — external IDs, not generated values

### For Qloo Integration

1. **Test Qloo on modern films** before concluding it's useful
2. **Build proper entity resolution** before measuring information gain
3. **Consider alternative approaches** for historical data
4. **Document limitations clearly** — what Qloo can and cannot do

---

## Conclusion

M10 found and corrected 6 major data integrity issues from M9. The most critical were:

1. **Security:** Hardcoded API key (now removed)
2. **Accuracy:** Invalid Qloo validation (now corrected)
3. **Data quality:** Missing film year and weak provenance (now addressed)

**Key Lesson:** Always verify entity resolution with multiple signals (title, year, IMDb ID) before making claims about data coverage or information gain.

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE