// Adjacent API client — use the Next.js /api proxy locally; configure an external API URL in deployment.

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

export interface ProgrammeItemInput {
  title: string;
  year?: number;
  imdb_id?: string;
}

export interface RunRequest {
  city: string;
  venue_name?: string;
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
  stop_reason?: string;
  stop_message?: string;
  error?: string;
  result?: any;
  trace: any[];
}

export interface SSEEvent {
  event: string;
  data: any;
}

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
  if (!res.ok) {
    throw new Error("Run not found");
  }
  return res.json();
}

export function streamRun(
  runId: string,
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Error) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/run/${runId}/stream`);

  const handlers: Record<string, (data: any) => void> = {
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

export async function getHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

// Verified demo programme
export const DEMO_PROGRAMME: ProgrammeItemInput[] = [
  { title: "Perfect Days", year: 2023, imdb_id: "tt7594358" },
  { title: "The Zone of Interest", year: 2023, imdb_id: "tt7160372" },
  { title: "Taipei Story", year: 1985, imdb_id: "tt0089853" },
  { title: "Sansho the Bailiff", year: 1954, imdb_id: "tt0047445" },
  { title: "Le Samourai", year: 1967, imdb_id: "tt0062229" },
  { title: "Paris, Texas", year: 1984, imdb_id: "tt0087884" },
];