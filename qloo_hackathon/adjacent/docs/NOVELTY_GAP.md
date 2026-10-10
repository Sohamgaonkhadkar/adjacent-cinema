# NOVELTY GAP — Adjacent

## What existing tools already do

### Operational Cinema Management
- **Showtime Analytics**: Real-time POS analytics, customer segmentation (RFM), demand forecasting, scheduling suggestions
- **Movio**: Audience propensity scoring (which moviegoers will attend which films), campaign targeting
- **Cinema Intelligence**: Demand forecasting (±15% on opening weekend), automated scheduling
- **Vista/Veezi**: Basic cinema management, reporting, email marketing

### Academic Research
- **Eliashberg et al. (2009)**: Demand-driven scheduling using OLS + column generation optimization
- **Marshall et al. (2013)**: Bass diffusion model for movie attendance lifecycle
- **Poland study (2020)**: Show-level attendance forecasting with linear regression
- **Abernethy et al. (2016)**: Collaborative filtering for performing arts audience preferences

### Open-Source
- **Kaggle cinema forecasting**: Gradient boosting on anonymized cinema data (R² 0.656)
- **Various box office prediction**: Film-level revenue prediction using metadata

## What data they rely on

| Tool | Primary Data | Secondary Data |
|------|-------------|----------------|
| Showtime Analytics | POS transactions, ticketing | Comscore market data |
| Movio | Individual ticket purchase history | Film metadata |
| Cinema Intelligence | Historical box office, POS | Screen metadata |
| Academic models | Historical attendance per venue | Film metadata, calendar |
| Kaggle projects | Anonymized attendance + bookings | Theatre metadata |

**Common pattern**: All rely on **proprietary venue data** (POS transactions, ticketing history). None use cultural/programme intelligence from external sources.

## What they do NOT know

### 1. Cultural Adjacency
No existing tool answers: "Which audiences from OTHER cultural domains (music, books, art, dining) would be interested in our cinema's programming?"

Movio's Propensity Algorithm only works within film — matching moviegoers to films they haven't seen. It cannot discover that a cinema showing art-house films might attract audiences who attend jazz concerts or read literary fiction.

### 2. Cross-Domain Audience Discovery
No existing tool connects:
- Film audiences ↔ Music audiences
- Film audiences ↔ Book audiences
- Film audiences ↔ Art gallery visitors
- Film audiences ↔ Restaurant/dining preferences

Qloo's unique capability is precisely this cross-domain cultural intelligence.

### 3. Venue-Specific Cultural Profile
Current tools tell a cinema:
- "Your audience is 60% male, aged 25-34" (Movio)
- "This film will perform well in week 1" (Cinema Intelligence)

They do NOT tell a cinema:
- "Your programming creates a distinctive cultural profile that aligns with [specific adjacent audiences]"
- "Your venue's taste profile is similar to [other cultural venues] in your city"

### 4. Geographic Cultural Concentration
No existing tool shows WHERE culturally aligned audiences live relative to a specific venue.

Movio can target by postcode, but only for existing customers. It cannot identify geographic concentrations of potential NEW audiences based on cultural affinity.

### 5. Programming Direction (Not Film Recommendations)
Existing tools recommend specific films:
- "Film X will perform well at your venue" (Cinema Intelligence)
- "Customer Y would enjoy Film Z" (Movio)

None provide programming DIRECTIONS:
- "Consider programming that bridges your art-house profile with documentary audiences"
- "There's a cultural bridge between your current programme and the literary fiction audience in your catchment"

### 6. Intervention Measurement
No existing tool measures whether a programming change actually expanded the audience:
- Did the new documentary season attract new attendees?
- Did the Q&A events bring in a different demographic?
- Was the audience expansion sustained or one-off?

## What Qloo makes possible

### Qloo's Unique Data
1. **Cross-domain cultural affinity**: Film, music, books, art, dining, travel, fashion
2. **Geographic cultural heatmaps**: Where specific cultural affinities concentrate
3. **Entity-level affinity**: Not just genre-level, but specific entities (films, artists, authors)
4. **Tag-level taste profiling**: Granular cultural tags (not just "drama" but "contemplative cinema", "slow cinema", "Asian new wave")

