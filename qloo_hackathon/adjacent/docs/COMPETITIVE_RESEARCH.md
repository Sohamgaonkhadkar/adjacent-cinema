# COMPETITIVE RESEARCH — Adjacent

## 1. Commercial Products

### 1.1 Showtime Analytics (Dublin, Ireland)

| Attribute | Detail |
|-----------|--------|
| **Product** | AI-enabled data platform for cinema operations |
| **Customer** | Cinema chains (GQT Movies, major exhibitors) |
| **Problem** | Fragmented cinema data across POS, ticketing, loyalty, concessions |
| **Input data** | POS transactions, ticketing data, loyalty programs, online transactions, Comscore market data |
| **Model/Analytics** | Real-time analytics, demand forecasting, customer segmentation (RFM), AI-driven scheduling suggestions, SurvAi feedback |
| **Output** | Dashboards, occupancy alerts, scheduling suggestions, market share analysis, customer segments |
| **Decision supported** | When to move screenings, which segments to target, pricing, scheduling |
| **Data advantage** | Direct POS integration, real-time data, Comscore benchmark data |
| **Limitations** | Requires POS integration; no cultural/programme intelligence; no cross-domain adjacency |
| **Proprietary venue data** | POS transactions, loyalty data, real-time occupancy |
| **Unavailable to small indie** | Enterprise pricing, POS integration requirements |

### 1.2 Movio (Vista Group, Auckland, NZ)

| Attribute | Detail |
|-----------|--------|
| **Product** | Audience insights & marketing analytics for cinema |
| **Customer** | Studios, distributors, cinema chains |
| **Problem** | Understanding moviegoer behaviour, targeting marketing campaigns |
| **Input data** | 100M+ moviegoers, 750M+ behavioural/transactional records, 5000+ movie titles |
| **Model/Analytics** | Propensity Algorithm (predicts which moviegoers will attend specific films), audience segmentation, campaign management |
| **Output** | Audience propensity scores, campaign targeting, demographic/behavioural insights |
| **Decision supported** | Which moviegoers to target for specific films, release window analysis |
| **Data advantage** | World's largest moviegoer database, real-time ticket purchase data |
| **Limitations** | Only works with participating cinemas; no programme optimization; no cultural adjacency |
| **Proprietary venue data** | Individual ticket purchase history, loyalty data |
| **Unavailable to small indie** | Requires Vista POS integration; enterprise pricing |

### 1.3 Cinema Intelligence (Vista Group, Amsterdam)

| Attribute | Detail |
|-----------|--------|
| **Product** | AI-powered film forecasting, scheduling, and business analysis |
| **Customer** | Cinema exhibitors (Pathé Netherlands, major chains) |
| **Problem** | Manual scheduling is time-consuming and suboptimal |
| **Input data** | Historical box office, POS data, screen metadata, film metadata |
| **Model/Analytics** | Demand forecasting (±15% accuracy on opening weekend), automated scheduling, "what-if" analysis |
| **Output** | Optimised weekly schedules, demand forecasts, booking recommendations |
| **Decision supported** | Which films to book, how to allocate screens, when to schedule |
| **Data advantage** | Integrated with Vista POS, historical performance data |
| **Limitations** | Focuses on scheduling optimization, not audience development; no cultural intelligence |
| **Proprietary venue data** | POS data, historical attendance |
| **Unavailable to small indie** | Requires Vista integration; enterprise pricing |

### 1.4 Vista Group / Veezi

| Attribute | Detail |
|-----------|--------|
| **Product** | Cinema management software for independents |
| **Customer** | Independent cinemas, small chains |
| **Problem** | Need affordable cinema management without enterprise complexity |
| **Input data** | Box office, concessions, loyalty, ticketing |
| **Model/Analytics** | Basic reporting, film programming, Movie Mailer marketing |
| **Output** | Sales dashboards, programming tools, email marketing |
| **Decision supported** | Basic scheduling, marketing |
| **Data advantage** | Designed for independents; affordable |
| **Limitations** | No AI/ML; no audience intelligence; no cultural analysis |
| **Proprietary venue data** | Ticketing data |
| **Unavailable to small indie** | Actually designed for them, but lacks advanced analytics |

### 1.5 Cinematik

