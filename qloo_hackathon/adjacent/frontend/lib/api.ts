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
  TraceRow,
} from "@/types/adjacent";

// Keep the backend server-side: browser requests always stay on this origin,
// and Next.js proxies /api using ADJACENT_API_ORIGIN.
const API_BASE = "/api";
const API_TIMEOUT_MS = 12_000;
// Render's free service may need tens of seconds to wake from sleep. Only run
// creation gets this longer budget; polling, reads and ordinary writes stay bounded.
const RUN_START_TIMEOUT_MS = 75_000;

async function fetchWithTimeout(
  path: string,
  init: RequestInit,
  timeoutMessage: string
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    return await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal });
  } catch (err) {
    if (controller.signal.aborted) throw new Error(timeoutMessage);
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchJsonWithTimeout<T>(
  path: string,
  init: RequestInit,
  timeoutMessage: string,
  timeoutMs = API_TIMEOUT_MS
): Promise<{ response: Response; data: T | null }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal });
    const data = await response.json().catch((err: unknown) => {
      if (controller.signal.aborted) throw err;
      return null;
    }) as T | null;
    return { response, data };
  } catch (err) {
    if (controller.signal.aborted) throw new Error(timeoutMessage);
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

function responseDetail(value: unknown): string | null {
  if (typeof value !== "object" || value === null || !("detail" in value)) return null;
  const detail = (value as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : null;
}


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
  trace: TraceRow[];
}

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

// ─── API Calls ──────────────────────────────────────────────────────────────

export async function createRun(request: RunRequest): Promise<RunResponse> {
  const { response: res, data } = await fetchJsonWithTimeout<RunResponse | { detail?: string }>(
    "/run",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
    "Analysis start timed out. The backend may have accepted the request; check run status before retrying.",
    RUN_START_TIMEOUT_MS
  );
  if (!res.ok) {
    const detail = data && "detail" in data && typeof data.detail === "string" ? data.detail : res.statusText;
    throw new Error(detail || "Failed to create run");
  }
  if (!data || !("run_id" in data)) throw new Error("The backend returned an invalid run response.");
  return data;
}

export async function getRun(runId: string): Promise<RunResponse> {
  const { response: res, data } = await fetchJsonWithTimeout<RunResponse>(
    `/run/${runId}`,
    {},
    "Run status request timed out. Check the backend connection and retry."
  );
  if (!res.ok) throw new Error("Run not found");
  if (!data) throw new Error("The backend returned an empty run response.");
  return data;
}

/**
 * Start the explicitly labelled fixture demo run (no Qloo key required).
 * The backend marks every artefact `data_status: "fixture"` — the UI must
 * always show that labelling. This never replaces a live request.
 */
export async function createDemoRun(): Promise<RunResponse> {
  const { response: res, data } = await fetchJsonWithTimeout<RunResponse | { detail?: string }>(
    "/run/demo",
    { method: "POST" },
    "Fixture run start timed out. The backend may have accepted the request; check run status before retrying.",
    RUN_START_TIMEOUT_MS
  );
  if (!res.ok) {
    const detail = data && "detail" in data && typeof data.detail === "string" ? data.detail : res.statusText;
    throw new Error(detail || "Failed to start fixture demo run");
  }
  if (!data || !("run_id" in data)) throw new Error("The backend returned an invalid fixture-run response.");
  return data;
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

  let terminalReceived = false;
  const terminalEvents = new Set(["done", "insufficiency", "error"]);
  for (const [eventType, handler] of Object.entries(handlers)) {
    eventSource.addEventListener(eventType, (e: MessageEvent) => {
      const isTerminal = terminalEvents.has(eventType);
      try {
        handler(JSON.parse(e.data));
      } catch (err) {
        console.error(`Failed to parse ${eventType} event:`, err);
      }
      if (isTerminal) {
        terminalReceived = true;
        eventSource.close();
      }
    });
  }

  eventSource.onerror = () => {
    if (terminalReceived) return;
    onError?.(new Error("SSE connection lost"));
    eventSource.close();
  };

  return () => eventSource.close();
}

export interface BackendHealth {
  status: string;
  mode: string;
  qloo_configured?: boolean;
  mock_mode?: boolean;
  public_demo?: boolean;
  fixture_demo_available?: boolean;
  live_creator_available?: boolean;
  filmsponsor_guest_enabled?: boolean;
}

export async function getHealth(): Promise<BackendHealth> {
  const { response, data } = await fetchJsonWithTimeout<BackendHealth>(
    "/health",
    {},
    "Backend status check timed out. Check the backend connection and retry."
  );
  if (!response.ok || !data) throw new Error("Could not load backend status");
  return data;
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
    affinity: c.affinity ?? null,
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
  demo?: string | boolean;
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

let filmSponsorCsrfToken: string | null = null;
let sponsorSessionInitialization: Promise<{ expires_at: string }> | null = null;

function noteGuestSessionExpiry(path: string, response: Response) {
  if (path.startsWith("/filmsponsor/") && response.status === 401 && typeof window !== "undefined") {
    filmSponsorCsrfToken = null;
    window.dispatchEvent(new Event("filmsponsor-session-expired"));
  }
}

export async function initializeSponsorGuestSession(): Promise<{ expires_at: string }> {
  if (sponsorSessionInitialization) return sponsorSessionInitialization;
  const initialize = async (): Promise<{ expires_at: string }> => {
    const { response: res, data } = await fetchJsonWithTimeout<{
      csrf_token: string;
      expires_at: string;
      detail?: string;
    }>(
      "/filmsponsor/guest-session",
      {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
      "FilmSponsor workspace initialization timed out. Check the backend connection and retry."
    );
    if (!res.ok || !data) {
      throw new Error(typeof data?.detail === "string" ? data.detail : "Could not initialize guest session.");
    }
    filmSponsorCsrfToken = data.csrf_token;
    return { expires_at: data.expires_at };
  };
  const pending: Promise<{ expires_at: string }> = typeof navigator !== "undefined" && "locks" in navigator
    ? navigator.locks.request("adjacent-filmsponsor-guest-session", initialize).then(async (value) => await value)
    : initialize();
  sponsorSessionInitialization = pending;
  try {
    return await pending;
  } finally {
    if (sponsorSessionInitialization === pending) sponsorSessionInitialization = null;
  }
}

export async function revokeSponsorGuestSession(): Promise<void> {
  const res = await fetchWithTimeout(
    "/filmsponsor/guest-session",
    {
      method: "DELETE",
      credentials: "same-origin",
      headers: { "X-FilmSponsor-CSRF": filmSponsorCsrfToken ?? "" },
    },
    "Ending the FilmSponsor workspace timed out. The session may already be revoked; recheck workspace status before retrying."
  );
  noteGuestSessionExpiry("/filmsponsor/guest-session", res);
  if (!res.ok) throw new Error("Could not end guest session.");
  filmSponsorCsrfToken = null;
}

async function sponsorFetchJson<T>(
  path: string,
  init: RequestInit = {}
): Promise<{ response: Response; data: T | { detail?: string } | null }> {
  const headers = new Headers(init.headers);
  if (filmSponsorCsrfToken && path !== "/filmsponsor/guest-session") {
    headers.set("X-FilmSponsor-CSRF", filmSponsorCsrfToken);
  }
  const result = await fetchJsonWithTimeout<T | { detail?: string }>(
    path,
    {
      ...init,
      credentials: "same-origin",
      headers,
    },
    "FilmSponsor request timed out. Check the backend connection and retry."
  );
  noteGuestSessionExpiry(path, result.response);
  return result;
}

async function postJson<T>(
  path: string,
  body: unknown,
  label: string,
  timeoutMs = API_TIMEOUT_MS
): Promise<T> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (path.startsWith("/filmsponsor/") && filmSponsorCsrfToken) {
    headers.set("X-FilmSponsor-CSRF", filmSponsorCsrfToken);
  }
  // Keep the abort timer active through response-body parsing as well as the
  // initial connection. A server that sends headers and then stalls must not
  // leave a write action spinning forever.
  const { response: res, data } = await fetchJsonWithTimeout<T | { detail?: string }>(
    path,
    {
      method: "POST",
      credentials: "same-origin",
      headers,
      body: JSON.stringify(body),
    },
    `${label} timed out. The request may not have been recorded — reload before retrying.`,
    timeoutMs
  );
  noteGuestSessionExpiry(path, res);
  if (!res.ok) {
    const detail = responseDetail(data);
    throw new Error(detail || `${label} failed (${res.status})`);
  }
  if (data === null) throw new Error(`${label} returned an empty or invalid response.`);
  return data as T;
}

export function createCreatorRun(
  req: CreatorRunRequest,
  options?: { demo?: boolean }
): Promise<RunResponse> {
  const isDemo = options?.demo || req.demo === "fixture" || req.demo === true;
  const path = isDemo ? "/creator/run?demo=fixture" : "/creator/run";
  return postJson<RunResponse>(
    path, req, isDemo ? "Creator fixture demo" : "Creator analysis", RUN_START_TIMEOUT_MS
  );
}

export function createCreatorDemoRun(
  req?: Partial<CreatorRunRequest>
): Promise<RunResponse> {
  return postJson<RunResponse>(
    "/creator/run/demo", req ?? {}, "Creator fixture demo", RUN_START_TIMEOUT_MS
  );
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
  const { response, data } = await fetchJsonWithTimeout<{ experiments?: ExperimentRecord[] }>(
    "/experiments",
    {},
    "Research Log request timed out. Check the backend connection and retry."
  );
  if (!response.ok) throw new Error("Failed to load experiments");
  return data?.experiments ?? [];
}

export async function getExperiment(
  experimentId: string
): Promise<{
  experiment: ExperimentRecord;
  observations: ObservationRecord[];
  evaluations: EvaluationRecord[];
}> {
  const { response: res, data } = await fetchJsonWithTimeout<{
    experiment: ExperimentRecord;
    observations: ObservationRecord[];
    evaluations: EvaluationRecord[];
  }>(
    `/experiments/${experimentId}`,
    {},
    "Experiment details request timed out. Check the backend connection and retry."
  );
  if (!res.ok) throw new Error("Experiment not found");
  if (!data) throw new Error("The backend returned an empty experiment response.");
  return data;
}

// ---------------------------------------------------------------------------
// YouTube integration (M13.10) — optional, creator-authorized analytics
// ---------------------------------------------------------------------------

export interface YouTubeStatus {
  mode: "mock" | "live" | "not_configured";
  mock_data: boolean;
  configured: boolean;
  redirect_uri: string | null;
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
  disabled_reason?: string;
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
  const { response: res, data: body } = await fetchJsonWithTimeout<YouTubeStatus | { detail?: string }>(
    "/youtube/status",
    {},
    "YouTube connection status request timed out. Check the backend connection and retry."
  );
  if (!res.ok) {
    const detail = body && "detail" in body && typeof body.detail === "string" ? body.detail : res.statusText;
    throw new Error(detail || "Could not load YouTube connection status");
  }
  if (!body || !("mode" in body)) throw new Error("The backend returned an invalid YouTube status response.");
  return body;
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
  type VideosResponse = {
    data_status: "mock" | "live";
    videos: YouTubeVideo[];
    note: string;
  };
  const { response: res, data } = await fetchJsonWithTimeout<VideosResponse | { detail?: string }>(
    "/youtube/videos",
    {},
    "YouTube video list request timed out. Check the backend connection and retry."
  );
  if (res.status === 409) throw new Error("No YouTube connection — authorize first.");
  if (!res.ok) {
    const detail = data && "detail" in data && typeof data.detail === "string" ? data.detail : res.statusText;
    throw new Error(detail || "Could not list videos");
  }
  if (!data || !("videos" in data)) throw new Error("The backend returned an invalid YouTube video list.");
  return data;
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
  const { response: res, data } = await fetchJsonWithTimeout<YouTubeMetricsPreview | { detail?: string }>(
    `/youtube/metrics?${params.toString()}`,
    {},
    "YouTube metrics request timed out. Check the backend connection and retry."
  );
  if (!res.ok) {
    const detail = data && "detail" in data && typeof data.detail === "string" ? data.detail : res.statusText;
    throw new Error(detail || "Could not fetch metrics");
  }
  if (!data || !("video_id" in data)) throw new Error("The backend returned an invalid YouTube metrics response.");
  return data;
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
  type DisconnectResponse = {
    revoked_upstream: boolean;
    credentials_deleted: boolean;
    youtube_observations_deleted: number;
    experiments_tombstoned: number;
  } | { detail?: string };
  const { response: res, data: body } = await fetchJsonWithTimeout<DisconnectResponse>(
    "/youtube/disconnect",
    { method: "POST" },
    "YouTube disconnect timed out. The backend may have completed it; refresh connection status before retrying."
  );
  if (!res.ok) {
    const detail = body && "detail" in body && typeof body.detail === "string" ? body.detail : res.statusText;
    throw new Error(detail || "Could not disconnect");
  }
  if (!body || !("revoked_upstream" in body)) throw new Error("The backend returned an invalid disconnect response.");
  return body;
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
  const { response: res, data } = await fetchJsonWithTimeout<SynthesisStatus | { detail?: string }>(
    "/creator/synthesis-status",
    {},
    "Decision brief availability check timed out. Check the backend connection and retry."
  );
  if (!res.ok) {
    const detail = data && "detail" in data && typeof data.detail === "string" ? data.detail : res.statusText;
    throw new Error(detail || "Failed to load synthesis status");
  }
  if (!data || !("available" in data)) throw new Error("The backend returned an invalid synthesis-status response.");
  return data;
}

export function synthesizeRun(runId: string): Promise<SynthesisResponse> {
  return postJson<SynthesisResponse>("/creator/synthesize", { run_id: runId }, "Decision brief");
}

// ─── FilmSponsor campaigns (Creator Mode) ─────────────────────────────────
// Campaign intake → live brand discovery → editable drafts → official-source
// review → approval → export → outreach outcomes. Brand candidates come only
// from a live, measured discovery; a missing key is an honest 503, never a
// fixture substitution.

import type {
  SponsorCampaign,
  SponsorCampaignDetail,
  SponsorDiscovery,
  SponsorDraft,
  SponsorExportPackage,
  SponsorOutreachRecord,
  SponsorSourceReview,
} from "@/types/adjacent";

export interface SponsorCampaignInput {
  request_id: string;
  film_title: string;
  film_year?: number | null;
  imdb_id?: string | null;
  themes?: string[];
  goals?: string;
}

export function createSponsorCampaign(
  body: SponsorCampaignInput
): Promise<{ duplicate: boolean; campaign: SponsorCampaign }> {
  return postJson("/filmsponsor/campaigns", body, "Create campaign");
}

export async function listSponsorCampaigns(): Promise<SponsorCampaign[]> {
  const headers = new Headers();
  if (filmSponsorCsrfToken) headers.set("X-FilmSponsor-CSRF", filmSponsorCsrfToken);
  const { response, data } = await fetchJsonWithTimeout<{
    campaigns?: SponsorCampaign[];
    detail?: string;
  }>(
    "/filmsponsor/campaigns",
    { credentials: "same-origin", headers },
    "FilmSponsor campaign request timed out. Check the backend connection and retry."
  );
  noteGuestSessionExpiry("/filmsponsor/campaigns", response);
  if (!response.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : "Failed to load campaigns");
  }
  return data?.campaigns ?? [];
}

export async function getSponsorCampaign(campaignId: string): Promise<SponsorCampaignDetail> {
  const { response: res, data } = await sponsorFetchJson<SponsorCampaignDetail>(
    `/filmsponsor/campaigns/${campaignId}`
  );
  if (!res.ok) {
    const detail = responseDetail(data);
    throw new Error(detail || "Campaign not found");
  }
  if (
    !data ||
    typeof data !== "object" ||
    !("campaign" in data) ||
    !("discoveries" in data) ||
    !("drafts" in data) ||
    !("source_reviews" in data) ||
    !("outreach" in data)
  ) {
    throw new Error("The backend returned an invalid campaign response.");
  }
  return data as SponsorCampaignDetail;
}

/**
 * Runs live Qloo brand discovery. Fails honestly (503) when the backend key
 * is not configured; the response detail is surfaced verbatim — no fixture
 * brands are ever substituted.
 */
export function runSponsorDiscovery(
  campaignId: string,
  request_id: string
): Promise<{ duplicate: boolean; discovery: SponsorDiscovery }> {
  return postJson(
    `/filmsponsor/campaigns/${campaignId}/discover`,
    { request_id },
    "Brand discovery"
  );
}

export function saveSponsorDraft(
  campaignId: string,
  body: { request_id: string; brand_name: string; pitch?: string; supersedes_id?: string | null }
): Promise<{ duplicate: boolean; draft: SponsorDraft }> {
  return postJson(`/filmsponsor/campaigns/${campaignId}/drafts`, body, "Save draft");
}

export function addSponsorSourceReview(
  campaignId: string,
  draftId: string,
  body: {
    request_id: string;
    source_url?: string;
    claim_checked?: string;
    verification_status: string;
    notes?: string | null;
    supersedes_id?: string | null;
  }
): Promise<{ duplicate: boolean; review: SponsorSourceReview }> {
  return postJson(
    `/filmsponsor/campaigns/${campaignId}/drafts/${draftId}/source-reviews`,
    body,
    "Record source review"
  );
}

export function approveSponsorDraft(
  campaignId: string,
  draftId: string
): Promise<{ draft: SponsorDraft }> {
  return postJson(
    `/filmsponsor/campaigns/${campaignId}/drafts/${draftId}/approve`,
    {},
    "Approve draft"
  );
}

export function addSponsorOutreach(
  campaignId: string,
  body: {
    request_id: string;
    contact_status: string;
    measurement_status: string;
    draft_id?: string | null;
    observed_on?: string | null;
    metrics?: Record<string, number | null>;
    outcome?: string | null;
    notes?: string | null;
    evidence_ref?: string | null;
    supersedes_id?: string | null;
  }
): Promise<{ duplicate: boolean; outreach: SponsorOutreachRecord }> {
  return postJson(`/filmsponsor/campaigns/${campaignId}/outreach`, body, "Record outreach");
}

export async function exportSponsorCampaign(campaignId: string): Promise<SponsorExportPackage> {
  const { response: res, data } = await sponsorFetchJson<SponsorExportPackage>(
    `/filmsponsor/campaigns/${campaignId}/export`
  );
  if (!res.ok) {
    const detail = responseDetail(data);
    throw new Error(detail || "Export failed");
  }
  if (
    !data ||
    typeof data !== "object" ||
    !("campaign" in data) ||
    !("export_ready" in data) ||
    !("approved_drafts" in data) ||
    !("excluded_drafts" in data)
  ) {
    throw new Error("The backend returned an invalid export response.");
  }
  return data as SponsorExportPackage;
}
