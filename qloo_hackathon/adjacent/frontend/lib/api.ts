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
