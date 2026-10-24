// ─── Adjacent Frontend Type System ─────────────────────────────────────────
// Strict types for the API boundary.  Components consume these interfaces,
// never raw backend database structures.

// ─── Cinema / Venue ────────────────────────────────────────────────────────

export interface CinemaIdentity {
  name: string;
  city: string;
  country: string;
  tagline: string;
}

// ─── Programme (frontend normalized) ────────────────────────────────────────

export interface ResolutionEvidence {
  input_title: string;
  input_year: number | null;
  input_external_id: string | null;
  input_external_family: string | null;
  qloo_entity_id: string | null;
  qloo_name: string | null;
  qloo_entity_type: string | null;
  qloo_year: number | null;
  qloo_disambiguation: string | null;
  qloo_popularity: number | null;
  match_status: "VERIFIED" | "AMBIGUOUS" | "UNRESOLVED" | "MISMATCH";
  match_method: string | null;
  verification_notes: string[];
  call_id: string | null;
  related_call_ids: string[];
}

export interface ProgrammeFilm {
  title: string;
  year: number | null;
  imdb_id: string | null;
  resolved: boolean;
  qloo_entity_id: string | null;
  qloo_name: string | null;
  /** Sanitized resolver evidence; absent for fixture-only seed records. */
  resolution_evidence?: ResolutionEvidence | null;
  /** Present on some payloads (demo/normalised); the /run result omits it. */
  popularity?: number | null;
}

export interface ProgrammeData {
  films: ProgrammeFilm[];
  resolved_count: number;
  total_count: number;
}

// ─── Taste DNA / Cultural Profile ───────────────────────────────────────────

export interface TasteTag {
  tag_id: string;
  name: string;
  affinity: number | null;
  band: string | null;
  popularity: number | null;
}

export interface TasteDNA {
  tags: TasteTag[];
  tag_count: number;
  call_id: string | null;
}

// ─── Cultural Field (Cohorts) ───────────────────────────────────────────────

export interface CohortMember {
  entity_id: string;
  /** Provider-supplied entity name only; not a cohort explanation or display label. */
  name: string | null;
  type?: string | null;
  subtype?: string | null;
  affinity: number | null;
  band: string | null;
  popularity: number | null;
  tags?: { tag_id: string; name: string | null; subtype: string | null }[];
  call_id?: string | null;
  /** Qloo's normalized per-input contribution, when requested and returned. */
  qloo_attributions?: { entity_id: string; score: number }[];
  qloo_attribution_status?: "returned" | "missing" | "unsupported" | "not_requested_limit" | "not_requested_budget" | string;
}

export interface CohortScore {
  mean_affinity: number | null;
  max_affinity: number | null;
  novelty_proxy: number | null;
}

/// An entity considered but not counted as qualifying — kept visible with a
/// reason code so the reader can disagree (never silently deleted).
export interface ExcludedMember {
  entity_id: string;
  name: string | null;
  reason_code: string;
  affinity: number | null;
}

export interface RankedCohort {
  cohort_id: string;
  domain: string;
  kind?: string;
  construction_reason?: string;
  construction_evidence?: {
    rule?: string;
    subtype?: string;
    shared_tags?: string[];
    [key: string]: unknown;
  };
  rank: number;
  member_count: number;
  verdict: string | null;
  score: CohortScore | null;
  members: CohortMember[];
  qualifying_count?: number;
  excluded_members?: ExcludedMember[];
}

export interface RejectedCohort {
  cohort_id: string;
  domain: string;
  rejection_reason: string | null;
  rejection_detail: string | null;
}

export interface CulturalField {
  ranked: RankedCohort[];
  rejected: RejectedCohort[];
  total_ranked: number;
  total_rejected: number;
}

// ─── Geography ──────────────────────────────────────────────────────────────

export interface HeatmapCell {
  latitude: number;
  longitude: number;
  affinity: number | null;
  geohash: string | null;
  affinity_rank: number | null;
  popularity: number | null;
}