| Attribute | Detail |
|-----------|--------|
| **Product** | Data-driven film distribution platform |
| **Customer** | Studios, distributors, cinemas |
| **Problem** | Unifying scheduling, marketing, and ticketing for film distribution |
| **Input data** | Cinema exhibitor data, digital marketing, ticket purchases |
| **Model/Analytics** | Predictive performance, AI-driven audience targeting, real-time optimization |
| **Output** | Venue matching, hyper-targeted marketing, real-time analytics |
| **Decision supported** | Where to book films, how to market, release strategy |
| **Data advantage** | Integrated data from exhibitors, marketing, ticketing |
| **Limitations** | Focused on distribution, not venue-level programming; limited independent cinema support |

### 1.6 CineMetrics

| Attribute | Detail |
|-----------|--------|
| **Product** | Box office analytics platform |
| **Customer** | Giant-screen theaters, planetariums, independent cinemas |
| **Problem** | Centralizing attendance, box office, lease terms, analytics |
| **Input data** | Attendance, box office, lease terms, royalties, invoicing |
| **Model/Analytics** | Historical trend analysis, title performance comparison, audience engagement metrics |
| **Output** | Visual dashboards, performance insights, benchmarking |
| **Decision supported** | Programming decisions, revenue optimization |
| **Data advantage** | Specialized for giant-screen/independent venues |
| **Limitations** | Reporting tool, not predictive; no ML; no cultural intelligence |

### 1.7 Anolla

| Attribute | Detail |
|-----------|--------|
| **Product** | Cinema booking system with AI assistant |
| **Customer** | Cinemas of all sizes |
| **Problem** | Fragmented cinema management, manual scheduling |
| **Input data** | Ticket sales, auditorium occupancy, booking data, customer segments |
| **Model/Analytics** | AI chatbot (resolves 79% of queries), dynamic pricing, demand forecasting, scheduling optimization |
| **Output** | Optimized schedules, pricing recommendations, customer insights |
| **Decision supported** | Showtime optimization, pricing, customer engagement |
| **Data advantage** | Real-time occupancy data, customer behaviour |
| **Limitations** | Focuses on operational efficiency, not cultural/programme intelligence |

### 1.8 Filmgrail

| Attribute | Detail |
|-----------|--------|
| **Product** | Cinema CMS, analytics, and marketing platform |
| **Customer** | Cinema operators |
| **Problem** | Digital presence, audience engagement, loyalty |
| **Input data** | Movie data, ticket sales, customer engagement, push notifications |
| **Model/Analytics** | Cinema-optimized analytics, loyalty program insights, location-based services |
| **Output** | Cinema apps, analytics dashboards, loyalty programs |
| **Decision supported** | Marketing, audience engagement, retention |
| **Data advantage** | Direct customer relationship via apps |
| **Limitations** | Marketing-focused, not programming/audience development |

---

## 2. Open-Source Repositories

### 2.1 Cinema Audience Forecasting (Kaggle Competition)

| Attribute | Detail |
|-----------|--------|
| **Repository** | Multiple (23f3001514/MLP_PROJECT, patraakash98/cinema-audience-forecasting, ritiksharma3/cinema_audience_forecast) |
| **Stars/Forks** | 0-2 (student projects) |
| **Problem** | Predict daily audience count per theatre per date |
| **Dataset** | BookNow + CinePOS data: 7 CSV files (visits, bookings, theatres, dates) |
| **Dataset size** | ~38,000 predictions; ~142,524 rows in cinema tickets dataset |
| **Features** | Theatre type, area, date, day-of-week, lag features, rolling statistics, booking aggregates |
| **Model** | Gradient Boosting, LightGBM, CatBoost, ARIMA/SARIMA |
| **Target** | audience_count per theatre-date |
| **Validation** | 80/20 split, expanding future-month folds |
| **Metrics** | RMSE: 18.03, R²: 0.656 (best); Kaggle LB: 0.27-0.60 |
| **Architecture** | Feature engineering + gradient boosting ensemble |
| **What worked** | Lag features, rolling statistics, theatre-level statistics |
| **Limitations** | Anonymized data (no film titles, no venue names); no cultural metadata; no programme context |
| **What is generic** | Time-series forecasting approach |
| **What could be improved** | Add film metadata, cultural features, geographic context |

### 2.2 Cinema Occupancy Rate Forecasting (ARIMA)

| Attribute | Detail |
|-----------|--------|
| **Repository** | muohannedxd/Time-Series-Analysis-and-Forecasting-of-Cinema-Occupancy-Rate |
| **Problem** | Forecast cinema occupancy rate for pricing optimization |
| **Dataset** | Kaggle cinema.csv: daily sales and occupancy, March-November 2023 |
| **Features** | Daily total sales, occupancy rate |
| **Model** | ARIMA family models |
| **Target** | Occupancy rate percentage |
| **What worked** | Time-series decomposition, seasonal patterns |
| **Limitations** | Aggregate data (not per-film); no programme context |

