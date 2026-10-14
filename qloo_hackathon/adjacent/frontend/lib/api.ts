// ─── Adjacent API Adapter ──────────────────────────────────────────────────
// Typed client that talks to the real Adjacent backend.
// Normalizes responses into the frontend type system.
// Never exposes raw database structures or credentials.

import type {
  AdjacentRunResult,
  CulturalField,
  DataMode,
  GeographyData,
  HeatmapCell,
  ProgrammeBetData,
  ProgrammeData,
  ProgrammeFilm,
  TestCardData,
  TasteDNA,
} from "@/types/adjacent";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

// ─── Programme Input ────────────────────────────────────────────────────────

export interface ProgrammeItemInput {
  title: string;
  year?: number;
  imdb_id?: string;
}

// ─── Run API ────────────────────────────────────────────────────────────────

export interface RunRequest {
  city: string;
  venue_name: string;
  programme: ProgrammeItemInput[];
}

export interface RunResponse {
  run_id: string;
  status: string;
  created_at: number;
  city: string;
  venue_name: string;
  programme: ProgrammeItemInput[];
  current_phase: string;
  stop_reason: string | null;
  stop_message: string | null;
  error: string | null;
  result: AdjacentRunResult | null;
  trace: unknown[];
}

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

// ─── API Calls ──────────────────────────────────────────────────────────────

export async function createRun(request: RunRequest): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create run");
  }
  return res.json();
}

export async function getRun(runId: string): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/run/${runId}`);
  if (!res.ok) throw new Error("Run not found");
  return res.json();
}

/**
 * Start the explicitly labelled fixture demo run (no Qloo key required).
 * The backend marks every artefact `data_status: "fixture"` — the UI must
 * always show that labelling. This never replaces a live request.
 */
export async function createDemoRun(): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/run/demo`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to start fixture demo run");
  }
  return res.json();
}