### Qloo + Venue Programme Data = New Intelligence
By combining:
- **Venue programme history** (what films they've shown)
- **Qloo cultural affinity** (what audiences those films attract)
- **Qloo geographic data** (where those audiences live)
- **Qloo cross-domain data** (what other cultural interests those audiences have)

We can produce:
1. **Venue Cultural Profile**: What makes this cinema's audience distinctive
2. **Adjacent Audience Discovery**: Which culturally related audiences exist but aren't being served
3. **Geographic Opportunity Map**: Where potential new audiences concentrate
4. **Programming Direction**: What type of programming would bridge current and new audiences
5. **Testable Hypothesis**: A concrete, falsifiable prediction

## What data we can realistically obtain

### Available Now:
- Public cinema programme data (scrape websites) — 50+ venues, 20,000+ screenings
- Film metadata (TMDb, Wikidata) — unlimited
- Venue geodata (OSM, Wikidata) — thousands
- Demographic data (UK Census) — postcode-level
- Cultural participation surveys (Taking Part) — national-level
- Qloo API — cultural affinity, heatmaps, entity resolution

### Available with Partnership:
- Kinomatics global showtimes — 330M records (research partnership)
- Audience Finder — 16M transactions (sector partnership)

### Not Available:
- Individual cinema POS data (proprietary)
- Individual ticket purchase history (private/GDPR)
- Real-time attendance per screening (not public)

## What prediction/decision is underserved

**The core underserved question:**

> "I run an independent cinema. I show films I love. But my audience isn't growing. I don't know which new programming directions would attract new audiences. I can't afford market research. What should I try?"

**Current answers:**
- Movio: "Market this film to these existing customers" (requires Vista POS integration)
- Cinema Intelligence: "This film will sell well here" (only works for major releases)
- Academic research: "Optimize your schedule" (requires historical data you don't have)

**Adjacent's answer:**
1. "Here's your venue's cultural profile based on your programme history"
2. "Here are culturally adjacent audiences in your area that you're not currently reaching"
3. "Here's a programming direction to test, based on real cultural affinity data"
4. "Here's how to falsify this hypothesis"

## Why would a real cinema programmer care?

### The Problem is Real:
1. **Independent cinemas are losing audiences to streaming** — UK admissions down 30% from 2019
2. **They lack data to make evidence-based programming decisions** — most rely on intuition
3. **Existing tools are designed for chains** — expensive, require POS integration
4. **They don't know what they don't know** — they can't discover adjacent audiences they're missing
5. **They can't afford market research** — Movio/Showtime Analytics pricing is enterprise-level

### Adjacent's Value Proposition:
- **No POS integration required** — works from programme history + public data
- **No existing customer data needed** — discovers NEW audiences
- **Cross-domain intelligence** — connects film to music, books, art, dining
- **Geographic specificity** — shows WHERE potential audiences live
- **Actionable output** — not "here's a dashboard" but "here's a testable hypothesis"
- **Affordable** — designed for independents, not enterprise chains

## Is Adjacent actually novel enough?

**YES, with caveats:**

### Novel:
1. Cross-domain cultural adjacency discovery (no existing tool does this)
2. Venue cultural profiling without POS data
3. Geographic cultural concentration mapping
4. Testable hypothesis generation (not just predictions)
5. Designed for independent cinemas (not enterprise chains)

### Not Novel:
1. Demand forecasting (Cinema Intelligence, academic models)
2. Film metadata analysis (TMDb, Wikidata)
3. Audience segmentation (Movio, Audience Spectrum)
4. Schedule optimization (SilverScreener, Eliashberg)

### Risk:
If Kinomatics data becomes available, a well-funded competitor could combine programme data with cultural intelligence. Our advantage is the Qloo integration and the focus on the underserved independent cinema market.

### Differentiation:
Adjacent is NOT a recommendation system. It's NOT a scheduling optimizer. It's NOT an analytics dashboard.

It's a **cultural adjacency discovery engine** that helps independent cinemas find new audiences by connecting their programme history to cross-domain cultural intelligence.

**This is a real gap.** No existing product does this.