export interface GeographyData {
  city: string;
  city_display: string;
  total_cells: number;
  /** The backend geography payload sends `highest_affinity_cells`; `cells` may be absent. */
  cells?: HeatmapCell[];
  highest_affinity_cells: HeatmapCell[];
  call_id: string | null;
  data_status: "measured" | "fixture" | "demo";
  source: string;
  sufficient: boolean;
  note: string;
}

// ─── Programme Bet ──────────────────────────────────────────────────────────

export interface TwoSidedSignals {
  programme_adjacency: number | null;
  adjacency_band: string | null;
  adjacency_call_id: string | null;
  cohort_breadth: number | null;
  breadth_band: string | null;
  breadth_call_id: string | null;
  methodology_note: string;
}

export interface ProgrammeBetData {
  primary: {
    domain: string;
    cohort_name: string;
    member_count: number;
    mean_affinity: number | null;
    cohort_id: string | null;
    call_id: string | null;
  };
  runner_up: {
    domain: string | null;
    cohort_name: string | null;
    mean_affinity: number | null;
    call_id: string | null;
  } | null;
  two_sided_signals: TwoSidedSignals;
  why: string;
  cultural_bridge: string;
  geographic_signal: string;
  programming_direction: string;
  falsification_condition: string;
  rejected_candidates: {
    cohort_id: string;
    domain: string;
    reason: string;
    detail: string;
  }[];
  geography_call_id: string | null;
  data_status: string;
}

// ─── Test Card ──────────────────────────────────────────────────────────────

export interface TestCardData {
  title: string;
  programme_context: string;
  audience_hypothesis: string;
  cultural_bridge: string;
  geographic_signal: string;
  programming_direction: string;
  primary_evidence: string;
  runner_up: string;
  falsification_condition: string;
  success_criteria?: string;
  observation_window?: string;
  comparison_protocol?: string;
  primary_measure?: string;
  decision_rule?: string;
  provenance: Record<string, string | null>;
  data_status: string;
}

// ─── Evidence ───────────────────────────────────────────────────────────────

export interface EvidenceData {
  qloo_calls: number;
  trace_rows: number;
  stop_reason: string;
  stop_message: string | null;
}

/** A redacted provenance row returned with a run; it may represent a call or logical operation. */
export interface TraceRow {
  call_id: string;
  seq?: number;
  tool?: string;
  endpoint?: string;
  method?: string;
  params?: Record<string, unknown>;
  started_at?: string;
  duration_ms?: number | null;
  status?: number | null;
  result_count?: number | null;
  cache?: string;
  source?: string;
  data_status?: string;
  attempt?: number;
  backfill_detected?: boolean;
  error?: Record<string, unknown> | null;
  notes?: string[];
}

// ─── Prediction Lifecycle (M13.6.1) ────────────────────────────────────────

export type PredictionState =
  | "PLANNED"
  | "FROZEN"
  | "OUTCOME_FINAL"
  | "CENSORED";

export type QlooFeatureStatus =
  | "AVAILABLE_AT_PREDICTION_TIME"
  | "RETROSPECTIVE_ONLY"
  | "NO_FEATURE";

export interface PredictionSnapshot {
  prediction_id: string;
  observation_id: string;
  film_key: string;
  prediction_timestamp: string;
  prediction_horizon_hours: number;
  show_start_at: string;
  prediction_state: PredictionState;
  freeze_timestamp: string | null;
  qloo_entity_id: string | null;
  qloo_popularity: number | null;
  qloo_band: string | null;
  qloo_domain: string | null;
  qloo_feature_timestamp: string | null;
  qloo_feature_status: QlooFeatureStatus;
  feature_provenance: string;
  outcome_status: string;
  sold_out_observed: number | null;
}

// ─── Run Result (raw backend response — before normalization) ───────────────