export function streamRun(
  runId: string,
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Error) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/run/${runId}/stream`);

  const handlers: Record<string, (data: Record<string, unknown>) => void> = {
    trace: (data) => onEvent({ event: "trace", data }),
    resolution: (data) => onEvent({ event: "resolution", data }),
    taste_dna: (data) => onEvent({ event: "taste_dna", data }),
    cohort: (data) => onEvent({ event: "cohort", data }),
    heatmap: (data) => onEvent({ event: "heatmap", data }),
    bet: (data) => onEvent({ event: "bet", data }),
    test_card: (data) => onEvent({ event: "test_card", data }),
    done: (data) => onEvent({ event: "done", data }),
    insufficiency: (data) => onEvent({ event: "insufficiency", data }),
    error: (data) => onEvent({ event: "error", data }),
  };

  for (const [eventType, handler] of Object.entries(handlers)) {
    eventSource.addEventListener(eventType, (e: MessageEvent) => {
      try {
        handler(JSON.parse(e.data));
      } catch (err) {
        console.error(`Failed to parse ${eventType} event:`, err);
      }
    });
  }

  eventSource.onerror = () => {
    onError?.(new Error("SSE connection lost"));
    eventSource.close();
  };

  return () => eventSource.close();
}

export async function getHealth(): Promise<{
  status: string;
  qloo_configured: boolean;
  mode: string;
  mock_mode: string;
}> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

// ─── Normalizers ────────────────────────────────────────────────────────────
// Convert raw backend response into typed frontend models.

export function normalizeProgramme(result: AdjacentRunResult): ProgrammeData {
  const items = result.programme?.items ?? [];
  return {
    films: items.map((item) => ({
      title: item.title ?? "",
      year: item.year ?? null,
      imdb_id: item.imdb_id ?? null,
      resolved: Boolean(item.resolved),
      qloo_entity_id: item.qloo_entity_id ?? null,
      qloo_name: item.qloo_name ?? null,
      popularity: item.popularity ?? null,
    })),
    resolved_count: result.programme?.resolved_count ?? 0,
    total_count: result.programme?.total_count ?? 0,
  };
}

export function normalizeGeography(geo: GeographyData): GeographyData {
  const rawCells = geo.highest_affinity_cells ?? geo.cells ?? [];
  const cells: HeatmapCell[] = rawCells.map((c) => ({
    latitude: c.latitude ?? 0,
    longitude: c.longitude ?? 0,
    affinity: c.affinity ?? 0,
    geohash: c.geohash ?? null,
    affinity_rank: c.affinity_rank ?? null,
    popularity: c.popularity ?? null,
  }));
  return {
    city: geo.city ?? "",
    city_display: geo.city_display ?? geo.city ?? "",
    total_cells: geo.total_cells ?? cells.length,
    cells,
    highest_affinity_cells: cells,
    call_id: geo.call_id ?? null,
    data_status: geo.data_status ?? "measured",
    source: geo.source ?? "qloo",
    sufficient: Boolean(geo.sufficient),
    note: geo.note ?? "",
  };
}

export function normalizeCohorts(cohorts: CulturalField): CulturalField {
  return {
    ranked: cohorts.ranked ?? [],
    rejected: cohorts.rejected ?? [],
    total_ranked: cohorts.total_ranked ?? cohorts.ranked?.length ?? 0,
    total_rejected: cohorts.total_rejected ?? cohorts.rejected?.length ?? 0,
  };
}

// ─── Sample programme (explicit demo input) ────────────────────────────────
// These six verified titles are offered in the intake form as a clearly
// labelled SAMPLE. They are never submitted silently — only when the
// programmer deliberately loads them.

export const DEMO_PROGRAMME: ProgrammeItemInput[] = [
  { title: "Perfect Days", year: 2023, imdb_id: "tt7594358" },
  { title: "The Zone of Interest", year: 2023, imdb_id: "tt7160372" },
  { title: "Taipei Story", year: 1985, imdb_id: "tt0089853" },
  { title: "Sansho the Bailiff", year: 1954, imdb_id: "tt0047445" },
  { title: "Le Samourai", year: 1967, imdb_id: "tt0062229" },
  { title: "Paris, Texas", year: 1984, imdb_id: "tt0087884" },
];

// ─── Creator Mode (M13.9) ───────────────────────────────────────────────────

export interface CreatorRunRequest {
  title: string;
  logline?: string;
  genre?: string;
  language?: string;
  themes?: string[];
  references?: { title: string; year?: number | null }[];
  release_goal?: string;
  city?: string;
}

export interface ExperimentRecord {
  experiment_id: string;
  request_id: string;
  created_at: string;
  film_title: string;
  film_context: Record<string, unknown>;
  hypothesis: string;
  success_criteria: string;
  observation_window: string;
  action_plan: string;
  data_status: string;
  source_run_id: string | null;
  source_bet: Record<string, unknown>;
  provenance: Record<string, unknown>;
  status: string;
  observation_count?: number;
  latest_evaluation?: string | null;
}

export interface ObservationRecord {
  observation_id: string;
  experiment_id: string;
  created_at: string;
  observed_on: string | null;
  kind: string;
  measurement_status: string;
  metrics: Record<string, number | null>;
  interpretation: string | null;
  source: string | null;
  evidence_ref: string | null;
  limitations: string | null;
  supersedes_id: string | null;
}

export interface EvaluationRecord {
  evaluation_id: string;
  experiment_id: string;
  created_at: string;
  outcome: "SUPPORTED" | "CONTRADICTED" | "INCONCLUSIVE";
  rationale: string;
  observations_used: string[];
  unknowns: string | null;
  supersedes_id: string | null;
}

async function postJson<T>(path: string, body: unknown, label: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      typeof err.detail === "string" ? err.detail : `${label} failed (${res.status})`
    );
  }
  return res.json();
}

export function createCreatorRun(req: CreatorRunRequest): Promise<RunResponse> {
  return postJson<RunResponse>("/creator/run", req, "Creator analysis");
}

export function createCreatorDemoRun(): Promise<RunResponse> {
  return postJson<RunResponse>("/creator/run/demo", {}, "Creator fixture demo");
}

export function saveExperiment(
  body: Record<string, unknown>
): Promise<{ duplicate: boolean; experiment: ExperimentRecord }> {
  return postJson("/experiments", body, "Save experiment");
}

export function addObservation(
  experimentId: string,
  body: Record<string, unknown>
): Promise<{ duplicate: boolean; observation: ObservationRecord }> {
  return postJson(`/experiments/${experimentId}/observations`, body, "Record observation");
}

export function addEvaluation(
  experimentId: string,
  body: Record<string, unknown>
): Promise<{ duplicate: boolean; evaluation: EvaluationRecord }> {
  return postJson(`/experiments/${experimentId}/evaluations`, body, "Record evaluation");
}

export async function listExperiments(): Promise<ExperimentRecord[]> {
  const res = await fetch(`${API_BASE}/experiments`);
  if (!res.ok) throw new Error("Failed to load experiments");
  const data = await res.json();
  return data.experiments ?? [];
}

export async function getExperiment(
  experimentId: string
): Promise<{
  experiment: ExperimentRecord;
  observations: ObservationRecord[];
  evaluations: EvaluationRecord[];
}> {
  const res = await fetch(`${API_BASE}/experiments/${experimentId}`);
  if (!res.ok) throw new Error("Experiment not found");
  return res.json();
}

// ---------------------------------------------------------------------------
// YouTube integration (M13.10) — optional, creator-authorized analytics
// ---------------------------------------------------------------------------

export interface YouTubeStatus {
  mode: "mock" | "live" | "not_configured";
  mock_data: boolean;
  configured: boolean;
  redirect_uri: string;
  requested_scopes: string[];
  single_connection_posture: boolean;
  connection: {
    channel_id: string | null;
    channel_title: string | null;
    connected_at: string;
    days_since_connection: number;
    reauthorization_recommended: boolean;
  } | null;
  connected: boolean;
}

export interface YouTubeVideo {
  video_id: string;
  title: string | null;
  published_at: string | null;
}

export interface YouTubeMetricsPreview {
  data_status: "mock" | "live";
  video_id: string;
  period: { start_date: string; end_date: string };
  metrics_queried: string[];
  row_count: number;
  metrics: Record<string, number>;
  limitations: string[];
  retrieved_at: string;
}

export async function youtubeStatus(): Promise<YouTubeStatus> {
  const res = await fetch(`${API_BASE}/youtube/status`);
  if (!res.ok) throw new Error("Could not load YouTube connection status");
  return res.json();
}

/** Begins the consent flow in the top-level window (Google requires it). */
export function beginYouTubeAuthorization(): void {
  window.location.href = `${API_BASE}/youtube/authorize?via=proxy`;
}

export async function youtubeVideos(): Promise<{
  data_status: "mock" | "live";
  videos: YouTubeVideo[];
  note: string;
}> {
  const res = await fetch(`${API_BASE}/youtube/videos`);
  if (res.status === 409) throw new Error("No YouTube connection — authorize first.");
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Could not list videos");
  }
  return res.json();
}

export async function youtubeMetrics(
  videoId: string,
  startDate: string,
  endDate: string
): Promise<YouTubeMetricsPreview> {
  const params = new URLSearchParams({
    video_id: videoId,
    start_date: startDate,
    end_date: endDate,
  });
  const res = await fetch(`${API_BASE}/youtube/metrics?${params.toString()}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Could not fetch metrics");
  }
  return res.json();
}

