// ─── Adjacent API Adapter ──────────────────────────────────────────────────
// Typed client that talks to the real Adjacent backend.
// Normalizes responses into the frontend type system.
// Never exposes raw database structures or credentials.

import type {
  AdjacentRunResult,
  CinemaIdentity,
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

// ─── Demo Data ──────────────────────────────────────────────────────────────

export const PRINCE_CHARLES_CINEMA: CinemaIdentity = {
  name: "Prince Charles Cinema",
  city: "London",
  country: "United Kingdom",
  tagline: "The beating heart of repertory cinema in London's West End",
};

export const DEMO_PROGRAMME: ProgrammeItemInput[] = [
  { title: "Perfect Days", year: 2023, imdb_id: "tt7594358" },
  { title: "The Zone of Interest", year: 2023, imdb_id: "tt7160372" },
  { title: "Taipei Story", year: 1985, imdb_id: "tt0089853" },
  { title: "Sansho the Bailiff", year: 1954, imdb_id: "tt0047445" },
  { title: "Le Samourai", year: 1967, imdb_id: "tt0062229" },
  { title: "Paris, Texas", year: 1984, imdb_id: "tt0087884" },
];

export const DEMO_RESULT: AdjacentRunResult = {
  programme: {
    items: [
      { title: "Perfect Days", year: 2023, imdb_id: "tt7594358", resolved: true, qloo_entity_id: "E7C3A2", qloo_name: "Perfect Days", popularity: 0.72 },
      { title: "The Zone of Interest", year: 2023, imdb_id: "tt7160372", resolved: true, qloo_entity_id: "E8D4B3", qloo_name: "The Zone of Interest", popularity: 0.68 },
      { title: "Taipei Story", year: 1985, imdb_id: "tt0089853", resolved: true, qloo_entity_id: "E9E5C4", qloo_name: "Taipei Story", popularity: 0.31 },
      { title: "Sansho the Bailiff", year: 1954, imdb_id: "tt0047445", resolved: true, qloo_entity_id: "EAF6D5", qloo_name: "Sansho the Bailiff", popularity: 0.28 },
      { title: "Le Samourai", year: 1967, imdb_id: "tt0062229", resolved: true, qloo_entity_id: "EB07E6", qloo_name: "Le Samouraï", popularity: 0.55 },
      { title: "Paris, Texas", year: 1984, imdb_id: "tt0087884", resolved: true, qloo_entity_id: "EC18F7", qloo_name: "Paris, Texas", popularity: 0.61 },
    ],
    resolved_count: 6,
    total_count: 6,
  },
  taste_dna: {
    tags: [
      { tag_id: "T1", name: "Japanese Cinema", affinity: 0.82, band: "High", popularity: 0.45 },
      { tag_id: "T2", name: "Contemplative Drama", affinity: 0.79, band: "High", popularity: 0.38 },
      { tag_id: "T3", name: "Art House", affinity: 0.76, band: "High", popularity: 0.52 },
      { tag_id: "T4", name: "European Arthouse", affinity: 0.71, band: "High", popularity: 0.41 },
      { tag_id: "T5", name: "World Cinema", affinity: 0.68, band: "Medium", popularity: 0.55 },
      { tag_id: "T6", name: "Slow Cinema", affinity: 0.65, band: "Medium", popularity: 0.22 },
      { tag_id: "T7", name: "Neo-Noir", affinity: 0.58, band: "Medium", popularity: 0.35 },
      { tag_id: "T8", name: "Minimalism", affinity: 0.55, band: "Medium", popularity: 0.18 },
    ],
    tag_count: 8,
    call_id: "demo-taste-001",
  },
  cohorts: {
    ranked: [
      {
        cohort_id: "C1", domain: "urn:entity:music_artist", rank: 1, member_count: 12,
        verdict: "EVIDENCE_SUFFICIENT",
        score: { mean_affinity: 0.72, max_affinity: 0.89, novelty_proxy: 0.65 },
        members: [
          { entity_id: "M1", name: "Ryuichi Sakamoto", affinity: 0.89, band: "High", popularity: 0.62 },
          { entity_id: "M2", name: "Arvo Pärt", affinity: 0.84, band: "High", popularity: 0.48 },
          { entity_id: "M3", name: "Nils Frahm", affinity: 0.78, band: "High", popularity: 0.55 },
          { entity_id: "M4", name: "Max Richter", affinity: 0.75, band: "High", popularity: 0.51 },
          { entity_id: "M5", name: "Bryce Dessner", affinity: 0.71, band: "Medium", popularity: 0.42 },
        ],
      },
      {
        cohort_id: "C2", domain: "urn:entity:book", rank: 2, member_count: 8,
        verdict: "EVIDENCE_SUFFICIENT",
        score: { mean_affinity: 0.68, max_affinity: 0.82, novelty_proxy: 0.58 },
        members: [
          { entity_id: "B1", name: "Kenzaburō Ōe", affinity: 0.82, band: "High", popularity: 0.35 },
          { entity_id: "B2", name: "Yukio Mishima", affinity: 0.79, band: "High", popularity: 0.41 },
          { entity_id: "B3", name: "Haruki Murakami", affinity: 0.74, band: "High", popularity: 0.72 },
        ],
      },
      {
        cohort_id: "C3", domain: "urn:entity:artist", rank: 3, member_count: 10,
        verdict: "EVIDENCE_SUFFICIENT",
        score: { mean_affinity: 0.64, max_affinity: 0.78, novelty_proxy: 0.71 },
        members: [
          { entity_id: "A1", name: "Hiroshi Sugimoto", affinity: 0.78, band: "High", popularity: 0.38 },
          { entity_id: "A2", name: "Tadao Ando", affinity: 0.74, band: "High", popularity: 0.42 },
          { entity_id: "A3", name: "Yayoi Kusama", affinity: 0.71, band: "Medium", popularity: 0.65 },
        ],
      },
    ],
    rejected: [
      { cohort_id: "R1", domain: "urn:entity:venue", rejection_reason: "INSUFFICIENT_MEMBERS", rejection_detail: "Only 2 qualifying members (need 3+)" },
    ],
    total_ranked: 3,
    total_rejected: 1,
  },
  geography: {
    city: "London, UK",
    city_display: "London",
    total_cells: 47,
    cells: [
      { latitude: 51.5074, longitude: -0.1278, affinity: 0.85, geohash: "gcpvj", affinity_rank: 1, popularity: 0.72 },
      { latitude: 51.5155, longitude: -0.1415, affinity: 0.78, geohash: "gcpvn", affinity_rank: 2, popularity: 0.68 },
      { latitude: 51.5225, longitude: -0.1532, affinity: 0.72, geohash: "gcpvp", affinity_rank: 3, popularity: 0.61 },
      { latitude: 51.4975, longitude: -0.1351, affinity: 0.69, geohash: "gcpvh", affinity_rank: 4, popularity: 0.55 },
      { latitude: 51.5301, longitude: -0.1246, affinity: 0.65, geohash: "gcpvq", affinity_rank: 5, popularity: 0.52 },
      { latitude: 51.5421, longitude: -0.1489, affinity: 0.61, geohash: "gcpvs", affinity_rank: 6, popularity: 0.48 },
      { latitude: 51.4812, longitude: -0.1102, affinity: 0.58, geohash: "gcpvf", affinity_rank: 7, popularity: 0.45 },
      { latitude: 51.5532, longitude: -0.1621, affinity: 0.55, geohash: "gcpvt", affinity_rank: 8, popularity: 0.42 },
      { latitude: 51.4689, longitude: -0.0952, affinity: 0.52, geohash: "gcpve", affinity_rank: 9, popularity: 0.39 },
      { latitude: 51.5612, longitude: -0.1754, affinity: 0.48, geohash: "gcpvu", affinity_rank: 10, popularity: 0.35 },
    ],
    highest_affinity_cells: [
      { latitude: 51.5074, longitude: -0.1278, affinity: 0.85, geohash: "gcpvj", affinity_rank: 1, popularity: 0.72 },
      { latitude: 51.5155, longitude: -0.1415, affinity: 0.78, geohash: "gcpvn", affinity_rank: 2, popularity: 0.68 },
      { latitude: 51.5225, longitude: -0.1532, affinity: 0.72, geohash: "gcpvp", affinity_rank: 3, popularity: 0.61 },
    ],
    call_id: "demo-geo-001",
    data_status: "demo",
    source: "qloo",
    sufficient: true,
    note: "",
  },
  programme_bet: {
    primary: {
      domain: "urn:entity:music_artist",
      cohort_name: "Contemporary Classical & Minimalist Composers",
      member_count: 12,
      mean_affinity: 0.72,
      call_id: "demo-bet-001",
    },
    runner_up: {
      domain: "urn:entity:book",
      cohort_name: "Japanese Literary Fiction",
      mean_affinity: 0.68,
      call_id: "demo-bet-002",
    },
    two_sided_signals: {
      programme_adjacency: 0.72,
      adjacency_band: "High",
      adjacency_call_id: "demo-bet-001",
      cohort_breadth: 0.58,
      breadth_band: "Medium",
      breadth_call_id: "demo-bet-001",
      methodology_note: "Programme adjacency measures cultural proximity to your existing film programme. Cohort breadth measures the fraction of the cohort that clears the quality threshold.",
    },
    why: "Your programme reveals a strong affinity for contemplative, formally rigorous cinema — from Ozu's spiritual descendants (Wenders, Kore-eda) to European minimalism (Bresson's heirs, the Dardenne tradition). This cultural profile maps directly onto contemporary classical music and minimalist composition.",
    cultural_bridge: "Ryuichi Sakamoto scored Merry Christmas Mr. Lawrence alongside Bowie — a bridge between your Japanese cinema strand and music audiences. Arvo Pärt's tintinnabuli method shares the structural minimalism of Bresson and Ozu. Nils Frahm's concert-film work (Victoria, music for spaces) already overlaps cinema culture.",
    geographic_signal: "Cultural affinity concentrates in central London — Bloomsbury, Fitzrovia, Marylebone — with a secondary cluster in Hampstead. These areas overlap with existing independent cinema audiences and contemporary classical concert venues (Wigmore Hall, Barbican).",
    programming_direction: "Test a screening-and-live-score event: pair a Wenders or Kore-eda film with a live performance by a contemporary classical artist (e.g., Nils Frahm, Max Richter). Use the Prince Charles Cinema's intimate setting as a differentiator from the Barbican's scale.",
    falsification_condition: "If fewer than 40 tickets sell across two test screenings, or if post-event surveys show no overlap between film and music audiences, the cultural bridge hypothesis is falsified.",
    rejected_candidates: [
      { cohort_id: "R1", domain: "urn:entity:venue", reason: "INSUFFICIENT_MEMBERS", detail: "Only 2 qualifying members (need 3+)" },
    ],
    geography_call_id: "demo-geo-001",
    data_status: "demo",
  },
  test_card: {
    title: "Prince Charles Cinema × Contemporary Classical",
    programme_context: "Prince Charles Cinema, London — 6-film programme spanning Japanese New Wave to European Arthouse",
    audience_hypothesis: "Contemporary classical and minimalist music audiences share cultural DNA with the Prince Charles Cinema's repertory programme",
    cultural_bridge: "Ryuichi Sakamoto, Arvo Pärt, Nils Frahm — artists whose work bridges film scoring, minimalism, and contemplative cinema",
    geographic_signal: "Affinity concentrates in Bloomsbury/Fitzrovia/Marylebone — overlapping with existing independent cinema and concert audiences",
    programming_direction: "Screen a Wenders or Kore-eda film with live contemporary classical score; test at the Prince Charles Cinema's intimate scale",
    primary_evidence: "Music Artist cohort: 12 members, mean affinity 0.72 (High programme adjacency), 58% cohort breadth (Medium)",
    runner_up: "Japanese Literary Fiction: 8 members, mean affinity 0.68 — potential for author events or book-club tie-ins",
    falsification_condition: "Fewer than 40 tickets across two test screenings, or no audience overlap in post-event surveys",
    provenance: {
      "Programme Adjacency": "Qloo /v2/insights (call: demo-bet-001)",
      "Cohort Breadth": "Qloo /v2/insights (call: demo-bet-001)",
      "Geography": "Qloo heatmap (call: demo-geo-001)",
      "Taste Profile": "Qloo /v2/insights (call: demo-taste-001)",
    },
    data_status: "demo",
  },
  evidence: {
    qloo_calls: 8,
    trace_rows: 8,
    stop_reason: "complete",
    stop_message: "Analysis complete: 6/6 films resolved, 3 cohorts ranked, 1 Programme Bet generated",
  },
  city: "London, UK",
};