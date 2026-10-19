"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  addEvaluation,
  addObservation,
  beginYouTubeAuthorization,
  createCreatorDemoRun,
  createCreatorRun,
  disconnectYouTube,
  getExperiment,
  getHealth,
  getRun,
  listExperiments,
  recordYouTubeObservation,
  saveExperiment,
  streamRun,
  getSynthesisStatus,
  synthesizeRun,
  type SynthesisResponse,
  type SynthesisStatus,
  youtubeStatus,
  youtubeVideos,
  type BackendHealth,
  type EvaluationRecord,
  type ExperimentRecord,
  type ObservationRecord,
  type RunResponse,
  type SSEEvent,
  type YouTubeStatus,
  type YouTubeVideo,
} from "@/lib/api";
import type { AdjacentRunResult, InvestigationData, ProgrammeFilm, TraceRow } from "@/types/adjacent";
import AdjacencyGraph from "@/components/AdjacencyGraph";
import { EvidenceReferences, EvidenceTraceLog } from "@/components/EvidenceTrace";

// Small helpers shared with the cinema page's visual language.
const mono = { fontFamily: "var(--mono)" } as const;

function statusLabel(status: string | null): string {
  if (status === "measured") return "MEASURED QLOO DATA";
  if (status === "fixture") return "FIXTURE DEMONSTRATION — NOT LIVE DATA";
  return "DATA STATUS UNKNOWN";
}

function statusTone(status: string | null) {
  if (status === "measured") {
    return { color: "#7aba8a", background: "rgba(62,122,76,0.12)", border: "rgba(62,122,76,0.3)" };
  }
  if (status === "fixture") {
    return { color: "#c29a6e", background: "rgba(194,154,110,0.12)", border: "rgba(194,154,110,0.3)" };
  }
  return { color: "#a7a39b", background: "rgba(232,226,213,0.04)", border: "rgba(232,226,213,0.18)" };
}

function resolutionCallLabel(evidence: NonNullable<ProgrammeFilm["resolution_evidence"]>): string {
  const callIds = [evidence.call_id, ...evidence.related_call_ids].filter(
    (callId): callId is string => Boolean(callId),
  );
  return callIds.length
    ? ` · CALL${callIds.length === 1 ? "" : "S"} ${callIds.join(", ")}`
    : "";
}