export interface CreatorThemeInputEvidence {
  input: string;
  status: "matched" | "ambiguous" | "unresolved";
  qloo_tag_id: string | null;
  qloo_name: string | null;
  call_id: string | null;
  candidate_count?: number;
}

export interface AdjacentRunResult {
  /** Provenance of the whole result: "measured" for live Qloo, "fixture" for demo runs. */
  data_status: "measured" | "fixture" | string;
  programme: {
    items: ProgrammeFilm[];
    resolved_count: number;
    total_count: number;
  };
  taste_dna: TasteDNA;
  cohorts: CulturalField;
  geography: GeographyData | null;
  programme_bet: ProgrammeBetData | null;
  test_card: TestCardData | null;
  /// Creator Mode additions (M13.9)
  mode?: "creator";
  /// M13.11 structured cultural investigation
  investigation?: InvestigationData | null;
  film?: {
    title: string;
    logline: string;
    genre: string;
    language: string;
    release_goal: string;
    themes?: string[];
  };
  /** Creator themes resolved as exact Qloo tag matches; unresolved themes are explicitly excluded. */
  theme_inputs?: CreatorThemeInputEvidence[];
  evidence: EvidenceData;
  city: string;
}

// ─── Data Mode ──────────────────────────────────────────────────────────────

export type DataMode = "LIVE" | "DEMO" | "OFFLINE" | "MODE_UNVERIFIED";

// ─── Pipeline Phase ─────────────────────────────────────────────────────────

export type PipelinePhase =
  | "idle"
  | "resolving"
  | "analysing"
  | "expanding"
  | "ranking"
  | "geography"
  | "deciding"
  | "complete"
  | "error";

// ─── App State ──────────────────────────────────────────────────────────────

export interface AppState {
  dataMode: DataMode;
  phase: PipelinePhase;
  cinema: CinemaIdentity;
  programme: ProgrammeData | null;
  tasteDNA: TasteDNA | null;
  culturalField: CulturalField | null;
  geography: GeographyData | null;
  programmeBet: ProgrammeBetData | null;
  testCard: TestCardData | null;
  evidence: EvidenceData | null;
  runId: string | null;
  error: string | null;
}
/// M13.11 — the structured investigation account of one creator run.
export interface InvestigationQuestion {
  id: string;
  question: string;
  tool: string;
  operation: string;
  status: "answered" | "insufficient" | "unavailable";
  evidence_refs: string[];
  summary: string;
}

export interface InvestigationFinding {
  kind: "FACT" | "INTERPRETATION";
  statement: string;
  evidence_refs: string[];
}

export interface InvestigationData {
  investigation_id: string;
  film: { title?: string; logline?: string; genre?: string; language?: string; release_goal?: string };
  seeds: string[];
  questions: InvestigationQuestion[];
  findings: InvestigationFinding[];
  hypotheses: {
    primary: {
      statement: string;
      cohort_id: string | null;
      world: string;
      evidence_refs: string[];
      supporting_evidence: string;
      falsification: string;
    } | null;
    alternatives: { statement: string; world: string; evidence_refs: string[] }[];
    rejected_worlds: { cohort_id: string | null; world: string | null; reason: string | null }[];
  };
  experiment: {
    title: string;
    action_plan: string;
    success_criteria: string;
    observation_window: string;
    falsification: string;
  } | null;
  limitations: string[];
  open_questions: string[];
  data_status: string;
  provenance: { call_ids: string[]; qloo_calls_used: number; run_data_status: string };
}

// ─── FilmSponsor campaigns (Creator Mode) ──────────────────────────────────
// Mirror of the /filmsponsor/* API. Brand candidates and affinity values only
// ever come from a live, measured discovery report — never fabricated.

export interface SponsorCampaign {
  campaign_id: string;
  request_id: string;
  created_at: string;
  film_title: string;
  film_year: number | null;
  imdb_id: string | null;
  themes: string[];
  goals: string;
  provenance: Record<string, unknown>;
  discovery_count?: number;
  draft_count?: number;
  outreach_count?: number;
}

