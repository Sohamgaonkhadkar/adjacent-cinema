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

export interface ProgrammeFilm {
  title: string;
  year: number | null;
  imdb_id: string | null;
  resolved: boolean;
  qloo_entity_id: string | null;
  qloo_name: string | null;
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
  name: string;
  affinity: number | null;
  band: string | null;
  popularity: number | null;
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
  affinity: number;
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