export async function recordYouTubeObservation(
  experimentId: string,
  body: {
    request_id: string;
    video_id: string;
    start_date: string;
    end_date: string;
    interpretation?: string | null;
    variant_label?: string | null;
  }
): Promise<{ duplicate: boolean; observation: ObservationRecord }> {
  return postJson(
    `/experiments/${experimentId}/observations/from-youtube`,
    body,
    "Record YouTube observation"
  );
}

export async function disconnectYouTube(): Promise<{
  revoked_upstream: boolean;
  credentials_deleted: boolean;
  youtube_observations_deleted: number;
  experiments_tombstoned: number;
}> {
  const res = await fetch(`${API_BASE}/youtube/disconnect`, { method: "POST" });
  if (!res.ok) throw new Error("Could not disconnect");
  return res.json();
}

// ── Role-B synthesis (M13.13): optional, provider-gated decision briefs ────

export interface SynthesisStatus {
  available: boolean;
  provider: string;
  model: string | null;
  blocked_reason?: string;
  note?: string;
}

export interface SynthesisClaim {
  statement: string;
  claim_type: "FACT" | "INTERPRETATION" | "HYPOTHESIS" | "UNKNOWN";
  evidence_refs: string[];
  rationale?: string;
  limitations?: string;
}

export interface SynthesisExperimentProposal {
  kind: "test" | "information_gathering";
  hypothesis: string;
  action_plan: string;
  success_criteria: string;
  observation_window: string;
  falsification: string;
  relevant_metrics: string[];
  assumptions: string[];
  limitations: string;
}

export interface SynthesisBrief {
  summary: string;
  hypothesis_restated: string;
  rationale: string;
  alternatives: string[];
  next_experiment: string;
  caveats: string[];
  claims: SynthesisClaim[];
  experiment_proposal: SynthesisExperimentProposal;
  _fallback_error?: string;
}

export interface SynthesisMetadata {
  schema_version: string;
  provider_kind: string;
  model: string | null;
  /** "live_llm" | "stub" | "deterministic_fallback" — never ambiguous. */
  method: string;
  validation: string;
  llm_error?: string;
  evidence_refs_available: string[];
  guarantees?: Record<string, string>;
}

export interface SynthesisResponse {
  run_id: string;
  synthesis: SynthesisBrief;
  metadata: SynthesisMetadata;
}

export async function getSynthesisStatus(): Promise<SynthesisStatus> {
  const res = await fetch(`${API_BASE}/creator/synthesis-status`);
  if (!res.ok) throw new Error("Failed to load synthesis status");
  return res.json();
}

export function synthesizeRun(runId: string): Promise<SynthesisResponse> {
  return postJson<SynthesisResponse>("/creator/synthesize", { run_id: runId }, "Decision brief");
}
