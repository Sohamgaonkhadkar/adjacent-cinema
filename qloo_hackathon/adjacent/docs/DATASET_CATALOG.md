# DATASET CATALOG — Adjacent

## 1. Cinema/Venue Data

### 1.1 UK Cinema Infrastructure (UK Cinema Association)

| Attribute | Detail |
|-----------|--------|
| **Source** | UK Cinema Association (cinemauk.org.uk) |
| **URL** | https://www.cinemauk.org.uk/the-industry/facts-and-figures/uk-cinema-industry-infrastructure/sites-and-screens/ |
| **License** | Public statistics (requires citation) |
| **Fields** | Cinema screens, cinema sites, cinema seats, average seats per screen, average screens per site |
| **Scale** | UK-wide aggregates, 2013-2025 |
| **Time coverage** | Annual, 2013-2025 |
| **Granularity** | National aggregates (not venue-level) |
| **Use case** | Market sizing, benchmarking |
| **Limitations** | Not venue-level; aggregates only |

### 1.2 Datathistle UK Cinemas

| Attribute | Detail |
|-----------|--------|
| **Source** | datathistle.com |
| **URL** | https://www.datathistle.com/places/cinemas/ and https://film.datathistle.com/cinemas/ |
| **License** | Public website (scraping permitted for research) |
| **Fields** | Cinema name, address, city, screens, description, type |
| **Scale** | ~800+ UK cinemas |
| **Time coverage** | Current (no historical) |
| **Granularity** | Venue-level |
| **Use case** | Venue database building |
| **Limitations** | No lat/lng directly; need geocoding; no historical data |

### 1.3 ScrapeHero Cineworld Locations

| Attribute | Detail |
|-----------|--------|
| **Source** | ScrapeHero Data Store |
| **URL** | https://www.scrapehero.com/store/product/cineworld-cinemas-locations-in-the-uk/ |
| **License** | Commercial (paid download) |
| **Fields** | Store No, Zip Code, URL, Name, Address, City, Latitude, Longitude, Country |
| **Scale** | 103 Cineworld locations |
| **Time coverage** | Updated March 2024 |
| **Granularity** | Venue-level with coordinates |
| **Use case** | Chain cinema geocoded database |
| **Limitations** | Single chain; paid |

### 1.4 Wikidata Cinema/Theatre Entities

| Attribute | Detail |
|-----------|--------|
| **Source** | Wikidata SPARQL |
| **URL** | https://query.wikidata.org/ |
| **License** | CC0 (public domain) |
| **Fields** | Name, location (lat/lng), capacity, screens, inception, country, type |
| **Scale** | Thousands of cinema entities globally |
| **Time coverage** | Historical + current |
| **Granularity** | Venue-level |
| **Use case** | Venue database enrichment, geocoding |
| **Limitations** | Incomplete coverage; varying data quality; need SPARQL queries |

### 1.5 OpenStreetMap Cinema/Theatre Entities

| Attribute | Detail |
|-----------|--------|
| **Source** | OpenStreetMap Overpass API |
| **URL** | https://overpass-api.de/ |
| **License** | ODbL (Open Database License) |
| **Fields** | Name, location (lat/lng), amenity type, capacity, address |
| **Scale** | Thousands globally |
| **Time coverage** | Current |
| **Granularity** | Venue-level |
| **Use case** | Venue geocoding, geographic analysis |
| **Limitations** | Incomplete; varying quality; no historical programme data |

---

## 2. Historical Programme Data

### 2.1 Kinomatics Global Showtime Dataset

| Attribute | Detail |
|-----------|--------|
| **Source** | Kinomatics Project (Deakin/RMIT Universities, Australia) |
| **URL** | https://kinomatics.com/about/what-is-kinomatics/ |
| **License** | Research use (contact required) |
| **Fields** | Film title, date, time, screen, venue, country |
| **Scale** | 120-330 million records; 48 countries; 30,000+ venues; 47,000+ films |
| **Time coverage** | 2012-2015 (30 months) |
| **Granularity** | Individual screening level |
| **Use case** | Global cinema programming analysis, cultural flow research |
| **Strengths** | Massive scale; global coverage; screening-level detail |
| **Limitations** | Requires research partnership; data from 2012-2015; no attendance figures |
| **Access** | Contact Kinomatics team; academic partnership likely required |

### 2.2 Cinema Context (Netherlands)

| Attribute | Detail |
|-----------|--------|
| **Source** | University of Amsterdam, CREATE Digital Humanities |
| **URL** | http://www.cinemacontext.nl/ |
| **License** | Open Data (DANS deposit) |
| **DOI** | https://doi.org/10.17026/dans-z9y-c5g6 |
| **Fields** | Venues, persons, companies, films, screenings (since 1895) |
| **Scale** | 100,000+ film screenings |
| **Time coverage** | 1895-present |
| **Granularity** | Individual screening level |
| **Format** | MySQL dump + RDF/Linked Open Data |
| **Use case** | Historical cinema programming research |
| **Strengths** | Deep historical coverage; linked open data; well-documented |
| **Limitations** | Netherlands only; historical focus; no attendance data |
| **Access** | SPARQL endpoint: https://data.create.humanities.uva.nl/sparql |

