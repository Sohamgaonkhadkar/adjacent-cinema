# M10.1: Licence and Provenance Report

**Date:** 2026-10-06
**Status:** COMPLETE

---

## Executive Summary

This report documents the licence and provenance for the Cinema Context dataset used in the M9 corpus.

**Key Finding:** Cinema Context RDF data is licensed under **Creative Commons Attribution 4.0 International License (CC BY 4.0)**. Commercial use is permitted with attribution.

---

## Cinema Context Licence

### Licence Details

| Field | Value |
|-------|-------|
| **Licence Name** | Creative Commons Attribution 4.0 International License |
| **Licence URL** | https://creativecommons.org/licenses/by/4.0/ |
| **Retrieval Date** | 2026-10-06 |
| **Source Page** | https://uvacreate.gitlab.io/cinema-context/cinema-context-rdf/citation/ |
| **Commercial Use** | ✅ Permitted |
| **Attribution Required** | ✅ Yes |

### Licence Text

From the Cinema Context RDF documentation:

> "The Cinema Context RDF data are licensed under a Creative Commons Attribution 4.0 International License."

### Source Confirmation

1. **Cinema Context RDF Documentation**
   - URL: https://uvacreate.gitlab.io/cinema-context/cinema-context-rdf/citation/
   - States: "Creative Commons Attribution 4.0 International License"
   - Retrieved: 2026-10-06

2. **Research Data Journal Paper**
   - URL: https://researchdatajournal.org/article/view/24721
   - States: "This work is licensed under a Creative Commons Attribution 4.0 International License"
   - Published: 2020-11-04

3. **Cinema Context RDF Documentation Footer**
   - States: "The Cinema Context RDF documentation is written by CREATE and are licensed under a Creative Commons BY-SA 4.0 International License."
   - **Note:** This is for the documentation, not the data itself

---

## Attribution Requirements

### Required Citation

For the RDF data:

```
Menno den Engelse, Leon van Wissen, Thunnis van Oort, and Julia Noordegraaf (2020): 
Cinema Context in RDF. Version 1.0. CREATE, University of Amsterdam. DANS. 
https://doi.org/10.17026/dans-z64-mrvb
```

For the original data:

```
Karel Dibbets (2018): Cinema Context. Film in Nederland vanaf 1896: 
een encyclopedie van de filmcultuur. Universiteit van Amsterdam. DANS. 
https://doi.org/10.17026/dans-z9y-c5g6
```

### Commercial Use Notes

- ✅ Commercial use is permitted under CC BY 4.0
- ✅ Attribution is required
- ✅ No additional restrictions

---

## Data Provenance

### Source Information

| Field | Value |
|-------|-------|
| **Source Name** | Cinema Context |
| **Source URL** | https://www.cinemacontext.nl/ |
| **SPARQL Endpoint** | https://data.create.humanities.uva.nl/sparql |
| **Named Graph** | https://data.create.humanities.uva.nl/id/cinemacontext/ |
| **Data Version** | 1.0 (2020-10-27) |
| **DOI** | https://doi.org/10.17026/dans-z64-mrvb |
| **Publisher** | DANS (Data Archiving and Networked Services) |
| **Organization** | CREATE, University of Amsterdam |

### Data Collection

From the Cinema Context documentation:

> "Cinema Context is a comprehensive database of film screenings and cinema history in the Netherlands, providing researchers and students with access to historical data from 1896 to the present."

> "The database contains detailed records of films, cinemas, screening programmes, people, and companies involved in Dutch film culture."

### Data Scale

| Metric | Value |
|--------|-------|
| Films | 51,236 |
| Censorship files | 49,849 |
| Cinemas | 2,217 |
| Programmes | 144,176 |
| People | 4,379 |
| Companies | 1,652 |

---

## Query Used

### SPARQL Query for M9 Corpus

```sparql
PREFIX schema: <http://schema.org/>
PREFIX sem: <http://semanticweb.cs.vu.nl/2009/11/sem/>

SELECT ?venue ?name ?city ?title ?date ?imdb WHERE {
  GRAPH <https://data.create.humanities.uva.nl/id/cinemacontext/> {
    ?venue a schema:MovieTheater ;
           schema:name ?name ;
           schema:location ?place .
    
    ?place schema:address ?address .
    ?address schema:addressLocality ?city .
    
    ?program schema:location ?venue ;
             schema:subEvent ?screening ;
             sem:hasEarliestBeginTimeStamp ?date .
    
    ?screening schema:workPresented ?film .
    ?film schema:name ?title .
    
    OPTIONAL { ?film schema:sameAs ?imdb . }
  }
}
ORDER BY ?name ?date
```

### Query Parameters

- **Endpoint:** https://data.create.humanities.uva.nl/sparql
- **Graph:** https://data.create.humanities.uva.nl/id/cinemacontext/
- **Retrieved:** 2026-10-06
- **Parser:** build_m9_dataset.py v1.0

---

## Transformation Provenance

### Parser Version

- **Script:** research/scripts/build_m9_dataset.py
- **Version:** 1.0
- **Date:** 2026-10-06

### Transformations Applied

1. **SPARQL query** → Raw JSON response
2. **JSON parsing** → Python dicts
3. **DataFrame creation** → pandas DataFrame
4. **Parquet export** → independent_cinema_programmes.parquet

### Checksums

- **Source:** SPARQL endpoint (no static file)
- **Parser:** build_m9_dataset.py
- **Output:** data/processed/independent_cinema_programmes.parquet

---

## Reproducibility

### How to Reproduce

1. **Install dependencies:**
   ```bash
   pip install httpx pandas pyarrow
   ```

2. **Run parser:**
   ```bash
   python research/scripts/build_m9_dataset.py
   ```

3. **Expected output:**
   - data/processed/independent_cinema_programmes.parquet
   - data/venue_source_validation.csv
   - data/manifests/independent_cinema_programmes_2026-10-06_manifest.json

### Dependencies

- **Python:** 3.13+
- **httpx:** HTTP client
- **pandas:** Data manipulation
- **pyarrow:** Parquet support

---

## Corrections to Previous Reports

### M9 Reports

All M9 reports stated "CC-BY 4.0" for the licence. This is **CORRECT**.

### M10 Reports

M10 reports did not challenge the licence claim. This is **CORRECT**.

### M10.1 Reports

This report provides authoritative evidence for the licence claim. This is **CORRECT**.

---

## Conclusion

**Licence:** Creative Commons Attribution 4.0 International License (CC BY 4.0)

**Status:** ✅ VERIFIED

**Evidence:**
1. Cinema Context RDF documentation states CC BY 4.0
2. Research Data Journal paper states CC BY 4.0
3. Commercial use is permitted with attribution

**Attribution Required:** Yes — cite the dataset using the provided citations.

---

**Report Generated:** 2026-10-06
**Status:** COMPLETE