### 2.3 Cinema Ticket Demand Forecasting (Kaggle)

| Attribute | Detail |
|-----------|--------|
| **Repository** | Veritxs/kaggle |
| **Problem** | Predict daily ticket sales (total_ticket) for days 4-10 of a movie's run per (movie, cinema) pair |
| **Dataset** | Kaggle cinema tickets: film_code, cinema_code, total_sales, tickets_sold, show_time, occu_perc, ticket_price, capacity, date |
| **Dataset size** | 142,524 rows |
| **Features** | Film code, cinema code, show time, occupancy, ticket price, capacity |
| **Model** | LightGBM, CatBoost ratio ensemble |
| **Target** | total_ticket for days 4-10 |
| **Validation** | Rolling out-of-time folds (expanding future-month) |
| **Metrics** | MASE: 0.33-0.60 |
| **What worked** | Horizon-aware policy, rolling CV |
| **Limitations** | Anonymized (no film titles); no cultural metadata |

### 2.4 UMS Audience Preferences (Michigan Data Science Team)

| Attribute | Detail |
|-----------|--------|
| **Repository** | Abernethy et al. (2016) - arXiv:1611.05788 |
| **Problem** | Predict audience preferences for performing arts |
| **Dataset** | 5 years of UMS ticket transaction data (individual-level) |
| **Features** | Purchase history, performance metadata, program descriptions |
| **Model** | Collaborative filtering (matrix factorization with ALS), NLP on descriptions, Markov chains for lifecycle |
| **Target** | Willingness to purchase for specific performances |
| **What worked** | Matrix factorization for taste profiling, NLP for description optimization |
| **Key finding** | 66% of customers made only one purchase; subscription revenue critical |
| **Limitations** | Single venue; performing arts (not cinema); cold-start problem |
| **Relevance** | Directly relevant: audience segmentation, recommendation, retention prediction |

---

## 3. Academic Papers

### 3.1 A Forecasting System for Movie Attendance (Marshall et al., 2013)

| Attribute | Detail |
|-----------|--------|
| **Problem** | Forecast movie demand at different life cycle stages |
| **Dataset** | 117 movies in Chile, 2001-2003 |
| **Features** | Weekly attendance, movie age, advertising |
| **Model** | Bass diffusion model, Sawhney-Eliashberg model |
| **Target** | Weekly cumulative attendance |
| **Evaluation** | Relative mean error |
| **Result** | Bass model fits well; innovation > imitation effect |
| **Weakness** | Small sample (117 movies); single country |
| **Relevance** | Life-cycle modelling applicable to programme analysis |

### 3.2 Demand-Driven Scheduling of Movies in a Multiplex (Eliashberg et al., 2009)

| Attribute | Detail |
|-----------|--------|
| **Problem** | Optimize weekly movie schedules for maximum visitors |
| **Dataset** | Pathé multiplex in Amsterdam, 14 weeks |
| **Features** | Movie age, day-of-week, time-of-day, holidays, weather, football |
| **Model** | OLS demand model + column generation optimization |
| **Target** | Visitors per show |
| **Evaluation** | MAE: 22.09, RMSE: 38.94, Pearson r: 0.65 |
| **Result** | Generated more visitors than intuition-based schedules |
| **Weakness** | Single venue; short test period |
| **Relevance** | DIRECTLY RELEVANT: demand forecasting + schedule optimization for independent cinema |

### 3.3 Forecasting Cinema Attendance at the Movie Show Level (Poland, 2020)

| Attribute | Detail |
|-----------|--------|
| **Problem** | Short-term forecasting of cinema attendance at individual show level |
| **Dataset** | 179,103 shows from 25 cinemas over 19 months in Poland |
| **Features** | Cinema characteristics, region variables, movie popularity, opening week data, genre, 3D, sequels |
| **Model** | Linear regression models (recursive estimation) |
| **Target** | Tickets sold per show |
| **Evaluation** | RMSE, one-week ahead forecasts |
| **Result** | Cinema characteristics reduce RMSE by ~1%; opening week data critical |
| **Weakness** | Linear models; limited feature engineering |
| **Relevance** | Show-level prediction; feature importance analysis |

### 3.4 An Iterative Model for Predicting Film Attendance (Yue et al., 2017)