export interface SponsorBrandObservation {
  source: string;
  affinity: number | null;
  band: string | null;
  call_id: string | null;
}

export interface SponsorBrand {
  entity_id: string | null;
  name: string | null;
  popularity: number | null;
  type_evidence: string[];
  observations: SponsorBrandObservation[];
}

export interface SponsorNonBrandResult {
  entity_id: string | null;
  name: string | null;
  reason_code: string;
  type_evidence: string[];
  call_ids: string[];
}

export interface SponsorFilmResolution {
  input_title: string;
  input_year: number | null;
  input_external_id?: string | null;
  match_status: "VERIFIED" | "AMBIGUOUS" | "MISMATCH" | "UNRESOLVED";
  match_method?: string | null;
  usable: boolean;
  candidate: { entity_id: string; name: string | null; year: number | null; type: string | null } | null;
  verification_notes: string[];
  call_id?: string | null;
  related_call_ids?: string[];
  error?: Record<string, unknown> | null;
}

export interface SponsorDiscoveryReport {
  data_status?: string;
  source?: string;
  films: SponsorFilmResolution[];
  theme_canonicalization: Array<Record<string, unknown>>;
  stages: Record<string, Record<string, unknown>>;
  brands: SponsorBrand[];
  non_brand_results: SponsorNonBrandResult[];
  interpretation_limits: string[];
  call_ids: string[];
  empty?: boolean;
  logical_gets?: number;
  halt_reason?: Record<string, unknown> | null;
  brand_domain?: string;
}

export interface SponsorDiscovery {
  discovery_id: string;
  request_id: string;
  campaign_id: string;
  created_at: string;
  data_status: string;
  report: SponsorDiscoveryReport;
  supersedes_id: string | null;
}

export interface SponsorDraft {
  draft_id: string;
  request_id: string;
  campaign_id: string;
  created_at: string;
  version: number;
  brand_name: string;
  pitch: string;
  status: "DRAFT" | "APPROVED";
  approved_at: string | null;
  supersedes_id: string | null;
}

export type SponsorReviewStatus =
  | "SUPPORTED_BY_OFFICIAL_SOURCE"
  | "CONTRADICTED"
  | "UNVERIFIED";

export interface SponsorSourceReview {
  review_id: string;
  request_id: string;
  campaign_id: string;
  draft_id: string;
  created_at: string;
  source_url: string;
  claim_checked: string;
  verification_status: SponsorReviewStatus;
  notes: string | null;
  supersedes_id: string | null;
}

export interface SponsorOutreachRecord {
  outreach_id: string;
  request_id: string;
  campaign_id: string;
  draft_id: string | null;
  created_at: string;
  observed_on: string | null;
  contact_status: "CONTACTED" | "RESPONDED" | "PASSED" | "DECLINED" | "COLLABORATED";
  measurement_status: "OBSERVED" | "PARTIAL" | "MISSING" | "UNAVAILABLE" | "FAILED";
  metrics: Record<string, number | null>;
  outcome: string | null;
  notes: string | null;
  evidence_ref: string | null;
  supersedes_id: string | null;
}

export interface SponsorCampaignDetail {
  campaign: SponsorCampaign;
  discoveries: SponsorDiscovery[];
  drafts: SponsorDraft[];
  source_reviews: SponsorSourceReview[];
  outreach: SponsorOutreachRecord[];
}

export interface SponsorExportPackage {
  campaign: SponsorCampaign;
  export_ready: boolean;
  approved_drafts: Array<SponsorDraft & { source_reviews: SponsorSourceReview[] }>;
  excluded_drafts: Array<{ draft_id: string; brand_name: string; reason: string }>;
  outreach_records: SponsorOutreachRecord[];
  interpretation_limits: string[];
}