export default function CreatorPage() {
  // ── intake state (values persist through failures) ──────────────────────
  const [title, setTitle] = useState("");
  const [logline, setLogline] = useState("");
  const [genre, setGenre] = useState("");
  const [language, setLanguage] = useState("");
  const [themesText, setThemesText] = useState("");
  const [referenceRows, setReferenceRows] = useState<{ title: string; year: string }[]>([
    { title: "", year: "" },
    { title: "", year: "" },
  ]);
  const [releaseGoal, setReleaseGoal] = useState("");
  const [city, setCity] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  // ── run state ────────────────────────────────────────────────────────────
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [analysing, setAnalysing] = useState(false);
  const [requestMode, setRequestMode] = useState<"live" | "fixture" | null>(null);
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const stopStream = useRef<(() => void) | null>(null);
  const experimentDetailRequest = useRef(0);
  const publicDemoRef = useRef(false);

  // ── experiment state ─────────────────────────────────────────────────────
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [experimentsLoading, setExperimentsLoading] = useState(true);
  const [experimentsError, setExperimentsError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<string | null>(null);
  const [openExpId, setOpenExpId] = useState<string | null>(null);
  const [loadingExpId, setLoadingExpId] = useState<string | null>(null);
  const [expDetailError, setExpDetailError] = useState<string | null>(null);
  const [expDetail, setExpDetail] = useState<{
    experiment: ExperimentRecord;
    observations: ObservationRecord[];
    evaluations: EvaluationRecord[];
  } | null>(null);
  const [expError, setExpError] = useState<string | null>(null);
  const [ytBanner, setYtBanner] = useState<string | null>(null);
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);

  const result: AdjacentRunResult | null = (run?.result as AdjacentRunResult | null) ?? null;
  const traceRows: TraceRow[] = run?.trace ?? [];
  const insufficient = run?.status === "insufficient";
  const failed = run?.status === "failed";
  const resultTone = statusTone(failed || insufficient ? null : result?.data_status ?? null);

  const refreshExperiments = useCallback(async () => {
    if (publicDemoRef.current) {
      setExperiments([]);
      setExperimentsError("Shared experiment storage is disabled in public-demo mode.");
      setExperimentsLoading(false);
      return;
    }
    setExperimentsLoading(true);
    setExperimentsError(null);
    try {
      setExperiments(await listExperiments());
    } catch (err) {
      setExperimentsError(err instanceof Error ? err.message : "Could not load saved experiments");
    } finally {
      setExperimentsLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then((health) => {
        if (!mounted) return;
        publicDemoRef.current = health.public_demo === true;
        setBackendHealth(health);
        if (health.public_demo) {
          setExperiments([]);
          setExperimentsError("Shared experiment storage is disabled in public-demo mode.");
          setExperimentsLoading(false);
        } else {
          void refreshExperiments();
        }
      })
      .catch(() => {
        if (mounted) void refreshExperiments();
      });
    return () => {
      mounted = false;
      stopStream.current?.();
    };
  }, [refreshExperiments]);

  const watchRun = useCallback((id: string) => {
    setRunId(id);
    setAnalysing(true);
    setEvents([]);
    stopStream.current?.();
    stopStream.current = streamRun(
      id,
      (event) => {
        setEvents((prev) => [...prev, event]);
        if (event.event === "done" || event.event === "insufficiency" || event.event === "error") {
          getRun(id)
            .then((r) => {
              setRun(r);
              setAnalysing(false);
            })
            .catch(() => {
              setError("Could not load the completed analysis");
              setAnalysing(false);
            });
        }
      },
      (err) => {
        setError(err.message);
        setAnalysing(false);
      }
    );
  }, []);

  const startDemoRun = useCallback(() => {
    setError(null);
    setRun(null);
    setSaveState(null);
    setFormError(null);
    setRequestMode("fixture");
    setAnalysing(true);
    createCreatorDemoRun()
      .then((r) => watchRun(r.run_id))
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to start the fixture demo");
        setAnalysing(false);
      });
  }, [watchRun]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const yt = params.get("yt");
    const startFixture = params.get("demo") === "fixture";

    if (yt === "connected") setYtBanner("YouTube account connected. Pick a video inside a saved experiment to record real analytics.");
    else if (yt === "denied") setYtBanner("Authorization was declined — no data was accessed. You can reconnect any time.");
    else if (yt === "error") setYtBanner(`YouTube authorization failed (${params.get("reason") ?? "unknown reason"}). No connection was stored.`);

    if (yt || startFixture) {
      params.delete("yt");
      params.delete("demo");
      if (yt) params.delete("reason");
      const query = params.toString();
      window.history.replaceState(
        {},
        "",
        `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`
      );
    }
    if (startFixture) startDemoRun();
  }, [startDemoRun]);

  function handleAnalyse() {
    setError(null);
    setRun(null);
    setSaveState(null);
    const refs = referenceRows
      .map((r) => ({ title: r.title.trim(), year: r.year.trim() ? Number(r.year) : null }))
      .filter((r) => r.title);
    const badYear = referenceRows.some(
      (r) => r.year.trim() && (!Number.isInteger(Number(r.year)) || Number(r.year) < 1888 || Number(r.year) > 2100)
    );
    if (!title.trim()) {
      setFormError("Give your film a working title.");
      return;
    }
    if (badYear) {
      setFormError("Reference years must be between 1888 and 2100.");
      return;
    }
    const themes = themesText.split(",").map((t) => t.trim()).filter(Boolean);
    if (refs.length > 5) {
      setFormError("Use at most five reference works.");
      return;
    }
    if (themes.length > 5) {
      setFormError("Use at most five themes.");
      return;
    }
    if (themes.some((theme) => theme.length > 120)) {
      setFormError("Each theme must be 120 characters or fewer.");
      return;
    }
    if (refs.some((ref) => ref.title.length > 160)) {
      setFormError("Each reference title must be 160 characters or fewer.");
      return;
    }
    if (refs.length === 0 && themes.length === 0) {
      setFormError("Add at least one reference work or theme — the analysis needs cultural seeds.");
      return;
    }
    setFormError(null);
    setRequestMode("live");
    setAnalysing(true);
    createCreatorRun({
      title: title.trim(),
      logline: logline.trim(),
      genre: genre.trim(),
      language: language.trim(),
      themes,
      references: refs,
      release_goal: releaseGoal.trim(),
      city: city.trim(),
    })
      .then((r) => watchRun(r.run_id))
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to start analysis");
        setAnalysing(false);
      });
  }

  async function handleSaveExperiment() {
    if (!result?.test_card || !runId) return;
    if (backendHealth?.public_demo) {
      setExpError("Saving shared experiments is disabled in public-demo mode. The run is temporary.");
      return;
    }
    setExpError(null);
    try {
      const card = result.test_card;
      const inv = result.investigation as Record<string, unknown> | undefined;
      const invHyp = ((inv?.hypotheses as Record<string, unknown> | undefined)?.primary ??
        null) as Record<string, unknown> | null;
      const invSummary = inv
        ? {
            investigation_id: inv.investigation_id,
            data_status: inv.data_status,
            primary_hypothesis: invHyp?.statement ?? null,
            limitations: (inv.limitations as string[]) ?? [],
            open_questions: (inv.open_questions as string[]) ?? [],
          }
        : null;
      const invEvidenceRefs = ((inv?.provenance as Record<string, unknown> | undefined)
        ?.call_ids ?? []) as string[];
      const resp = await saveExperiment({
        request_id: `exp-${runId}`, // one saved decision per analysis run — retry-safe
        film_title: (result.film as { title?: string } | undefined)?.title ?? title,
        hypothesis: card.audience_hypothesis,
        success_criteria: card.success_criteria ?? "",
        observation_window: card.observation_window ?? "",
        action_plan: card.programming_direction,
        data_status: card.data_status,
        source_run_id: runId,
        source_bet: (result.programme_bet ?? {}) as Record<string, unknown>,
        provenance: (card.provenance ?? {}) as Record<string, unknown>,
        film_context: (result.film ?? {}) as Record<string, unknown>,
        // M13.12: trace the saved decision back to the investigation itself.
        ...(invSummary
          ? { investigation_summary: invSummary, evidence_refs: invEvidenceRefs }
          : {}),
      });
      setSaveState(
        resp.duplicate
          ? "Already saved from this analysis — showing the original decision."
          : "Saved as a planned experiment. Record what actually happens below."
      );
      refreshExperiments();
    } catch (err) {
      setExpError(err instanceof Error ? err.message : "Could not save the experiment");
    }
  }

  async function loadExperimentDetail(id: string) {
    const requestId = ++experimentDetailRequest.current;
    setLoadingExpId(id);
    setExpDetailError(null);
    try {
      const detail = await getExperiment(id);
      if (requestId === experimentDetailRequest.current) setExpDetail(detail);
    } catch (err) {
      if (requestId === experimentDetailRequest.current) {
        setExpDetailError(err instanceof Error ? err.message : "Could not load experiment");
      }
    } finally {
      if (requestId === experimentDetailRequest.current) setLoadingExpId(null);
    }
  }

  async function openExperiment(id: string) {
    setExpError(null);
    if (id === openExpId) {
      experimentDetailRequest.current += 1;
      setOpenExpId(null);
      setLoadingExpId(null);
      setExpDetailError(null);
      return;
    }
    setOpenExpId(id);
    await loadExperimentDetail(id);
  }

  const bet = result?.programme_bet ?? null;
  const card = result?.test_card ?? null;
  const ranked = result?.cohorts?.ranked ?? [];
  const rejected = result?.cohorts?.rejected ?? [];
  const tasteTags = result?.taste_dna?.tags ?? [];
  const progItems = result?.programme?.items ?? [];

  return (
    <main style={{ background: "var(--void)", minHeight: "100vh", color: "var(--paper)" }}>
      <header style={{ padding: "20px 32px", borderBottom: "1px solid var(--rule)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <span className="micro-label">ADJACENT · CREATOR MODE</span>
          <h1 style={{ fontFamily: "var(--display)", fontSize: 28, fontWeight: 400, margin: "4px 0 0" }}>
            Position your film in its <em style={{ color: "#bcb4a7" }}>cultural world.</em>
          </h1>
        </div>
        <span style={{ display: "flex", gap: 8 }}>
          <Link href="/" className="intake-sample-btn" style={{ textDecoration: "none" }}>
            ← Home
          </Link>
          <Link href="/cinema" className="intake-sample-btn" style={{ textDecoration: "none" }}>
            Cinema Mode
          </Link>
        </span>
      </header>

      {/* ── Step navigation (M13.15): the creator journey at a glance ────── */}
      <nav className="step-nav" aria-label="Creator journey">
        <a href="#intake">01 · Your film</a>
        {result ? (
          <a href="#analysis">02 · Investigation</a>
        ) : (
          <span className="is-disabled" aria-disabled="true">02 · Investigation</span>
        )}
        {result?.cohorts ? (
          <a href="#fingerprint">03 · Fingerprint</a>
        ) : (
          <span className="is-disabled" aria-disabled="true">03 · Fingerprint</span>
        )}
        {result?.investigation ? (
          <a href="#brief">04 · Decision brief</a>
        ) : (
          <span className="is-disabled" aria-disabled="true">04 · Decision brief</span>
        )}
        <a href="#experiments" className="is-soft">05 · Experiments</a>
      </nav>

      <div style={{ maxWidth: 980, margin: "0 auto", padding: "40px 24px 80px" }}>
        {ytBanner && (
          <div className="evidence-panel" style={{ borderColor: "var(--amber)", marginBottom: 20 }}>
            <span className="mono-note">{ytBanner}</span>
          </div>
        )}
        {backendHealth?.public_demo && (
          <div className="evidence-panel" role="status" style={{ borderColor: "var(--amber)", marginBottom: 20 }}>
            <strong className="mono-note" style={{ display: "block", color: "var(--amber)" }}>
              PUBLIC DEMO MODE · FIXTURE DATA IS LABELLED
            </strong>
            <p style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.7, margin: "8px 0 0" }}>
              {backendHealth.live_creator_available
                ? "Bounded live Creator requests are enabled; upstream Qloo may still fail honestly."
                : "Live Creator requests are disabled. Use the labelled offline fixture demo."}
              {" Shared experiments, YouTube and synthesis are unavailable. Run records are temporary and expire."}
            </p>
          </div>
        )}
        {/* ── 1. Film intake ─────────────────────────────────────────── */}
        <div className="evidence-panel" id="intake">
          <h3>Your film</h3>
          <span className="mono-note" style={{ display: "block", marginBottom: 16 }}>
            ONLY THE TITLE IS REQUIRED · EVERYTHING ELSE STRENGTHENS THE EVIDENCE
          </span>
          <div style={{ display: "grid", gap: 12 }}>
            <label className="micro-label" style={{ display: "grid", gap: 6 }}>
              WORKING TITLE *
              <input className="intake-input" maxLength={160} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Neon Harbour" />
            </label>
            <label className="micro-label" style={{ display: "grid", gap: 6 }}>
              LOGLINE / DESCRIPTION
              <textarea className="intake-input" rows={2} maxLength={2000} value={logline} onChange={(e) => setLogline(e.target.value)} placeholder="A dockside night-shift romance told in three silent vignettes." />
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
              <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                GENRE
                <input className="intake-input" maxLength={120} value={genre} onChange={(e) => setGenre(e.target.value)} placeholder="drama" />
              </label>
              <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                LANGUAGE
                <input className="intake-input" maxLength={80} value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="English" />
              </label>
            </div>
            <label className="micro-label" style={{ display: "grid", gap: 6 }}>
              THEMES (COMMA-SEPARATED)
              <input className="intake-input" maxLength={604} value={themesText} onChange={(e) => setThemesText(e.target.value)} placeholder="isolation, night workers, coastal towns" />
            </label>
            <fieldset style={{ border: "1px solid var(--rule)", borderRadius: 6, padding: 12, margin: 0 }}>
              <legend className="micro-label" style={{ padding: "0 6px" }}>COMPARABLE WORKS / REFERENCES</legend>
              {referenceRows.map((row, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "minmax(0, 3fr) minmax(72px, 1fr) auto", gap: 8, marginBottom: 8 }}>
                  <input className="intake-input" maxLength={160} value={row.title} placeholder="Film, artist, book, game…"
                    aria-label={`Reference work ${i + 1}`}
                    onChange={(e) => setReferenceRows((rows) => rows.map((r, ri) => (ri === i ? { ...r, title: e.target.value } : r)))} />
                  <input className="intake-input" maxLength={4} value={row.year} placeholder="year" inputMode="numeric"
                    aria-label={`Reference year ${i + 1}`}
                    onChange={(e) => setReferenceRows((rows) => rows.map((r, ri) => (ri === i ? { ...r, year: e.target.value } : r)))} />
                  <button type="button" className="intake-sample-btn" aria-label={`Remove reference ${i + 1}`}
                    onClick={() => setReferenceRows((rows) => rows.filter((_, ri) => ri !== i))}>✕</button>
                </div>
              ))}
              <button type="button" className="intake-sample-btn" disabled={referenceRows.length >= 5}
                onClick={() => setReferenceRows((rows) => rows.length < 5 ? [...rows, { title: "", year: "" }] : rows)}>
                {referenceRows.length >= 5 ? "5 reference limit reached" : "+ Add reference"}
              </button>
            </fieldset>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
              <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                RELEASE GOAL
                <input className="intake-input" maxLength={300} value={releaseGoal} onChange={(e) => setReleaseGoal(e.target.value)} placeholder="YouTube premiere after festival window" />
              </label>
              <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                RELEASE LOCATION (OPTIONAL — ENABLES GEOGRAPHY)
                <input className="intake-input" maxLength={120} value={city} onChange={(e) => setCity(e.target.value)} placeholder="Lisbon, Portugal" />
              </label>
            </div>
            {formError && <p className="intake-form-error" role="alert">{formError}</p>}
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <button
                onClick={handleAnalyse}
                disabled={analysing || Boolean(backendHealth?.public_demo && !backendHealth.live_creator_available)}
                className="intake-submit"
              >
                {analysing
                  ? "Analysing…"
                  : backendHealth?.public_demo && !backendHealth.live_creator_available
                    ? "Live Creator disabled in public demo"
                    : "Analyse cultural position"}
              </button>
              <button onClick={startDemoRun} disabled={analysing} className="intake-sample-btn">
                View labelled fixture demo (offline)
              </button>
            </div>
            {error && (
              <div className="intake-form-error" role="alert" style={{ padding: 12, border: "1px solid rgba(138,80,72,0.4)", borderRadius: 6 }}>
                <strong style={{ display: "block", marginBottom: 4, ...mono, fontSize: 9 }}>
                  ANALYSIS ERROR — YOUR ENTRIES ARE PRESERVED ABOVE
                </strong>
                {error}
              </div>
            )}
            {analysing && (
              <div className="progress-rail" role="status" aria-live="polite" style={{ marginTop: 8 }}>
                {events.filter((e) => e.event === "trace").slice(-5).map((e, i) => (
                  <div className="progress-line" key={i}>
                    <span className="phase">{String(e.data?.phase ?? "…")}</span>
                    <span>{String(e.data?.message ?? "")}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── insufficiency / failure panels ─────────────────────────── */}
        {run && !analysing && insufficient && (
          <div className="insufficient-panel" style={{ marginTop: 24 }}>
            <h3>Not enough cultural evidence yet</h3>
            <p>{run.stop_message || "Qloo did not return enough verified signal for these seeds. Add more comparable works or themes — a refusal is an honest result."}</p>
          </div>
        )}
        {run && !analysing && failed && (
          <div className="insufficient-panel" role="alert" style={{ marginTop: 24, borderColor: "rgba(138,80,72,0.45)", background: "rgba(138,80,72,0.08)" }}>
            <h3 style={{ color: "#d4a89e" }}>The analysis could not complete</h3>
            <p>{run.error || run.stop_message || result?.evidence?.stop_message || "Unknown failure."}</p>
            {result && <p>Any partial evidence below is not a completed positioning result.</p>}
          </div>
        )}

        {/* ── 2. Cultural analysis ───────────────────────────────────── */}
        {result && (
          <div style={{ marginTop: 32 }}>
            <div style={{ marginBottom: 20, padding: "10px 14px", borderRadius: 6,
              background: resultTone.background,
              border: `1px solid ${resultTone.border}` }}>
              <span style={{ ...mono, fontSize: 9, letterSpacing: "0.1em", color: resultTone.color }}>
                {failed
                  ? `ANALYSIS FAILED · ${statusLabel(result.data_status ?? null)} · PARTIAL OUTPUT ONLY`
                  : insufficient
                    ? `INSUFFICIENT EVIDENCE · ${statusLabel(result.data_status ?? null)}`
                    : statusLabel(result.data_status ?? null)}
                {requestMode === "fixture" ? " · FIXTURE DEMO REQUESTED" : ""}
              </span>
            </div>

            <div className="evidence-panel" id="analysis">
              <h3>What was analysed</h3>
              <span className="mono-note" style={{ display: "block", marginBottom: 12 }}>
                {result.programme?.resolved_count ?? 0}/{result.programme?.total_count ?? 0} SEEDS RESOLVED AGAINST QLOO · UNRESOLVED SEEDS ARE EXCLUDED, NEVER GUESSED
              </span>
              <div style={{ display: "grid", gap: 6 }}>
                {progItems.map((item, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 12, flexWrap: "wrap" }}>
                    <span style={{ color: item.resolved ? "#7aba8a" : "#c97a6a" }}>{item.resolved ? "✓" : "✕"}</span>
                    <span>{item.title}</span>
                    {item.year != null && <span style={{ color: "#88837a" }}>({item.year})</span>}
                    {!item.resolved && <span className="mono-note">UNRESOLVED — EXCLUDED FROM EVIDENCE</span>}
                    {item.resolution_evidence && (
                      <span className="mono-note" style={{ color: item.resolved ? "#7aba8a" : "#c29a6e" }}>
                        {item.resolution_evidence.match_status}
                        {item.resolution_evidence.match_method ? ` · VIA ${item.resolution_evidence.match_method.toUpperCase()}` : ""}
                        {item.resolution_evidence.qloo_name ? ` · QLOO ${item.resolution_evidence.qloo_name}` : ""}
                        {item.resolution_evidence.qloo_year != null ? ` (${item.resolution_evidence.qloo_year})` : ""}
                        {item.resolution_evidence.qloo_entity_id ? ` · ENTITY ${item.resolution_evidence.qloo_entity_id}` : ""}
                        {resolutionCallLabel(item.resolution_evidence)}
                      </span>
                    )}
                    {(item.resolution_evidence?.verification_notes.length ?? 0) > 0 && (
                      <span className="mono-note" style={{ color: "#a7a39b" }}>
                        {item.resolution_evidence?.verification_notes.join(" · ")}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {tasteTags.length > 0 && (
              <div className="evidence-panel">
                <h3>Expressed cultural profile</h3>
                <span className="mono-note" style={{ display: "block", marginBottom: 12 }}>
                  QLOO AFFINITY 0–1 · SIMILARITY, NOT POPULARITY OR DEMAND
                </span>
                <div style={{ display: "grid", gap: 6 }}>
                  {tasteTags.slice(0, 10).map((tag, i) => (
                    <div className="bar-row" key={tag.tag_id || i}>
                      <span className="bar-label">{tag.name}</span>
                      <div className="bar-track">
                        <div className="bar-fill" style={{ width: `${Math.max(0, Math.min(1, tag.affinity ?? 0)) * 100}%` }} />
                      </div>
                      <span className="bar-value">{typeof tag.affinity === "number" ? tag.affinity.toFixed(2) : "—"}{tag.band ? ` · ${tag.band}` : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.cohorts && (
              <div className="evidence-panel" id="fingerprint">
                <h3>Cultural fingerprint</h3>
                <span className="mono-note" style={{ display: "block", marginBottom: 12 }}>
                  ADJACENT CULTURAL WORLDS AROUND YOUR FILM · DRAWN ONLY FROM THIS RUN&rsquo;S QLOO EVIDENCE
                </span>
                <AdjacencyGraph
                  filmTitle={(result.film as { title?: string } | undefined)?.title ?? title ?? "Your film"}
                  cohorts={result.cohorts}
                  bet={result.programme_bet}
                  dataStatus={result.data_status}
                  traceRows={traceRows}
                />
              </div>
            )}

            {ranked.length > 0 && (
              <div className="evidence-panel">
                <h3>Adjacent cultural worlds, ranked</h3>
                <span className="mono-note" style={{ display: "block", marginBottom: 12 }}>
                  {ranked.length} RANKED · {rejected.length} REJECTED WITH REASONS
                </span>
                <div style={{ display: "grid", gap: 14 }}>
                  {ranked.map((cohort) => (
                    <div key={cohort.cohort_id} style={{ padding: "14px 16px", border: "1px solid var(--rule)", borderRadius: 7 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 8 }}>
                        <span style={{ fontFamily: "var(--display)", fontSize: 20 }}>
                          <span style={{ ...mono, fontSize: 10, color: "var(--amber)", marginRight: 8 }}>0{cohort.rank}</span>
                          {cohort.domain.replace("urn:entity:", "")}
                        </span>
                        <span className="mono-note">
                          {cohort.member_count} MEMBERS · MEAN AFFINITY {typeof cohort.score?.mean_affinity === "number" ? cohort.score.mean_affinity.toFixed(2) : "—"}
                        </span>
                      </div>
                      <div style={{ display: "grid", gap: 6 }}>
                        {cohort.members.slice(0, 5).map((m, mi) => (
                          <div className="bar-row" key={m.entity_id || mi} style={{ gridTemplateColumns: "minmax(140px, 1.2fr) 2fr auto" }}>
                            <span className="bar-label">{m.name}</span>
                            <div className="bar-track">
                              <div className="bar-fill adjacent" style={{ width: `${Math.max(0, Math.min(1, m.affinity ?? 0)) * 100}%` }} />
                            </div>
                            <span className="bar-value">{typeof m.affinity === "number" ? m.affinity.toFixed(2) : "—"}{m.band ? ` · ${m.band}` : ""}</span>
                          </div>
                        ))}
                      </div>
                      {(cohort.excluded_members?.length ?? 0) > 0 && (
                        <details style={{ marginTop: 8 }}>
                          <summary className="mono-note" style={{ cursor: "pointer" }}>
                            {cohort.qualifying_count ?? cohort.members.length} OF {cohort.member_count} QUALIFY · {cohort.excluded_members?.length} EXCLUDED — AND WHY
                          </summary>
                          <div style={{ display: "grid", gap: 4, marginTop: 6 }}>
                            {cohort.excluded_members?.map((ex, ei) => (
                              <div key={ex.entity_id || ei} style={{ color: "#8a847a", fontSize: 11 }}>
                                {ex.name ?? ex.entity_id} — {ex.reason_code}
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  ))}
                </div>
                {rejected.length > 0 && (
                  <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--rule)" }}>
                    <span className="micro-label">REJECTED — AND WHY</span>
                    <div style={{ display: "grid", gap: 4, marginTop: 6 }}>
                      {rejected.map((r, ri) => (
                        <div key={r.cohort_id || ri} style={{ color: "#8a847a", fontSize: 11 }}>
                          {r.domain.replace("urn:entity:", "")} — {r.rejection_reason ?? "rejected"}{r.rejection_detail ? ` (${r.rejection_detail})` : ""}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {result.investigation && <InvestigationPanel inv={result.investigation} traceRows={traceRows} />}
            {!result.investigation && traceRows.length > 0 && <EvidenceTraceLog rows={traceRows} />}
            {result.investigation && runId && (
              <SynthesisBriefPanel
                runId={runId}
                filmTitle={(result.film as { title?: string } | undefined)?.title ?? title}
                inv={result.investigation}
                traceRows={traceRows}
                onSaved={(msg) => { setSaveState(msg); refreshExperiments(); }}
              />
            )}

            {/* ── Positioning Bet ────────────────────────────────────── */}
            {bet && (
              <div style={{ marginBottom: 24, padding: 24, background: "rgba(194,154,110,0.06)", border: "1px solid rgba(194,154,110,0.25)", borderRadius: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
                  <span className="eyebrow" style={{ color: "var(--amber)" }}>&#127919; POSITIONING BET</span>
                  <span style={{ ...mono, fontSize: 8, color: statusTone(bet.data_status ?? null).color }}>
                    DATA STATUS: {String(bet.data_status ?? "unknown").toUpperCase()}
                  </span>
                </div>
                <h3 style={{ fontFamily: "var(--display)", fontSize: 30, fontWeight: 400, margin: "0 0 8px" }}>
                  The {bet.primary?.domain.replace("urn:entity:", "")} world — via {bet.primary?.cohort_name}
                </h3>
                <p style={{ color: "#a7a39b", fontSize: 12, lineHeight: 1.7, marginBottom: 14 }}>
                  {bet.primary?.member_count} entities
                  {typeof bet.primary?.mean_affinity === "number" ? ` · mean affinity ${bet.primary.mean_affinity.toFixed(2)}` : ""}
                  {bet.primary?.call_id ? ` · call ${bet.primary.call_id}` : ""}
                  {bet.primary?.cohort_id ? ` · built from ranked cohort ${bet.primary.cohort_id} above` : ""}
                </p>
                <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, marginBottom: 12 }}>{bet.why}</p>
                {bet.primary?.call_id && (
                  <div style={{ marginBottom: 12 }}>
                    <span className="micro-label" style={{ marginBottom: 4 }}>PRIMARY EVIDENCE TRACE</span>
                    <EvidenceReferences refs={[bet.primary.call_id]} traceRows={traceRows} />
                  </div>
                )}
                {bet.cultural_bridge && (
                  <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, marginBottom: 12 }}>
                    <span className="micro-label" style={{ display: "inline", marginRight: 8 }}>BRIDGE</span>{bet.cultural_bridge}
                  </p>
                )}
                {bet.programming_direction && (
                  <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, marginBottom: 12 }}>
                    <span className="micro-label" style={{ display: "inline", marginRight: 8 }}>DIRECTION</span>{bet.programming_direction}
                  </p>
                )}
                {bet.geographic_signal && (
                  <p style={{ color: "#8a847a", fontSize: 12, lineHeight: 1.7, marginBottom: 12 }}>{bet.geographic_signal}</p>
                )}
                {bet.falsification_condition && (
                  <div style={{ marginTop: 12, padding: "12px 14px", background: "rgba(138,80,72,0.1)", border: "1px solid rgba(138,80,72,0.25)", borderRadius: 6 }}>
                    <span className="micro-label" style={{ color: "#c97a6a", marginBottom: 6, display: "block" }}>&#9888; FALSIFICATION CONDITION</span>
                    <p style={{ color: "#d4a89e", fontSize: 12, lineHeight: 1.7, margin: 0 }}>{bet.falsification_condition}</p>
                  </div>
                )}
              </div>
            )}

            {/* ── Test Card → experiment ─────────────────────────────── */}
            {card && (
              <article style={{ padding: 28, border: "1px solid var(--rule)", borderRadius: 8, background: "rgba(232,226,213,0.02)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
                  <span className="micro-label">EXPERIMENT · TEST CARD</span>
                  <span className="mono-note">DATA STATUS: {String(card.data_status ?? "unknown").toUpperCase()}</span>
                </div>
                <h3 style={{ fontFamily: "var(--display)", fontSize: 28, fontWeight: 400, margin: "0 0 20px" }}>{card.title}</h3>
                <div style={{ display: "grid", gap: 18 }}>
                  {([
                    ["PROGRAMME CONTEXT", card.programme_context],
                    ["AUDIENCE HYPOTHESIS", card.audience_hypothesis],
                    ["CULTURAL BRIDGE", card.cultural_bridge],
                    ["POSITIONING DIRECTION", card.programming_direction],
                    ["PRIMARY EVIDENCE", card.primary_evidence],
                    ["RUNNER-UP DIRECTION", card.runner_up],
                    ["SUCCESS CRITERIA (OBSERVABLE)", card.success_criteria],
                    ["OBSERVATION WINDOW", card.observation_window],
                  ] as [string, string | undefined][]).filter(([, v]) => v).map(([label, value]) => (
                    <div key={label}>
                      <span className="micro-label" style={{ marginBottom: 6, display: "block" }}>{label}</span>
                      <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, margin: 0 }}>{value}</p>
                    </div>
                  ))}
                  {card.falsification_condition && (
                    <div style={{ padding: "12px 14px", background: "rgba(138,80,72,0.1)", border: "1px solid rgba(138,80,72,0.25)", borderRadius: 6 }}>
                      <span className="micro-label" style={{ color: "#c97a6a", marginBottom: 6, display: "block" }}>&#9888; FALSIFICATION CONDITION</span>
                      <p style={{ color: "#d4a89e", fontSize: 12, lineHeight: 1.7, margin: 0 }}>{card.falsification_condition}</p>
                    </div>
                  )}
                  <div>
                    <span className="micro-label" style={{ marginBottom: 6, display: "block" }}>PROVENANCE</span>
                    <div style={{ display: "grid", gap: 4 }}>
                      {Object.entries(card.provenance ?? {}).map(([k, v]) => (
                        <div key={k} className="mono-note">
                          {k.toUpperCase()}: {k.endsWith("call_id") && typeof v === "string"
                            ? <EvidenceReferences refs={[v]} traceRows={traceRows} />
                            : String(v ?? "—")}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <div style={{ marginTop: 24, paddingTop: 18, borderTop: "1px solid var(--rule)", display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                  <button onClick={handleSaveExperiment} className="intake-submit" disabled={backendHealth?.public_demo}>
                    {backendHealth?.public_demo ? "Saving disabled in public demo" : "Save as planned experiment"}
                  </button>
                  {saveState && <span className="mono-note" role="status" aria-live="polite">{saveState}</span>}
                  {expError && <span className="intake-form-error" role="alert">{expError}</span>}
                </div>
              </article>
            )}
          </div>
        )}

        {/* ── 3. Experiment history ──────────────────────────────────── */}
        <div className="evidence-panel" style={{ marginTop: 32 }}>
          <h3 id="experiments">Your experiments</h3>
          <span className="mono-note" style={{ display: "block", marginBottom: 14 }}>
            PLANNED DECISIONS · SAVING DOES NOT EXECUTE · REAL OBSERVATIONS · HONEST EVALUATIONS · HISTORY IS NEVER REWRITTEN
          </span>
          {backendHealth?.public_demo ? (
            <p role="status" style={{ color: "#88837a", fontSize: 13, lineHeight: 1.8 }}>
              Shared experiment history is intentionally unavailable in this public demo; no shared records are read or written.
            </p>
          ) : experimentsError && (
            <div role="alert" className="intake-form-error" style={{ marginBottom: 12 }}>
              <p style={{ margin: 0 }}>
                The Research Log could not be loaded. {experiments.length > 0
                  ? "Showing the last successfully loaded records."
                  : "Saved records have not been checked, so this is not an empty-log result."}
                {` ${experimentsError}`}
              </p>
              <button type="button" className="intake-sample-btn" onClick={() => void refreshExperiments()} disabled={experimentsLoading} style={{ marginTop: 8 }}>
                {experimentsLoading ? "Retrying…" : "Retry Research Log"}
              </button>
            </div>
          )}
          {experimentsLoading && experiments.length === 0 && (
            <p role="status" aria-live="polite" style={{ color: "#88837a", fontSize: 13 }}>
              Loading saved experiments…
            </p>
          )}
          {experimentsLoading && experiments.length > 0 && (
            <p role="status" aria-live="polite" className="mono-note">Refreshing the Research Log…</p>
          )}
          {!experimentsLoading && !experimentsError && experiments.length === 0 && (
            <p style={{ color: "#88837a", fontSize: 13, lineHeight: 1.8 }}>
              No saved experiments were returned. Run an analysis (or the labelled fixture demo)
              and explicitly save its test card as a planned experiment. After release, record what
              genuinely happened — saving a plan does not execute it.
            </p>
          )}
          {experiments.length > 0 && (
            <div style={{ display: "grid", gap: 10 }}>
              {experiments.map((exp) => (
                <div key={exp.experiment_id} style={{ border: "1px solid var(--rule)", borderRadius: 7, padding: "12px 14px" }}>
                  <button
                    onClick={() => openExperiment(exp.experiment_id)}
                    aria-expanded={openExpId === exp.experiment_id}
                    aria-controls={`experiment-detail-${exp.experiment_id}`}
                    style={{ cursor: "pointer", display: "block", width: "100%", textAlign: "left", padding: 0, border: 0, background: "transparent", color: "inherit", font: "inherit" }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                      <span style={{ color: "#e9e3d8", fontSize: 14 }}>{exp.film_title}</span>
                      <span className="mono-note">
                        {String(exp.data_status).toUpperCase()}
                        {exp.latest_evaluation ? ` · ${exp.latest_evaluation}` : " · NO EVALUATION YET"}
                        {" · "}{exp.observation_count ?? 0} OBSERVATION(S)
                      </span>
                    </div>
                    <p style={{ color: "#8a847a", fontSize: 12, margin: "6px 0 0", lineHeight: 1.6 }}>
                      {exp.hypothesis.slice(0, 160)}{exp.hypothesis.length > 160 ? "…" : ""}
                    </p>
                  </button>
                  <div
                    id={`experiment-detail-${exp.experiment_id}`}
                    hidden={openExpId !== exp.experiment_id}
                  >
                    {openExpId === exp.experiment_id && (
                      <>
                        {loadingExpId === exp.experiment_id && (
                          <p role="status" aria-live="polite" className="mono-note" style={{ marginTop: 10 }}>
                            Loading the saved decision, observations, and evaluation history…
                          </p>
                        )}
                        {expDetailError && (
                          <div role="alert" className="intake-form-error" style={{ marginTop: 10 }}>
                            Could not load this experiment: {expDetailError}
                            <button type="button" className="intake-sample-btn" onClick={() => void loadExperimentDetail(exp.experiment_id)} style={{ marginTop: 8 }}>
                              Retry loading this experiment
                            </button>
                          </div>
                        )}
                        {expDetail && expDetail.experiment.experiment_id === exp.experiment_id && (
                          <ExperimentDetail
                            key={exp.experiment_id}
                            detail={expDetail}
                            onChanged={async () => {
                              setExpDetail(await getExperiment(exp.experiment_id));
                              refreshExperiments();
                            }}
                          />
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

// ─── Experiment detail: observations + evaluation, append-only ───────────────

function ExperimentDetail({
  detail,
  onChanged,
}: {
  detail: { experiment: ExperimentRecord; observations: ObservationRecord[]; evaluations: EvaluationRecord[] };
  onChanged: () => Promise<void>;
}) {
  const { experiment, observations, evaluations } = detail;
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [sourceTrace, setSourceTrace] = useState<TraceRow[]>([]);
  const [sourceTraceLoading, setSourceTraceLoading] = useState(Boolean(experiment.source_run_id));
  const [sourceTraceError, setSourceTraceError] = useState<string | null>(
    experiment.source_run_id ? null : "No source run reference was saved with this experiment."
  );
  const sourceTraceRequest = useRef(0);
  const sourceTraceScope = `research-${experiment.experiment_id}`;

  const loadSourceTrace = useCallback(async () => {
    const requestId = ++sourceTraceRequest.current;
    if (!experiment.source_run_id) {
      setSourceTrace([]);
      setSourceTraceLoading(false);
      setSourceTraceError("No source run reference was saved with this experiment.");
      return;
    }
    setSourceTrace([]);
    setSourceTraceLoading(true);
    setSourceTraceError(null);
    try {
      const runResponse = await getRun(experiment.source_run_id);
      if (requestId === sourceTraceRequest.current) setSourceTrace(runResponse.trace ?? []);
    } catch (err) {
      if (requestId === sourceTraceRequest.current) {
        setSourceTraceError(err instanceof Error ? err.message : "Could not load the source run trace");
      }
    } finally {
      if (requestId === sourceTraceRequest.current) setSourceTraceLoading(false);
    }
  }, [experiment.source_run_id]);

  useEffect(() => {
    void loadSourceTrace();
    return () => { sourceTraceRequest.current += 1; };
  }, [loadSourceTrace]);

  // observation form
  const [oKind, setOKind] = useState("ANALYTICS");
  const [oStatus, setOStatus] = useState("OBSERVED");
  const [oDate, setODate] = useState("");
  const [oViews, setOViews] = useState("");
  const [oWatchMin, setOWatchMin] = useState("");
  const [oInterp, setOInterp] = useState("");
  const [oLimits, setOLimits] = useState("");

  // evaluation form
  const [eOutcome, setEOutcome] = useState<"SUPPORTED" | "CONTRADICTED" | "INCONCLUSIVE">("INCONCLUSIVE");
  const [eRationale, setERationale] = useState("");
  const [eUnknowns, setEUnknowns] = useState("");

  async function submitObservation() {
    setBusy(true);
    setMsg(null);
    const metrics: Record<string, number | null> = {};
    if (oViews.trim() !== "") metrics.views = Number(oViews);
    if (oWatchMin.trim() !== "") metrics.watch_time_minutes = Number(oWatchMin);
    try {
      const resp = await addObservation(experiment.experiment_id, {
        request_id: `obs-${experiment.experiment_id}-${Date.now()}`,
        kind: oKind,
        measurement_status: oStatus,
        observed_on: oDate || null,
        metrics,
        interpretation: oInterp || null,
        limitations: oLimits || null,
        source: oKind === "ANALYTICS" ? "creator-reported" : "creator-reported",
      });
      setMsg(resp.duplicate ? "That observation was already recorded." : "Observation recorded.");
      setOViews(""); setOWatchMin(""); setOInterp(""); setOLimits(""); setODate("");
      await onChanged();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Could not record observation");
    } finally {
      setBusy(false);
    }
  }

  async function submitEvaluation() {
    if (!eRationale.trim()) {
      setMsg("An evaluation needs a rationale — what did the observations actually show?");
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      await addEvaluation(experiment.experiment_id, {
        request_id: `eval-${experiment.experiment_id}-${Date.now()}`,
        outcome: eOutcome,
        rationale: eRationale.trim(),
        observation_ids: observations.map((o) => o.observation_id),
        unknowns: eUnknowns || null,
      });
      setMsg("Evaluation recorded (previous evaluations are kept in history).");
      setERationale(""); setEUnknowns("");
      await onChanged();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Could not record evaluation");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--rule)", display: "grid", gap: 18 }}>
      <div>
        <span className="micro-label">SAVED DECISION (SNAPSHOT — NEVER REWRITTEN · NOT EXECUTED)</span>
        <p style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.7, margin: "6px 0 0" }}>{experiment.hypothesis}</p>
        {experiment.action_plan && (
          <p style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.7, margin: "6px 0 0" }}>
            <span className="mono-note">PLANNED ACTION: </span>{experiment.action_plan}
          </p>
        )}
        {experiment.success_criteria && (
          <p style={{ color: "#8a847a", fontSize: 12, lineHeight: 1.7, margin: "6px 0 0" }}>
            <span className="mono-note">SUCCESS CRITERIA: </span>{experiment.success_criteria}
          </p>
        )}
        {experiment.observation_window && (
          <p style={{ color: "#8a847a", fontSize: 12, lineHeight: 1.7, margin: "4px 0 0" }}>
            <span className="mono-note">WINDOW: </span>{experiment.observation_window}
          </p>
        )}
        <p className="mono-note" style={{ marginTop: 6 }}>
          SOURCE RUN: {experiment.source_run_id ?? "—"} · DATA STATUS: {String(experiment.data_status).toUpperCase()}
        </p>
      </div>

      <DecisionSummary
        detail={detail}
        traceRows={sourceTrace}
        traceScope={sourceTraceScope}
        traceAvailability={sourceTraceLoading ? "loading" : sourceTraceError ? "unavailable" : undefined}
      />
      {sourceTraceLoading && (
        <p role="status" aria-live="polite" className="mono-note">
          Loading the source run&apos;s recorded evidence trace…
        </p>
      )}
      {sourceTraceError && (
        <div role="status" className="evidence-trace-empty">
          <p style={{ margin: 0 }}>
            The source run trace is unavailable here. Saved call IDs remain identifiers, not independently inspectable evidence in this view.
            {` ${sourceTraceError}`}
          </p>
          {experiment.source_run_id && (
            <button type="button" className="intake-sample-btn" onClick={() => void loadSourceTrace()} style={{ marginTop: 8 }}>
              Retry source trace
            </button>
          )}
        </div>
      )}
      {!sourceTraceLoading && !sourceTraceError && (
        <EvidenceTraceLog rows={sourceTrace} scope={sourceTraceScope} />
      )}

      {/* observations */}
      <div>
        <span className="micro-label">OBSERVATIONS ({observations.length}) — ZERO IS A RESULT, EMPTY IS NOT</span>
        <div style={{ display: "grid", gap: 6, margin: "8px 0 12px" }}>
          {observations.map((o) => (
            <div key={o.observation_id} style={{ border: "1px solid var(--rule)", borderRadius: 6, padding: "8px 10px", fontSize: 12, color: "#b3aea4" }}>
              <span className="mono-note">{o.kind} · {o.measurement_status}{o.observed_on ? ` · ${o.observed_on}` : ""}{o.supersedes_id ? " · CORRECTION" : ""}</span>
              <div style={{ marginTop: 4 }}>
                {Object.entries(o.metrics ?? {}).map(([k, v]) => (
                  <span key={k} style={{ marginRight: 12 }}>{k}: {v === null ? "—" : String(v)}</span>
                ))}
                {Object.keys(o.metrics ?? {}).length === 0 && <span style={{ color: "#8a847a" }}>no metrics recorded</span>}
              </div>
              {o.interpretation && <div style={{ marginTop: 4, color: "#c29a6e" }}>creator interpretation: {o.interpretation}</div>}
              {o.limitations && <div style={{ marginTop: 2, color: "#8a847a" }}>limitations: {o.limitations}</div>}
            </div>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 8 }}>
          <select className="intake-input" value={oKind} onChange={(e) => setOKind(e.target.value)} aria-label="Observation kind">
            <option value="ANALYTICS">Analytics</option>
            <option value="SCREENING">Screening</option>
            <option value="FEEDBACK">Feedback</option>
            <option value="NOTE">Note</option>
          </select>
          <select className="intake-input" value={oStatus} onChange={(e) => setOStatus(e.target.value)} aria-label="Measurement status">
            <option value="OBSERVED">Observed</option>
            <option value="PARTIAL">Partial</option>
            <option value="MISSING">Missing</option>
            <option value="UNAVAILABLE">Unavailable</option>
            <option value="FAILED">Measurement failed</option>
          </select>
          <input className="intake-input" type="date" value={oDate} onChange={(e) => setODate(e.target.value)} aria-label="Observation date" />
          <input className="intake-input" value={oViews} onChange={(e) => setOViews(e.target.value)} placeholder="views (leave empty if unknown)" inputMode="numeric" aria-label="Views" />
          <input className="intake-input" value={oWatchMin} onChange={(e) => setOWatchMin(e.target.value)} placeholder="watch time minutes (optional)" inputMode="numeric" aria-label="Watch time" />
          <input className="intake-input" value={oInterp} onChange={(e) => setOInterp(e.target.value)} placeholder="your interpretation (kept separate)" aria-label="Interpretation" />
        </div>
        <input className="intake-input" style={{ marginTop: 8 }} value={oLimits} onChange={(e) => setOLimits(e.target.value)} placeholder="limitations / what's missing" aria-label="Limitations" />
        <button onClick={submitObservation} disabled={busy} className="intake-sample-btn" style={{ marginTop: 8 }}>
          Record observation
        </button>
        <YouTubePanel experimentId={experiment.experiment_id} onChanged={onChanged} />
      </div>

      {/* evaluations */}
      <div>
        <span className="micro-label">EVALUATIONS ({evaluations.length}) — APPEND-ONLY; CORRECTIONS SUPERSEDE</span>
        <div style={{ display: "grid", gap: 6, margin: "8px 0 12px" }}>
          {evaluations.map((ev) => (
            <div key={ev.evaluation_id} style={{ border: "1px solid var(--rule)", borderRadius: 6, padding: "8px 10px", fontSize: 12 }}>
              <span className="mono-note" style={{ color: ev.outcome === "SUPPORTED" ? "#7aba8a" : ev.outcome === "CONTRADICTED" ? "#c97a6a" : "#c29a6e" }}>
                {ev.outcome}{ev.supersedes_id ? " · SUPERSEDES EARLIER EVALUATION" : ""}
              </span>
              <p style={{ color: "#b3aea4", margin: "4px 0 0", lineHeight: 1.6 }}>{ev.rationale}</p>
              {ev.unknowns && <p style={{ color: "#8a847a", margin: "4px 0 0" }}>unknown: {ev.unknowns}</p>}
            </div>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 8 }}>
          <select className="intake-input" value={eOutcome} onChange={(e) => setEOutcome(e.target.value as typeof eOutcome)} aria-label="Evaluation outcome">
            <option value="SUPPORTED">Supported</option>
            <option value="CONTRADICTED">Contradicted</option>
            <option value="INCONCLUSIVE">Inconclusive</option>
          </select>
          <input className="intake-input" value={eRationale} onChange={(e) => setERationale(e.target.value)} placeholder="what did the observations actually show?" aria-label="Evaluation rationale" />
        </div>
        <input className="intake-input" style={{ marginTop: 8 }} value={eUnknowns} onChange={(e) => setEUnknowns(e.target.value)} placeholder="what remains unknown" aria-label="Unknowns" />
        <button onClick={submitEvaluation} disabled={busy} className="intake-sample-btn" style={{ marginTop: 8 }}>
          Record evaluation
        </button>
      </div>

      {msg && <p className="mono-note" role="status" aria-live="polite">{msg}</p>}
    </div>
  );
}

function parseEvidenceRef(raw: string | null): {
  provider?: string;
  data_status?: string;
  video_id?: string;
  period?: { start_date?: string; end_date?: string };
  retrieved_at?: string;
  row_count?: number;
} | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function DecisionSummary({
  detail,
  traceRows,
  traceScope,
  traceAvailability,
}: {
  detail: { experiment: ExperimentRecord; observations: ObservationRecord[]; evaluations: EvaluationRecord[] };
  traceRows: TraceRow[];
  traceScope: string;
  traceAvailability?: "loading" | "unavailable";
}) {
  const { experiment, observations, evaluations } = detail;
  const bet = experiment.source_bet as {
    primary?: { cohort_id?: string; cohort_name?: string };
  } | null;
  const provenance = experiment.provenance ?? {};
  const synthesisSnapshot =
    provenance.synthesis_snapshot && typeof provenance.synthesis_snapshot === "object" && !Array.isArray(provenance.synthesis_snapshot)
      ? provenance.synthesis_snapshot as Record<string, unknown>
      : null;
  const adoptedProposal =
    provenance.adopted_proposal && typeof provenance.adopted_proposal === "object" && !Array.isArray(provenance.adopted_proposal)
      ? provenance.adopted_proposal as Record<string, unknown>
      : null;
  const readRefs = (value: unknown): string[] =>
    Array.isArray(value) ? value.filter((ref): ref is string => typeof ref === "string") : [];
  const evidenceRefs = [...new Set([
    ...readRefs(provenance.evidence_refs),
    ...readRefs(synthesisSnapshot?.evidence_refs),
  ])];
  const unresolvedEvidenceRefs = [...new Set([
    ...readRefs(provenance.unresolved_evidence_refs),
    ...readRefs(synthesisSnapshot?.unresolved_evidence_refs),
  ])];
  const creatorEdits = Array.isArray(provenance.creator_edits)
    ? provenance.creator_edits.filter((field): field is string => typeof field === "string")
    : [];
  const originalHypothesis = typeof adoptedProposal?.hypothesis === "string" ? adoptedProposal.hypothesis : null;
  const originalActionPlan = typeof adoptedProposal?.action_plan === "string" ? adoptedProposal.action_plan : null;
  const originalSuccessCriteria = typeof adoptedProposal?.success_criteria === "string" ? adoptedProposal.success_criteria : null;
  const originalObservationWindow = typeof adoptedProposal?.observation_window === "string" ? adoptedProposal.observation_window : null;
  const synthesisMethod = typeof synthesisSnapshot?.method === "string" ? synthesisSnapshot.method : null;
  // Evaluations append as a superseding chain; the last record is current and
  // earlier records remain in the history below rather than being re-selected.
  const current = evaluations.length > 0 ? evaluations[evaluations.length - 1] : null;
  const youtubeObs = observations.filter((o) =>
    (o.source ?? "").includes("youtube")
  );
  const otherObs = observations.filter((o) => !(o.source ?? "").includes("youtube") && o.source !== "policy_deletion");
  const periods = youtubeObs
    .map((o) => parseEvidenceRef(o.evidence_ref)?.period)
    .filter((p): p is { start_date?: string; end_date?: string } => Boolean(p));

  return (
    <div style={{ border: "1px solid var(--rule)", borderRadius: 8, padding: "12px 14px" }}>
      <span className="micro-label">DECISION SUMMARY — HYPOTHESIZED · OBSERVED · CONCLUDED</span>
      <dl style={{ display: "grid", gap: 8, margin: "10px 0 0", fontSize: 12 }}>
        <div>
          <dt className="mono-note" style={{ color: "#8a847a" }}>HYPOTHESIZED (SAVED PLAN — NOT EXECUTED)</dt>
          <dd style={{ color: "#b3aea4", margin: "2px 0 0", lineHeight: 1.6 }}>
            {experiment.hypothesis}
            {bet?.primary?.cohort_name && (
              <span className="mono-note"> · BET COHORT: {bet.primary.cohort_name}</span>
            )}
            <span className="mono-note"> · EVIDENCE: {String(experiment.data_status).toUpperCase()}</span>
          </dd>
        </div>
        {adoptedProposal && (
          <div style={{ marginLeft: 10, paddingLeft: 10, borderLeft: "1px solid var(--rule)" }}>
            <dt className="mono-note" style={{ color: "#8a847a" }}>ORIGINAL PROPOSAL (SAVED SEPARATELY FROM YOUR EDITS)</dt>
            <dd style={{ color: "#b3aea4", margin: "2px 0 0", lineHeight: 1.6 }}>
              {originalHypothesis && <div>Original hypothesis: {originalHypothesis}</div>}
              {originalActionPlan && <div>Original action plan: {originalActionPlan}</div>}
              {originalSuccessCriteria && <div>Original success criteria: {originalSuccessCriteria}</div>}
              {originalObservationWindow && <div>Original observation window: {originalObservationWindow}</div>}
              <div className="mono-note">
                CREATOR-EDITED FIELDS: {creatorEdits.length > 0
                  ? creatorEdits.join(", ")
                  : "none recorded for hypothesis, action plan, success criteria, or observation window"}
                {synthesisMethod ? ` · SYNTHESIS METHOD: ${synthesisMethod}` : ""}
              </div>
            </dd>
          </div>
        )}
        <div>
          <dt className="mono-note" style={{ color: "#8a847a" }}>SAVED EVIDENCE REFERENCES</dt>
          <dd className="mono-note" style={{ color: "#b3aea4", margin: "2px 0 0", lineHeight: 1.6 }}>
            {experiment.source_run_id && <div>SOURCE RUN: {experiment.source_run_id}</div>}
              {evidenceRefs.length > 0
                ? <div>CALL IDS: <EvidenceReferences
                    refs={evidenceRefs}
                    traceRows={traceRows}
                    scope={traceScope}
                    availability={traceAvailability}
                  /></div>
                : <div>No call references are present in this saved provenance.</div>}
            {typeof synthesisSnapshot?.evidence_ref_status === "string" && (
              <div>REFERENCE STATUS: {synthesisSnapshot.evidence_ref_status}</div>
            )}
            {unresolvedEvidenceRefs.length > 0 && (
              <div className="evidence-trace-unresolved">
                UNRESOLVED — NOT STORED AS PROOF: {unresolvedEvidenceRefs.join(", ")}
              </div>
            )}
          </dd>
        </div>
        <div>
          <dt className="mono-note" style={{ color: "#8a847a" }}>OBSERVED (measured, never predicted)</dt>
          <dd style={{ color: "#b3aea4", margin: "2px 0 0", lineHeight: 1.6 }}>
            {observations.length === 0 && "Nothing observed yet."}
            {youtubeObs.length > 0 && (
              <span>
                {youtubeObs.length} YouTube observation(s)
                {periods.length > 0 && (
                  <span className="mono-note">
                    {" "}· PERIOD(S): {periods.map((p) => `${p.start_date}→${p.end_date}`).join(", ")}
                  </span>
                )}
              </span>
            )}
            {youtubeObs.length > 0 && otherObs.length > 0 && <span> · </span>}
            {otherObs.length > 0 && <span>{otherObs.length} manually recorded observation(s)</span>}
          </dd>
        </div>
        <div>
          <dt className="mono-note" style={{ color: "#8a847a" }}>CONCLUDED (latest evaluation, corrections kept)</dt>
          <dd style={{ margin: "2px 0 0", lineHeight: 1.6 }}>
            {current ? (
              <>
                <span style={{ color: current.outcome === "SUPPORTED" ? "#7aba8a" : current.outcome === "CONTRADICTED" ? "#c97a6a" : "#c29a6e" }}>
                  {current.outcome}
                </span>
                <span style={{ color: "#b3aea4" }}> — {current.rationale}</span>
              </>
            ) : (
              <span style={{ color: "#b3aea4" }}>Not yet evaluated — record observations first.</span>
            )}
          </dd>
        </div>
        <div>
          <dt className="mono-note" style={{ color: "#8a847a" }}>STILL MISSING</dt>
          <dd style={{ color: "#b3aea4", margin: "2px 0 0", lineHeight: 1.6 }}>
            {experiment.success_criteria
              ? `Success criteria to evaluate: ${experiment.success_criteria}`
              : "No success criteria recorded."}
            {current?.unknowns ? ` · Unknown: ${current.unknowns}` : ""}
          </dd>
        </div>
      </dl>
      <p className="mono-note" style={{ marginTop: 8, color: "#8a847a" }}>
        MEASUREMENTS ARE OBSERVATIONS, NOT PROOF OF CAUSE — CULTURAL AFFINITY ≠ VIEWERSHIP.
      </p>
    </div>
  );
}

function YouTubePanel({ experimentId, onChanged }: { experimentId: string; onChanged: () => Promise<void> }) {
  const [status, setStatus] = useState<YouTubeStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [videos, setVideos] = useState<YouTubeVideo[] | null>(null);
  const [videosLoading, setVideosLoading] = useState(false);
  const [videosError, setVideosError] = useState<string | null>(null);
  const [videosNote, setVideosNote] = useState<string | null>(null);
  const [videoId, setVideoId] = useState("");
  const today = new Date().toISOString().slice(0, 10);
  const twoWeeksAgo = new Date(Date.now() - 13 * 86400000).toISOString().slice(0, 10);
  const [startDate, setStartDate] = useState(twoWeeksAgo);
  const [endDate, setEndDate] = useState(today);
  const [variantLabel, setVariantLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const statusRequest = useRef(0);
  const videosRequest = useRef(0);

  const loadStatus = useCallback(async () => {
    const requestId = ++statusRequest.current;
    setStatusLoading(true);
    setStatus(null);
    setStatusError(null);
    try {
      const nextStatus = await youtubeStatus();
      if (requestId === statusRequest.current) setStatus(nextStatus);
    } catch (err) {
      if (requestId === statusRequest.current) {
        setStatus(null);
        setStatusError(err instanceof Error ? err.message : "Could not load YouTube connection status");
      }
    } finally {
      if (requestId === statusRequest.current) setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
    return () => { statusRequest.current += 1; };
  }, [loadStatus]);

  const loadVideos = useCallback(async () => {
    const requestId = ++videosRequest.current;
    if (!status?.connected) {
      setVideos(null);
      setVideosLoading(false);
      setVideosError(null);
      setVideosNote(null);
      return;
    }
    setVideos(null);
    setVideosLoading(true);
    setVideosError(null);
    setVideosNote(null);
    try {
      const response = await youtubeVideos();
      if (requestId === videosRequest.current) {
        setVideos(response.videos);
        setVideosNote(response.note || null);
      }
    } catch (err) {
      if (requestId === videosRequest.current) {
        setVideos(null);
        setVideosError(err instanceof Error ? err.message : "Could not load uploads");
      }
    } finally {
      if (requestId === videosRequest.current) setVideosLoading(false);
    }
  }, [status?.connected, status?.mode]);

  useEffect(() => {
    void loadVideos();
    return () => { videosRequest.current += 1; };
  }, [loadVideos]);

  async function record() {
    if (!videoId) {
      setMsg("Select the published video that corresponds to this experiment.");
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const resp = await recordYouTubeObservation(experimentId, {
        request_id: `obs-yt-${experimentId}-${Date.now()}`,
        video_id: videoId,
        start_date: startDate,
        end_date: endDate,
        variant_label: variantLabel.trim() || null,
      });
      setMsg(
        resp.duplicate
          ? "That fetch was already recorded (duplicate request)."
          : resp.observation.measurement_status === "OBSERVED"
            ? "Analytics recorded as an observation with full provenance."
            : "YouTube returned no rows — recorded as PARTIAL (ambiguous, not zero)."
      );
      await onChanged();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Could not record YouTube observation");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setMsg(null);
    try {
      const res = await disconnectYouTube();
      setMsg(
        `Disconnected. Credentials deleted; ${res.youtube_observations_deleted} YouTube-sourced observation(s) deleted per YouTube policy (tombstones kept).`
      );
      await onChanged();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Could not disconnect");
    } finally {
      setBusy(false);
      loadStatus();
    }
  }

  return (
    <div style={{ marginTop: 14, border: "1px dashed var(--rule)", borderRadius: 8, padding: "12px 14px" }}>
      {statusLoading && (
        <p role="status" aria-live="polite" className="mono-note" style={{ margin: "6px 0 0" }}>
          Checking YouTube connection status…
        </p>
      )}
      {!statusLoading && statusError && (
        <div role="alert" className="intake-form-error" style={{ marginTop: 8 }}>
          Connection status could not be checked. No authorization state is assumed. {statusError}
          <button type="button" className="intake-sample-btn" onClick={() => void loadStatus()} style={{ marginTop: 8 }}>
            Retry YouTube status
          </button>
        </div>
      )}
      {!statusLoading && !statusError && !status && (
        <p role="status" className="mono-note" style={{ marginTop: 8 }}>
          No YouTube connection status was returned; no authorization action is offered.
        </p>
      )}
      {!statusLoading && !statusError && status?.mode === "mock" && (
        <p className="mono-note" style={{ color: "#c29a6e", margin: "6px 0 0" }}>
          MOCK MODE — DEMO DATA, NOT REAL YOUTUBE ANALYTICS
        </p>
      )}

      {!statusLoading && !statusError && status && !status.connected && status.mode !== "mock" && (
        <>
          {!status.disabled_reason && (
            <p style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.6, margin: "6px 0 8px" }}>
              Connect your own YouTube channel (read-only: youtube.readonly +
              yt-analytics.readonly) to attach real per-video analytics to this
              experiment. Nothing is accessed without your explicit consent, and
              disconnecting deletes the stored data.
            </p>
          )}
          {status.disabled_reason ? (
            <p role="status" className="mono-note" style={{ color: "#8a847a" }}>
              {status.disabled_reason}
            </p>
          ) : status.mode === "not_configured" ? (
            <p className="mono-note" style={{ color: "#8a847a" }}>
              OAUTH NOT CONFIGURED ON THIS DEPLOYMENT — SEE
              DOCS/M13_10_YOUTUBE_ANALYTICS_INTEGRATION.MD
            </p>
          ) : (
            <button className="intake-sample-btn" onClick={beginYouTubeAuthorization}>
              Connect YouTube channel
            </button>
          )}
        </>
      )}

      {!statusLoading && !statusError && status?.connected && (
        <>
          <p className="mono-note" style={{ margin: "6px 0 8px" }}>
            CONNECTED: {status.connection?.channel_title ?? "channel"} ·{" "}
            {status.connection?.days_since_connection ?? 0} DAY(S)
            {status.connection?.reauthorization_recommended
              ? " · REAUTHORIZATION RECOMMENDED (30-DAY POLICY)"
              : ""}
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 8 }}>
            <select
              className="intake-input"
              value={videoId}
              onChange={(e) => setVideoId(e.target.value)}
              aria-label="Published video"
            >
              <option value="">
                {videosLoading
                  ? "Loading uploads…"
                  : videosError
                    ? "Uploads unavailable"
                    : videos?.length
                      ? "Select the published video…"
                      : videos
                        ? "No uploads returned"
                        : "Uploads not checked"}
              </option>
              {(videos ?? []).map((v) => (
                <option key={v.video_id} value={v.video_id}>
                  {v.title ?? v.video_id}
                </option>
              ))}
            </select>
            <input
              className="intake-input"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              aria-label="Period start"
            />
            <input
              className="intake-input"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              aria-label="Period end"
            />
          </div>
          {videosError && (
            <div role="alert" className="intake-form-error" style={{ marginTop: 8 }}>
              Could not load uploads: {videosError}
              <button type="button" className="intake-sample-btn" onClick={() => void loadVideos()} style={{ marginTop: 8 }}>
                Retry uploads
              </button>
            </div>
          )}
          {!videosLoading && !videosError && videos?.length === 0 && (
            <p role="status" className="mono-note" style={{ marginTop: 6 }}>
              {videosNote ?? "No uploads were returned for this channel."}
            </p>
          )}
          {videosNote && videos?.length !== 0 && (
            <p className="mono-note" style={{ marginTop: 6 }}>{videosNote}</p>
          )}
          <input
            className="intake-input"
            style={{ marginTop: 8 }}
            value={variantLabel}
            onChange={(e) => setVariantLabel(e.target.value)}
            placeholder="variant label if A/B testing (e.g. 'title A') — optional"
            aria-label="Variant label"
          />
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button className="intake-sample-btn" onClick={record} disabled={busy || videosLoading || Boolean(videosError) || !videoId}>
              Fetch analytics &amp; record observation
            </button>
            <button
              className="intake-sample-btn"
              onClick={disconnect}
              disabled={busy}
              style={{ borderColor: "#6a4a42" }}
            >
              Disconnect
            </button>
          </div>
          <p className="mono-note" style={{ marginTop: 8, color: "#8a847a" }}>
            FETCHES ONE VIDEO&apos;S VIEWS, WATCH TIME AND AVERAGE VIEW DURATION FOR
            THE SELECTED PERIOD — NEVER CHANNEL TOTALS, NEVER PREDICTIONS.
          </p>
        </>
      )}

      {msg && <p className="mono-note" role="status" aria-live="polite" style={{ marginTop: 8 }}>{msg}</p>}
    </div>
  );
}

// ── Decision brief (M13.13): on-demand Role-B synthesis, honestly labelled ──
// Minimal integration wiring only — no visual redesign (separate workstream).
function SynthesisBriefPanel({
  runId,
  filmTitle,
  inv,
  traceRows,
  onSaved,
}: {
  runId: string;
  filmTitle: string;
  inv: InvestigationData;
  traceRows: TraceRow[];
  onSaved: (msg: string) => void;
}) {
  const [status, setStatus] = useState<SynthesisStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [brief, setBrief] = useState<SynthesisResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Adoption draft (M13.14): a proposal becomes a saved experiment ONLY
  // through an explicit, editable, confirmed draft — never silently.
  const [draft, setDraft] = useState<{
    hypothesis: string;
    action_plan: string;
    success_criteria: string;
    observation_window: string;
  } | null>(null);
  const [adoptMsg, setAdoptMsg] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStatusLoading(true);
    setStatus(null);
    setStatusError(null);
    setBrief(null);
    setDraft(null);
    setAdoptMsg(null);
    setError(null);
    getSynthesisStatus()
      .then((st) => { if (!cancelled) setStatus(st); })
      .catch((err) => {
        if (!cancelled) {
          setStatus(null);
          setStatusError(err instanceof Error ? err.message : "Synthesis availability could not be checked");
        }
      })
      .finally(() => { if (!cancelled) setStatusLoading(false); });
    return () => { cancelled = true; };
  }, [runId]);

  function generate() {
    setBusy(true);
    setError(null);
    synthesizeRun(runId)
      .then(setBrief)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not generate the brief"))
      .finally(() => setBusy(false));
  }

  function startAdoption() {
    if (!brief) return;
    const prop = brief.synthesis.experiment_proposal;
    setAdoptMsg(null);
    setDraft({
      hypothesis:
        prop.kind === "test"
          ? prop.hypothesis
          : "No supported hypothesis yet — this is an information-gathering step, not a positioning test.",
      action_plan: prop.action_plan,
      success_criteria: prop.success_criteria,
      observation_window: prop.observation_window,
    });
  }

  async function confirmAdoption() {
    if (!brief || !draft) return;
    setBusy(true);
    setError(null);
    try {
      const prop = brief.synthesis.experiment_proposal;
      const resp = await saveExperiment({
        request_id: `exp-${runId}`, // one saved decision per run — replay-safe
        film_title: filmTitle,
        hypothesis: draft.hypothesis,
        success_criteria: draft.success_criteria,
        observation_window: draft.observation_window,
        action_plan: draft.action_plan,
        data_status: inv.data_status,
        source_run_id: runId,
        source_bet: {},
        provenance: {},
        film_context: (inv.film ?? {}) as Record<string, unknown>,
        investigation_summary: {
          investigation_id: inv.investigation_id,
          data_status: inv.data_status,
          primary_hypothesis: inv.hypotheses.primary?.statement ?? null,
          limitations: inv.limitations ?? [],
          open_questions: inv.open_questions ?? [],
        },
        evidence_refs: inv.provenance?.call_ids ?? [],
        // Immutable snapshot of the synthesis that informed this decision.
        synthesis_snapshot: {
          investigation_id: inv.investigation_id,
          source_run_id: runId,
          schema_version: brief.metadata.schema_version,
          method: brief.metadata.method,
          provider_kind: brief.metadata.provider_kind,
          model: brief.metadata.model,
          validation: brief.metadata.validation,
          summary: brief.synthesis.summary,
          hypothesis_restated: brief.synthesis.hypothesis_restated,
          claims: brief.synthesis.claims,
          caveats: brief.synthesis.caveats,
          limitations: inv.limitations ?? [],
          evidence_refs: inv.provenance?.call_ids ?? [],
          data_status: inv.data_status,
          experiment_proposal: prop,
        },
        // The model's ORIGINAL proposal, kept distinct from the saved fields
        // so the creator's manual edits are attributable to the creator.
        adopted_proposal: {
          kind: prop.kind,
          hypothesis: prop.hypothesis,
          action_plan: prop.action_plan,
          success_criteria: prop.success_criteria,
          observation_window: prop.observation_window,
          falsification: prop.falsification,
          relevant_metrics: prop.relevant_metrics,
          assumptions: prop.assumptions,
          limitations: prop.limitations,
        },
      });
      setDraft(null);
      setAdoptMsg(
        resp.duplicate
          ? "This analysis run already has a saved decision — showing the original. Nothing was overwritten."
          : prop.kind === "information_gathering"
            ? "Saved as an information-gathering plan (no positioning hypothesis was supported). It has not been executed."
            : "Saved as a planned experiment from the adopted proposal. This records intent; it does not execute the experiment."
      );
      onSaved(resp.duplicate ? "Existing saved decision retained." : "Adopted proposal saved as the planned experiment.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the adopted experiment");
    } finally {
      setBusy(false);
    }
  }

  const method = brief?.metadata.method;
  const methodLabel =
    method === "live_llm" ? "LIVE MODEL SYNTHESIS"
    : method === "stub" ? "STUB PROVIDER — NOT A REAL MODEL RESULT"
    : method === "deterministic_fallback" ? "DETERMINISTIC FALLBACK — MODEL OUTPUT UNAVAILABLE OR REJECTED"
    : null;

  return (
    <section id="brief" style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--rule)" }}>
      <h3>Decision brief (optional)</h3>
      {statusLoading && <p style={{ color: "#8a847a", fontSize: 12 }}>Checking synthesis availability…</p>}
      {!statusLoading && statusError && (
        <p role="alert" style={{ color: "#8a847a", fontSize: 12 }}>
          Availability could not be checked — {statusError}. The investigation above remains available; no model result is assumed.
        </p>
      )}
      {!statusLoading && !statusError && !status && (
        <p style={{ color: "#8a847a", fontSize: 12 }}>No synthesis availability status was returned.</p>
      )}
      {!statusLoading && status && !status.available && (
        <p style={{ color: "#8a847a", fontSize: 12 }}>
          Unavailable — {status.blocked_reason ?? "no provider configured."} The investigation
          above is complete and does not depend on it.
        </p>
      )}
      {!statusLoading && status?.available && !brief && (
        <button type="button" onClick={generate} disabled={busy}>
          {busy ? "Generating…" : "Generate decision brief"}
        </button>
      )}
      {error && <p role="alert" style={{ color: "#b4553f", fontSize: 12 }}>{error}</p>}
      {brief && (
        <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
          {methodLabel && <span className="micro-label">{methodLabel}</span>}
          {brief.metadata.llm_error && (
            <p style={{ color: "#8a847a", fontSize: 12 }}>Reason: {brief.metadata.llm_error}</p>
          )}
          <p style={{ fontSize: 13 }}>{brief.synthesis.summary}</p>
          <p style={{ fontSize: 13 }}><strong>Hypothesis:</strong> {brief.synthesis.hypothesis_restated}</p>
          {brief.synthesis.claims?.length > 0 && (
            <div>
              <span className="micro-label">CLAIMS & EVIDENCE</span>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18, display: "grid", gap: 6 }}>
                {brief.synthesis.claims.map((c, i) => (
                  <li key={i} style={{ fontSize: 12 }}>
                    <span className="micro-label">{c.claim_type}</span> {c.statement}
                    {c.evidence_refs?.length > 0 ? (
                      <EvidenceReferences refs={c.evidence_refs} traceRows={traceRows} />
                    ) : (
                      <span className="mono-note"> · no call reference supplied</span>
                    )}
                    {c.limitations ? <em style={{ color: "#8a847a" }}> — {c.limitations}</em> : null}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {brief.synthesis.caveats?.length > 0 && (
            <div>
              <span className="micro-label">CAVEATS</span>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 12 }}>
                {brief.synthesis.caveats.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}
          {brief.synthesis.experiment_proposal && !draft && (
            <div style={{ display: "grid", gap: 6 }}>
              <span className="micro-label">
                {brief.synthesis.experiment_proposal.kind === "test"
                  ? "PROPOSED EXPERIMENT (not yet saved)"
                  : "PROPOSED NEXT STEP — INFORMATION GATHERING (no supported hypothesis)"}
              </span>
              <p style={{ fontSize: 12 }}>
                {brief.synthesis.experiment_proposal.action_plan}
              </p>
              <p className="mono-note">Reviewing opens an unsaved draft. It does not adopt or execute the proposal.</p>
              <button type="button" onClick={startAdoption}>
                {brief.synthesis.experiment_proposal.kind === "test"
                  ? "Review and edit proposal"
                  : "Review information-gathering plan"}
              </button>
            </div>
          )}
          {draft && (
            <div style={{ display: "grid", gap: 6, marginTop: 6 }}>
              <span className="micro-label">REVIEW & EDIT BEFORE SAVING — nothing is saved yet</span>
              {(["hypothesis", "action_plan", "success_criteria", "observation_window"] as const).map((f) => (
                <label key={f} style={{ fontSize: 11, display: "grid", gap: 2 }}>
                  {f.replace(/_/g, " ")}
                  <textarea
                    value={draft[f]}
                    rows={2}
                    onChange={(e) => setDraft({ ...draft, [f]: e.target.value })}
                    style={{ fontFamily: "var(--mono)", fontSize: 11 }}
                  />
                </label>
              ))}
              <div style={{ display: "flex", gap: 8 }}>
                <button type="button" onClick={confirmAdoption} disabled={busy}>
                  {busy ? "Saving…" : "Confirm adoption and save as planned"}
                </button>
                <button type="button" onClick={() => setDraft(null)} disabled={busy}>
                  Cancel
                </button>
              </div>
            </div>
          )}
          {adoptMsg && <p role="status" aria-live="polite" style={{ color: "#8a847a", fontSize: 12 }}>{adoptMsg}</p>}
          <p style={{ color: "#8a847a", fontSize: 10, ...mono }}>
            method: {brief.metadata.method} · validation: {brief.metadata.validation}
          </p>
        </div>
      )}
    </section>
  );
}

function InvestigationPanel({
  inv,
  traceRows,
}: {
  inv: InvestigationData;
  traceRows: TraceRow[];
}) {
  const statusChip = (status: string) => {
    const color =
      status === "answered" ? "#7aba8a" : status === "insufficient" ? "#c29a6e" : "#8a847a";
    return <span className="mono-note" style={{ color }}>{status.toUpperCase()}</span>;
  };
  const investigationStatus =
    inv.data_status === "measured"
      ? "MEASURED QLOO DATA"
      : inv.data_status === "fixture"
        ? "FIXTURE DEMONSTRATION — NOT LIVE QLOO DATA"
        : "DATA STATUS UNKNOWN";

  return (
    <section className="evidence-panel" style={{ marginTop: 24 }}>
      <h3>Cultural investigation</h3>
      <span className="mono-note" style={{ display: "block", marginBottom: 14 }}>
        WHAT THE AGENT ASKED · WHICH TOOL ANSWERED · WHAT THE RECORDED EVIDENCE SUPPORTS · {investigationStatus}
      </span>

      <div style={{ display: "grid", gap: 10 }}>
        {inv.questions.map((q) => (
          <article key={q.id} style={{ border: "1px solid var(--rule)", borderRadius: 6, padding: "10px 12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
              <strong style={{ fontWeight: 500, fontSize: 13 }}>{q.question}</strong>
              {statusChip(q.status)}
            </div>
            <p style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.6, margin: "6px 0 0" }}>{q.summary}</p>
            <div style={{ display: "grid", gap: 4, marginTop: 6 }}>
              <span className="mono-note">TOOL: {q.tool} · {q.operation}</span>
              <span className="mono-note">EVIDENCE REFERENCES</span>
              {(q.evidence_refs?.length ?? 0) > 0 ? (
                <EvidenceReferences refs={q.evidence_refs} traceRows={traceRows} />
              ) : (
                <span className="evidence-trace-unresolved">No call reference supplied for this question.</span>
              )}
            </div>
          </article>
        ))}
      </div>

      {inv.findings.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <span className="micro-label">FINDINGS — SOURCE FACTS vs INTERPRETATION</span>
          <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
            {inv.findings.map((f, i) => (
              <div key={i} style={{ fontSize: 12, lineHeight: 1.6, color: f.kind === "FACT" ? "#b3aea4" : "#c29a6e" }}>
                <span className="mono-note">[{f.kind}]</span>{" "}
                {f.kind === "INTERPRETATION" ? <em>{f.statement}</em> : f.statement}
                <div style={{ marginTop: 3 }}>
                  {(f.evidence_refs?.length ?? 0) > 0 ? (
                    <EvidenceReferences refs={f.evidence_refs} traceRows={traceRows} />
                  ) : (
                    <span className="evidence-trace-unresolved">No call reference supplied.</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {inv.hypotheses.primary ? (
        <div style={{ marginTop: 16 }}>
          <span className="micro-label">POSITIONING HYPOTHESIS (TO TEST — NOT A PREDICTION)</span>
          <p style={{ color: "#e4dfd6", fontSize: 13, lineHeight: 1.7, margin: "8px 0 0" }}>
            {inv.hypotheses.primary.statement}
          </p>
          <div style={{ display: "grid", gap: 4, marginTop: 6 }}>
            <span className="mono-note">HYPOTHESIS EVIDENCE</span>
            {(inv.hypotheses.primary.evidence_refs?.length ?? 0) > 0 ? (
              <EvidenceReferences refs={inv.hypotheses.primary.evidence_refs} traceRows={traceRows} />
            ) : (
              <span className="evidence-trace-unresolved">No call reference supplied.</span>
            )}
          </div>
          {inv.hypotheses.alternatives.map((alt, i) => (
            <p key={i} style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.6, margin: "8px 0 0" }}>
              <span className="mono-note">ALTERNATIVE:</span> {alt.statement}
              {(alt.evidence_refs?.length ?? 0) > 0 && (
                <span> · <EvidenceReferences refs={alt.evidence_refs} traceRows={traceRows} /></span>
              )}
            </p>
          ))}
        </div>
      ) : (
        <p style={{ color: "#c29a6e", fontSize: 12, marginTop: 16 }}>
          No positioning hypothesis: the evidence did not support one. Nothing was invented.
        </p>
      )}

      <div style={{ marginTop: 16, display: "grid", gap: 10 }}>
        <div>
          <span className="micro-label">LIMITATIONS</span>
          <ul style={{ margin: "6px 0 0", paddingLeft: 18, color: "#8a847a", fontSize: 12, lineHeight: 1.7 }}>
            {inv.limitations.length > 0
              ? inv.limitations.map((limitation, i) => <li key={i}>{limitation}</li>)
              : <li>No limitations were recorded in this investigation.</li>}
          </ul>
        </div>
        <div>
          <span className="micro-label">OPEN QUESTIONS</span>
          <ul style={{ margin: "6px 0 0", paddingLeft: 18, color: "#8a847a", fontSize: 12, lineHeight: 1.7 }}>
            {inv.open_questions.length > 0
              ? inv.open_questions.map((question, i) => <li key={i}>{question}</li>)
              : <li>No open questions were recorded.</li>}
          </ul>
        </div>
      </div>

      <EvidenceTraceLog rows={traceRows} />
    </section>
  );
}
