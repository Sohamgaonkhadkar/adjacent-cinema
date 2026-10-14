# M13.9 — Creator Intelligence Research (dated, cited)

Research date: **2026-10-10** (sources accessed the same day unless noted). Every claim
below is labelled **[FACT]** (verifiable in the cited source), **[CLAIM]** (asserted by
the source, not independently verified here), or **[INFERENCE]** (our reasoning).

---

## 1. The creator-tooling market (the competitive frame)

### vidIQ
- **[FACT]** Pricing (creatorstackclub.com/software/vidiq/pricing): Free with 150 AI
  credits/month; Boost $39/mo or $199/yr; Max ~$79/mo or $468/yr; AI Coaching ~$199/mo.
- **[FACT]** Features: keyword research, channel audit, competitor tracking, AI Coach;
  pricing is AI-credit-metered. (outlierkit.com/resources/vidiq-review)
- **[INFERENCE]** Its unit of analysis is the *video/keyword*. It answers "what should my
  title and tags be", not "who is this film culturally adjacent to and how do I test that
  positioning".

### TubeBuddy
- **[FACT]** Pricing (ecommerceparadise.com/tubebuddy-pricing, outlierkit.com): Free; Pro
  $9/mo ($2.25/mo annual); Star $19/mo; Legend $49/mo. A/B thumbnail-and-title testing is
  Legend-gated.
- **[FACT]** Per-channel licensing; bulk-processing tools are the flagship utility.
- **[INFERENCE]** Its experiments are packaging A/B tests (title/thumbnail), run *after*
  the film exists. It has no concept of a positioning hypothesis recorded *before*
  release, or of an evidence trail attached to that hypothesis.

### Viewstats
- **[FACT]** Built by MrBeast's team; Free/Pro $49.99/mo/Business $249+ (creatoreconomytools.com/tool/viewstats).
- **[FACT]** Core features: outlier detection across channels, thumbnail history database.
  **[FACT]** A 2.4/5 Trustpilot score was noted in the outlierkit review (n not reported).
- **[INFERENCE]** Analytics-first: it tells you what already happened (and what outliers
  did), not what cultural audience a not-yet-released concept should be positioned toward.

**[INFERENCE — central competitive claim]** All three operate on YouTube-native signals
(SEO, packaging, published-video analytics). None structures a
*hypothesis → planned experiment → observation → evaluation* lifecycle, and none offers
cross-domain cultural context (music/art/lifestyle affinity) as positioning input. That is
the space Adjacent's Creator Mode occupies. We verified the absence of such a feature in
the reviewed sources, not in every product that exists.

## 2. Reference/cultural data sources

- **[FACT]** Letterboxd's API is in private beta; access is by application
  (letterboxd.zendesk.com → "Letterboxd API"), admission not guaranteed.
  **[INFERENCE]** Unusable as a product dependency.
- **[FACT]** TMDB API terms (themoviedb.org/api-terms-of-use): commercial use requires a
  written agreement (fees apply for some uses); attribution (logo + notice) mandatory;
  ~6-month cache limit.
  **[INFERENCE]** No TMDB dependency without a signed agreement; do not present TMDB data
  as ours.
- **[FACT]** Qloo Taste API: public docs repository with ~46 documentation pages and an
  OpenAPI 3.1 spec (github.com/qloo/docs-public); the company advertises 250M+ entities
  and a search/recommend/trending/tags surface (dev.to "qloo-taste-mcp"). A Taste AI
  API hackathon ran Jul–Aug 2025 with $25k prizes (qloo-hackathon.devpost.com).
  **[CLAIM, unverified here]** The 250M+ entity count is Qloo's own marketing figure.

## 3. YouTube platform constraints (relevant to any analytics integration)

- **[FACT]** Default YouTube Data API v3 quota is 10,000 units/day; `search.list` costs
  100 units, `videos.list` costs 1 (developers.google.com/youtube/v3/determine_quota_cost).
- **[FACT]** YouTube Analytics/Reporting requires OAuth from the channel owner with BOTH
  `youtube.readonly` AND `yt-analytics.readonly`; service accounts are not supported
  (developers.google.com/youtube/reporting/guides/authorization/installed-apps;
  rapidevelopers.com — "service accounts do not work for this API").
- **[FACT]** Audience-retention data is available only through the Analytics/Reporting
  APIs for the authenticated channel's own videos; it is not public metadata.
- **[INFERENCE]** A least-privilege YouTube integration is feasible (owner-authorized,
  read-only, own-channel) but must be opt-in and per-creator; it cannot be a shared
  server-side credential. Hence deferred, not rejected (see decision brief).

## 4. Indie short-film distribution reality (the demand frame)

- **[FACT]** Reported industry pattern (filmcane.com/blog/should-you-make-short-films-2026):
  a ~$15k short submitted to ~40 festivals (~$2k fees) receives ~6 acceptances; the
  YouTube release of a festival-accepted short earned ~3,200 views in year one in the
  cited case. Sundance Shorts acceptance rate <0.5%.
- **[FACT]** Distribution channels for shorts: festivals, YouTube, Vimeo, Short of the
  Week curation (same source).
- **[FACT]** Release-playbook guidance (FilmFreeway "10 steps to releasing your short
  film online", fetched in full): exposure > revenue for shorts; run an online + festival
  dual strategy; find curator/community partners; compress the release window; "launch,
  engage, recalibrate — keep tabs on who's connecting"; packaging and positioning are
  identified as the primary lever.
- **[FACT]** 2026 YouTube algorithm reporting (outlierkit.com/resources/youtube-algorithm-updates):
  packaging system (title+thumbnail promise alignment), outlier analysis, growing
  non-subscriber reach; Shorts gained custom thumbnails.
- **[INFERENCE]** For this segment the scarce resource is *audience-attention discovery*,
  and the controllable lever is positioning/packaging — precisely a
  hypothesis-and-experiment problem, not a production-budget problem.

## 5. What we did NOT find / did NOT do

- No market-size figures for "creator positioning tools" were found that we consider
  reliable; none are asserted here.
- No user interviews or surveys were conducted; demand statements above rest on the
  cited distribution data and playbook guidance, labelled accordingly.
- No Letterboxd/TMDB/YouTube-OAuth integration was built (constraints above).
- Live Qloo API calls were not executed this session (sandbox egress to
  `hackathon.api.qloo.com` is blocked); all fixture-path behaviour is labelled as fixture.
