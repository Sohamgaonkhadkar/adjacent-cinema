"use client";

import { useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import {
  createRun,
  streamRun,
  getRun,
  type ProgrammeItemInput,
  type RunResponse,
  type SSEEvent,
} from "@/lib/api";
import IntakeForm from "@/components/IntakeForm";
import AnalysisProgress from "@/components/AnalysisProgress";
import ProgrammeBet from "@/components/ProgrammeBet";
import TestCardView from "@/components/TestCardView";

// GeographyMap uses MapLibre GL JS — must be dynamically imported (no SSR)
const GeographyMap = dynamic(() => import("@/components/GeographyMap"), {
  ssr: false,
  loading: () => (
    <div className="rounded-xl border border-gray-700 bg-gray-900/60 p-6 h-64 flex items-center justify-center">
      <span className="text-gray-500 text-sm">Loading map…</span>
    </div>
  ),
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Phase = "intake" | "analysing" | "results";

// ---------------------------------------------------------------------------
// Results View
// ---------------------------------------------------------------------------

function ResultsView({ run }: { run: RunResponse }) {
  const [selectedCohort, setSelectedCohort] = useState<any>(null);
  const result = run.result;

  if (!result) return <div>No results available</div>;

  const programme = result.programme;
  const tasteDna = result.taste_dna;
  const cohorts = result.cohorts;
  const evidence = result.evidence;
  const geography = result.geography;
  const programmeBet = result.programme_bet;
  const testCard = result.test_card;
  const dataStatus = result.data_status;
  const sourceLabel = dataStatus === "measured"
    ? "Measured Qloo API data"
    : dataStatus === "fixture"
      ? "Fixture demo data (not live)"
      : "Source mode not reported";

  return (
    <div className="space-y-8">
      {/* Programme Profile */}
      <section className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Programme Profile
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <div className="text-sm text-gray-500">Venue</div>
            <div className="font-medium">{run.venue_name || "—"}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">City</div>
            <div className="font-medium">{run.city}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Films</div>
            <div className="font-medium">{programme.total_count}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Resolved</div>
            <div className="font-medium text-emerald-600">
              {programme.resolved_count}/{programme.total_count}
            </div>
          </div>
        </div>
        <div className="space-y-1">
          {programme.items.map((item: any, i: number) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span
                className={
                  item.resolved ? "text-emerald-500" : "text-red-500"
                }
              >
                {item.resolved ? "✓" : "✕"}
              </span>
              <span className="text-gray-900">{item.title}</span>
              {item.year && (
                <span className="text-gray-400">({item.year})</span>
              )}
              {item.qloo_name && (
                <span className="text-gray-400">→ {item.qloo_name}</span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Taste DNA */}
      <section className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Taste DNA
          <span className="ml-2 text-sm font-normal text-gray-500">
            {tasteDna.tag_count} tags · {sourceLabel}
          </span>
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {tasteDna.tags.slice(0, 20).map((tag: any) => (
            <div
              key={tag.tag_id}
              className="bg-gray-50 rounded-lg p-3 border"
            >
              <div className="text-sm font-medium text-gray-900">
                {tag.name}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Affinity: {tag.affinity?.toFixed(4)}
              </div>
              <div className="text-xs text-gray-400">Band: {tag.band}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Audience Opportunities */}
      <section className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Audience Opportunities
          <span className="ml-2 text-sm font-normal text-gray-500">
            {cohorts.ranked.length} ranked, {cohorts.rejected.length} rejected
          </span>
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Culturally aligned groups worth testing — ranked by affinity in a
          single Qloo scoring context.
        </p>

        <div className="space-y-4">
          {cohorts.ranked.map((cohort: any) => (
            <div
              key={cohort.cohort_id}
              className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                selectedCohort?.cohort_id === cohort.cohort_id
                  ? "border-indigo-300 bg-indigo-50"
                  : "hover:border-gray-400"
              }`}
              onClick={() =>
                setSelectedCohort(
                  selectedCohort?.cohort_id === cohort.cohort_id
                    ? null
                    : cohort
                )
              }
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">
                      #{cohort.rank}
                    </span>
                    <span className="text-sm text-gray-600">
                      {cohort.domain.replace("urn:entity:", "")}
                    </span>
                    <span className="text-xs text-gray-400">
                      {cohort.member_count} members
                    </span>
                  </div>
                  {cohort.score && (
                    <div className="text-xs text-gray-500 mt-1">
                      Mean affinity: {cohort.score.mean_affinity?.toFixed(4)} ·
                      Novelty: {cohort.score.novelty_proxy?.toFixed(4)}
                    </div>
                  )}
                </div>
                <div className="text-sm text-gray-400">{cohort.verdict}</div>
              </div>

              {/* Expanded view */}
              {selectedCohort?.cohort_id === cohort.cohort_id && (
                <div className="mt-4 pt-4 border-t">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Members
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {cohort.members.slice(0, 10).map((member: any) => (
                      <div
                        key={member.entity_id}
                        className="flex items-center justify-between text-sm"
                      >
                        <span className="text-gray-900">{member.name}</span>
                        <span className="text-gray-500">
                          {member.affinity?.toFixed(4)} ({member.band})
                        </span>
                      </div>
                    ))}
                  </div>
                  {cohort.members.length > 10 && (
                    <div className="text-xs text-gray-400 mt-2">
                      + {cohort.members.length - 10} more members
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Rejected */}
        {cohorts.rejected.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">
              Rejected
            </h3>
            <div className="space-y-2">
              {cohorts.rejected.map((cohort: any) => (
                <div
                  key={cohort.cohort_id}
                  className="text-sm text-gray-400 border-l-2 border-gray-200 pl-3"
                >
                  {cohort.domain.replace("urn:entity:", "")} —{" "}
                  {cohort.rejection_reason}
                  {cohort.rejection_detail &&
                    `: ${cohort.rejection_detail}`}
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Geographic Affinity (M7) */}
      {geography && <GeographyMap geography={geography} />}

      {/* Programme Bet (M7) */}
      {programmeBet && <ProgrammeBet bet={programmeBet} />}

      {/* Test Card (M7) */}
      {testCard && <TestCardView testCard={testCard} />}

      {/* Evidence Panel */}
      <section className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Evidence</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-gray-500">Qloo calls</div>
            <div className="font-medium">{evidence.qloo_calls}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Trace rows</div>
            <div className="font-medium">{evidence.trace_rows}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Stop reason</div>
            <div className="font-medium">{evidence.stop_reason}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Status</div>
            <div className="font-medium">{run.status}</div>
          </div>
        </div>
        {evidence.stop_message && (
          <div className="mt-3 text-sm text-gray-600">
            {evidence.stop_message}
          </div>
        )}
      </section>

      {/* Copy as JSON (M11) */}
      <section className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Export</h2>
        <p className="text-sm text-gray-500 mb-4">
          Copy the complete analysis result with full provenance as JSON.
        </p>
        <button
          onClick={() => {
            const exportData = {
              run_id: run.run_id,
              city: run.city,
              venue_name: run.venue_name,
              status: run.status,
              programme: result.programme,
              taste_dna: result.taste_dna,
              cohorts: result.cohorts,
              geography: result.geography,
              programme_bet: result.programme_bet,
              test_card: result.test_card,
              evidence: result.evidence,
              exported_at: new Date().toISOString(),
            };
            navigator.clipboard.writeText(JSON.stringify(exportData, null, 2));
          }}
          className="px-4 py-2 bg-gray-900 text-white text-sm rounded-lg hover:bg-gray-800 transition-colors"
        >
          Copy as JSON
        </button>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function Home() {
  const [phase, setPhase] = useState<Phase>("intake");
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const startTimeRef = useRef<number>(0);
  const cleanupRef = useRef<(() => void) | null>(null);

  // Elapsed timer
  useEffect(() => {
    if (phase !== "analysing") return;
    const interval = setInterval(() => {
      setElapsed((Date.now() - startTimeRef.current) / 1000);
    }, 100);
    return () => clearInterval(interval);
  }, [phase]);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => cleanupRef.current?.();
  }, []);

  async function handleSubmit(
    city: string,
    venue: string,
    programme: ProgrammeItemInput[]
  ) {
    setError(null);
    setLoading(true);
    setPhase("analysing");
    setEvents([]);
    startTimeRef.current = Date.now();

    try {
      const response = await createRun({ city, venue_name: venue, programme });
      setRunId(response.run_id);

      // Start SSE stream
      const cleanup = streamRun(
        response.run_id,
        (event) => {
          setEvents((prev) => [...prev, event]);

          if (event.event === "done" || event.event === "insufficiency") {
            // Close the stream, then fetch the canonical result. Surface retrieval
            // failures rather than leaving the analysis screen stuck forever.
            cleanupRef.current?.();
            getRun(response.run_id)
              .then((finalRun) => {
                setRun(finalRun);
                setPhase("results");
                setLoading(false);
              })
              .catch((err: unknown) => {
                setError(err instanceof Error ? err.message : "Could not load the completed analysis");
                setPhase("intake");
                setLoading(false);
              });
          }

          if (event.event === "error") {
            cleanupRef.current?.();
            setError(event.data.message || "Analysis failed");
            setPhase("intake");
            setLoading(false);
          }
        },
        (err) => {
          setError(err.message);
          setPhase("intake");
          setLoading(false);
        }
      );
      cleanupRef.current = cleanup;
    } catch (err: any) {
      setError(err.message);
      setPhase("intake");
      setLoading(false);
    }
  }

  function reset() {
    cleanupRef.current?.();
    setPhase("intake");
    setRunId(null);
    setRun(null);
    setEvents([]);
    setError(null);
    setLoading(false);
    setElapsed(0);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Adjacent</h1>
              <p className="text-sm text-gray-500">
                Audience intelligence for independent cinema
              </p>
            </div>
            {phase !== "intake" && (
              <button
                onClick={reset}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                ← New analysis
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Intake */}
        {phase === "intake" && (
          <div>
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Analyse your programme
              </h2>
              <p className="text-sm text-gray-500">
                Enter your cinema&apos;s programme to discover culturally
                aligned audience hypotheses backed by real Qloo data.
              </p>
            </div>
            <IntakeForm onSubmit={handleSubmit} loading={loading} />
          </div>
        )}

        {/* Analysis in progress */}
        {phase === "analysing" && (
          <AnalysisProgress events={events} elapsed={elapsed} />
        )}

        {/* Results */}
        {phase === "results" && run && <ResultsView run={run} />}
      </main>

      {/* Footer */}
      <footer className="border-t mt-16">
        <div className="max-w-4xl mx-auto px-4 py-4 text-xs text-gray-500">
          Adjacent uses cultural signals to develop testable programming hypotheses. Cultural affinity is not a ticket-sales or attendance forecast.
          {run && (
            <span className="block mt-1">Latest run source: {run.result?.data_status === "measured" ? "measured Qloo API responses" : run.result?.data_status === "fixture" ? "fixture demo data (not live)" : "not reported"}.</span>
          )}
        </div>
      </footer>
    </div>
  );
}