| Attribute | Detail |
|-----------|--------|
| **Problem** | Predict film attendance during distribution |
| **Dataset** | All films released in China, 2015-2016 |
| **Features** | Film metadata, audience want data, attendance pattern |
| **Model** | Random Forest + SVM iterative model (AIM) |
| **Target** | Daily attendance |
| **Evaluation** | MAE: 2-8 |
| **Result** | Iterative model outperforms multi-model approach |
| **Weakness** | Chinese market specific |
| **Relevance** | Iterative approach for attendance prediction |

### 3.5 Data Science in Service of Performing Arts (Abernethy et al., 2016)

| Attribute | Detail |
|-----------|--------|
| **Problem** | Predict audience preferences, optimize marketing |
| **Dataset** | 5 years UMS ticket data, individual-level |
| **Features** | Purchase history, performance metadata, program descriptions |
| **Model** | Collaborative filtering (ALS), NLP, Markov chains |
| **Target** | Willingness to purchase, customer lifecycle |
| **Evaluation** | Qualitative + quantitative |
| **Result** | 66% one-time attendees; description formality correlates with sales |
| **Weakness** | Single performing arts venue |
| **Relevance** | DIRECTLY RELEVANT: audience segmentation, recommendation, retention |

### 3.6 Social Influence in Predicting Cinema Attendance (2025)

| Attribute | Detail |
|-----------|--------|
| **Problem** | Role of ratings and recommendations in cinema attendance |
| **Dataset** | Factorial survey across 4 genres |
| **Features** | Expert ratings, user ratings, peer ratings, personal recommendations |
| **Model** | Vignette/factorial survey analysis |
| **Target** | Likelihood of cinema attendance |
| **Result** | Personal recommendation from close friends holds highest significance |
| **Relevance** | Social influence features for attendance prediction |

---

## 4. Gap Analysis

### What existing tools already do:
- **Showtime Analytics/Movio**: Real-time POS analytics, customer segmentation, marketing automation
- **Cinema Intelligence**: Demand forecasting (±15%), automated scheduling
- **Vista/Veezi**: Basic cinema management, reporting
- **Academic models**: Time-series forecasting, schedule optimization

### What they rely on:
- Proprietary POS data (ticketing transactions)
- Historical attendance per venue
- Film metadata (title, genre, runtime)
- Customer loyalty/CRM data

### What they do NOT know:
- **Cultural adjacency**: Which audiences from other cultural domains would attend if programmed correctly
- **Cross-domain intelligence**: How music, book, art audiences relate to film audiences
- **Programme-level intelligence**: Not just "will this film sell?" but "what kind of programming expands the audience?"
- **Venue-specific cultural profile**: What makes THIS cinema's audience unique
- **Geographic cultural concentration**: Where culturally aligned audiences concentrate
- **Intervention measurement**: Did a programming change actually expand the audience?

### What Qloo makes possible:
- Cultural affinity data across domains (film, music, books, art, dining)
- Audience taste profiling without requiring venue POS data
- Geographic cultural heatmaps
- Cross-domain adjacency discovery
- Cultural bridge identification

### What data we can realistically obtain:
- Public programme data from independent cinemas (scrape websites)
- Historical film metadata (TMDb, Wikidata, BFI)
- Public attendance/box office data (BFI, Kaggle)
- Venue metadata (scraping, OpenStreetMap, Wikidata)
- Geographic/demographic data (census, government open data)

### What prediction/decision is underserved:
- **"What kind of programming would expand our audience?"** — No existing tool answers this
- **"Which culturally adjacent audience should we target?"** — Only Movio does something similar, but only within film
- **"Where do our potential new audiences live?"** — No existing tool provides geographic cultural concentration

### Why would a real cinema programmer care:
- Independent cinemas are losing audiences to streaming
- They need to expand beyond their current audience
- They don't know which new programming directions would work
- They lack data to make evidence-based programming decisions
- Current tools focus on operational efficiency, not audience development

---

## 5. Conclusion: Adjacent's Competitive Position

**Adjacent is NOT competing with Showtime Analytics, Movio, or Cinema Intelligence.**

Those tools solve:
- "How is my cinema performing?" (analytics)
- "Which films should I book?" (scheduling)
- "Who should I market to?" (targeting)

Adjacent solves:
- **"What kind of programming would expand my audience beyond what I currently show?"**

This is a fundamentally different question. It requires:
1. Understanding the venue's current cultural profile (from programme history)
2. Discovering culturally adjacent audiences (from Qloo)
3. Identifying where those audiences live (geographic data)
4. Producing a testable hypothesis (not a recommendation)

No existing product does this. The closest is Movio's Propensity Algorithm, but that only works within film (matching moviegoers to films), not across cultural domains.