### 2.3 UK & Ireland Cinema Showtimes Scraper (Apify)

| Attribute | Detail |
|-----------|--------|
| **Source** | Apify Actor (kerlvision) |
| **URL** | https://apify.com/kerlvision/uk-ireland-cinema-showtimes-scraper |
| **License** | Commercial (Apify platform) |
| **Fields** | Cinema, venue, film, show_time, show_format, sold_out, booking_url, film_rating, film_genre, film_duration, venue_city, venue_lat, venue_lon |
| **Scale** | UK & Ireland cinemas (Cineworld, Glasgow Film, expanding) |
| **Time coverage** | Current (7-day forward) |
| **Granularity** | Individual showtime level |
| **Use case** | Current programme data acquisition |
| **Strengths** | Real-time; structured; includes venue coordinates |
| **Limitations** | Forward-looking only (no historical); commercial pricing; limited chains |

### 2.4 International Showtimes API

| Attribute | Detail |
|-----------|--------|
| **Source** | International Showtimes |
| **URL** | https://www.internationalshowtimes.com/ |
| **License** | Commercial API (7-day free trial) |
| **Fields** | Showtimes, cinema metadata, movie metadata, booking links, IMDB/TMDB IDs |
| **Scale** | 120+ countries, 25,000+ cinemas, 2M showtimes daily |
| **Time coverage** | Current (real-time) |
| **Granularity** | Individual showtime level |
| **Use case** | Global showtime data; movie metadata enrichment |
| **Strengths** | Massive scale; ID matching (IMDB, TMDB); deep booking links |
| **Limitations** | Commercial pricing; forward-looking only |

---

## 3. Attendance/Demand Data

### 3.1 Kaggle Cinema Tickets Dataset

| Attribute | Detail |
|-----------|--------|
| **Source** | Kaggle (arashnic) |
| **URL** | https://www.kaggle.com/datasets/arashnic/cinema-ticket |
| **License** | CC0 (public domain) |
| **Fields** | film_code, cinema_code, total_sales, tickets_sold, tickets_out, show_time, occu_perc, ticket_price, ticket_use, capacity, date, month, quarter, day |
| **Scale** | 142,524 rows |
| **Time coverage** | 2018 (8 months) |
| **Granularity** | Film-cinema-date level |
| **Use case** | Demand forecasting, occupancy prediction |
| **Strengths** | Real cinema data; includes capacity and occupancy |
| **Limitations** | Anonymized (no film titles, no venue names); single market; 2018 only |
| **Model performance** | Best: Gradient Boosting, RMSE 18.03, R² 0.656 |

### 3.2 Kaggle Cinema Audience Forecasting Competition

| Attribute | Detail |
|-----------|--------|
| **Source** | Kaggle (Mobisium) |
| **URL** | Search: "cinema audience forecasting mobisium" |
| **License** | Competition-specific |
| **Fields** | booknow_visits (audience_count), booknow_booking, cinePOS_booking, theatre metadata, date_info |
| **Scale** | ~38,000 predictions; multiple CSV files |
| **Time coverage** | 29 Jan 2023 – 28 Feb 2024 |
| **Granularity** | Theatre-date level |
| **Use case** | Daily audience forecasting |
| **Strengths** | Real cinema data; multiple data sources; time-series |
| **Limitations** | Anonymized lat/lng; no film titles; competition-specific license |

### 3.3 BFI Statistical Yearbook

| Attribute | Detail |
|-----------|--------|
| **Source** | British Film Institute |
| **URL** | https://www.bfi.org.uk/industry-data-insights/statistical-yearbook |
| **License** | Public (requires citation) |
| **Fields** | UK box office, admissions, top films, exhibition data, audience demographics |
| **Scale** | UK national-level statistics |
| **Time coverage** | Annual, 2009-2025 |
| **Granularity** | National aggregates; some venue-type breakdowns |
| **Use case** | Market benchmarking, trend analysis |
| **Strengths** | Authoritative; comprehensive; well-documented |
| **Limitations** | Aggregated (not venue-level); no individual screening data |

### 3.4 Singapore Cinema Attendance

| Attribute | Detail |
|-----------|--------|
| **Source** | Singapore Department of Statistics |
| **URL** | https://data.gov.sg/datasets/d_db2db28d64339467a1d44f4026f0dd7a |
| **License** | Open Data Licence |
| **Fields** | Cinema screens, seating capacity, cinema attendances (annual) |
| **Scale** | National aggregates |
| **Time coverage** | 1998-2025 |
| **Granularity** | Annual national |
| **Use case** | Benchmarking, trend analysis |
| **Limitations** | Aggregated; Singapore only |

---

## 4. Film/Cultural Metadata

### 4.1 TMDb API

| Attribute | Detail |
|-----------|--------|
| **Source** | The Movie Database |
| **URL** | https://www.themoviedb.org/documentation/api |
| **License** | Non-commercial use (attribution required) |
| **Fields** | Title, year, director, cast, genres, runtime, keywords, synopsis, ratings, country, language |
| **Scale** | 1M+ movies |
| **Use case** | Film metadata enrichment |
| **Strengths** | Comprehensive; free API; well-maintained |
| **Limitations** | Non-commercial license; no box office data |

### 4.2 Wikidata Film Entities

| Attribute | Detail |
|-----------|--------|
| **Source** | Wikidata SPARQL |
| **URL** | https://query.wikidata.org/ |
| **License** | CC0 (public domain) |
| **Fields** | Title, year, director, cast, genre, country, language, festival appearances |
| **Scale** | 500,000+ film entities |
| **Use case** | Film metadata enrichment, entity linking |
| **Strengths** | Open data; linked to other knowledge bases |
| **Limitations** | Incomplete; varying quality |

### 4.3 IMDb Datasets

| Attribute | Detail |
|-----------|--------|
| **Source** | IMDb (via datasets.imdbws.com) |
| **URL** | https://developer.imdb.com/non-commercial-datasets/ |
| **License** | Non-commercial use |
| **Fields** | Title, year, genres, runtime, ratings, cast, crew |
| **Scale** | 10M+ titles |
| **Use case** | Film metadata, ratings, genre classification |
| **Strengths** | Comprehensive; widely used |
| **Limitations** | Non-commercial; no box office |

---

## 5. Geographic/Catchment Context

### 5.1 UK Census Data (ONS)

| Attribute | Detail |
|-----------|--------|
| **Source** | Office for National Statistics |
| **URL** | https://www.ons.gov.uk/census |
| **License** | Open Government Licence |
| **Fields** | Population, age distribution, household structure, income, education, ethnicity |
| **Scale** | UK-wide, postcode-level |
| **Time coverage** | 2011, 2021 censuses |
| **Granularity** | Postcode sector / LSOA |
| **Use case** | Catchment area demographics |
| **Strengths** | Authoritative; granular; comprehensive |
| **Limitations** | Census years only; some fields suppressed for privacy |

### 5.2 Audience Spectrum (The Audience Agency)

| Attribute | Detail |
|-----------|--------|
| **Source** | The Audience Agency |
| **URL** | https://theaudienceagency.org/ |
| **License** | Proprietary (but widely used in UK arts sector) |
| **Fields** | 10 cultural engagement segments (Metroculturals, Commuterland Culturebuffs, etc.) |
| **Scale** | UK household-level |
| **Use case** | Cultural audience segmentation |
| **Strengths** | Purpose-built for arts/culture; postcode-level |
| **Limitations** | Proprietary; UK only; requires license |

### 5.3 Arts Audiences: Insight (Arts Council England)

| Attribute | Detail |
|-----------|--------|
| **Source** | Arts Council England |
| **URL** | https://www.artscouncil.org.uk/sites/default/files/download-file/arts_audience_insight_2011.pdf |
| **License** | Public |
| **Fields** | 13 arts consumer segments, demographics, attendance patterns |
| **Scale** | England-wide |
| **Use case** | Understanding arts audience segments |
| **Strengths** | Well-documented; covers multiple art forms |
| **Limitations** | 2011 data; survey-based; England only |

### 5.4 Taking Part Survey (DCMS)

| Attribute | Detail |
|-----------|--------|
| **Source** | Department for Digital, Culture, Media & Sport |
| **URL** | https://www.gov.uk/government/statistical-data-sets/taking-part-survey-data |
| **License** | Open Government Licence |
| **Fields** | Arts attendance, participation, demographics |
| **Scale** | England-wide survey |
| **Time coverage** | 2005-present (annual) |
| **Granularity** | Individual survey responses |
| **Use case** | Cultural participation analysis |
| **Strengths** | Longitudinal; nationally representative |
| **Limitations** | Survey-based (self-reported); England only |

---

## 6. Dataset Strategy Summary

### Priority 1: BUILD (Must Acquire)
1. **Venue database**: Scrape UK independent cinemas (datathistle.com, Wikidata, OSM) → target 100+ venues
2. **Historical programme data**: Scrape public cinema programmes (art-house cinemas with public schedules) → target 50,000+ screenings
3. **Film metadata**: TMDb API + Wikidata for all scraped films → thousands of unique films

### Priority 2: ACQUIRE (Download/Access)
4. **Kaggle Cinema Tickets**: Download 142,524 rows for demand forecasting benchmarking
5. **BFI Statistical Yearbook**: Market-level benchmarks
6. **UK Census**: Demographic catchment data

### Priority 3: NEGOTIATE (Research Partnership)
7. **Kinomatics**: Global showtime data (330M records) — requires academic partnership
8. **Audience Finder**: UK arts audience data — requires sector partnership

### Priority 4: EVALUATE (Assess Usefulness)
9. **Cinema Context**: Netherlands historical data — evaluate for cross-cultural analysis
10. **International Showtimes API**: Current global data — evaluate for real-time programme monitoring

### Not Pursuing:
- ScrapeHero (paid, limited)
- Commercial cinema POS data (proprietary, inaccessible)
- Individual cinema loyalty data (private, GDPR issues)