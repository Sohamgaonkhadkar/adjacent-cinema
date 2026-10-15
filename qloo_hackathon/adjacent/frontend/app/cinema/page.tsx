"use client";

import { useState, useEffect, useRef } from "react";
import {
  createRun,
  createDemoRun,
  streamRun,
  getRun,
  type ProgrammeItemInput,
  type RunResponse,
  type SSEEvent,
} from "@/lib/api";
import type { AdjacentRunResult } from "@/types/adjacent";
import IntakeForm from "@/components/IntakeForm";

// ─── Editorial sample strip (illustrative photography, NOT a live analysis) ──

const FILMS = [
  { id: "substance", title: "The Substance", year: 2024, genre: "Horror · Satire", director: "Coralie Fargeat",
    img: "https://images.pexels.com/photos/21316136/pexels-photo-21316136.jpeg?auto=compress&cs=tinysrgb&fit=crop&w=900&h=1250",
    credit: "Fakhri Baghirov", creditUrl: "https://www.pexels.com/photo/woman-face-illuminated-by-red-light-21316136/",
    note: "Body horror meets an uncompromising auteur sensibility." },
  { id: "aftersun", title: "Aftersun", year: 2022, genre: "Drama · Memory", director: "Charlotte Wells",
    img: "https://images.pexels.com/photos/7991486/pexels-photo-7991486.jpeg?auto=compress&cs=tinysrgb&fit=crop&w=900&h=1250",
    credit: "Tima Miroshnichenko", creditUrl: "https://www.pexels.com/photo/an-empty-cinema-7991486/",
    note: "Intimate, emotionally precise independent cinema." },
  { id: "strangers", title: "All of Us Strangers", year: 2023, genre: "Drama · Romance", director: "Andrew Haigh",
    img: "https://images.pexels.com/photos/16158304/pexels-photo-16158304.jpeg?auto=compress&cs=tinysrgb&fit=crop&w=900&h=1250",
    credit: "Shuvo Haque", creditUrl: "https://www.pexels.com/photo/puddles-on-empty-street-in-city-16158304/",
    note: "Contemporary British authorship with a nocturnal pulse." },
  { id: "poor-things", title: "Poor Things", year: 2023, genre: "Fantasy · Romance", director: "Yorgos Lanthimos",
    img: "https://images.pexels.com/photos/35551877/pexels-photo-35551877.jpeg?auto=compress&cs=tinysrgb&fit=crop&w=900&h=1250",
    credit: "Poetarojo", creditUrl: "https://www.pexels.com/photo/classical-columns-in-museum-interior-setting-35551877/",
    note: "An art-forward world built with unusually bold form." },
  { id: "past-lives", title: "Past Lives", year: 2023, genre: "Drama · Romance", director: "Celine Song",
    img: "https://images.pexels.com/photos/15510029/pexels-photo-15510029.jpeg?auto=compress&cs=tinysrgb&fit=crop&w=900&h=1250",
    credit: "Alexander Nadrilyanski", creditUrl: "https://www.pexels.com/photo/string-lights-above-the-cobblestone-street-in-soho-london-england-15510029/",
    note: "A quiet, contemporary story with a strong afterlife beyond the screen." },
];

const NAV_ITEMS = [
  { id: "cinema", label: "Cinema" },
  { id: "programme", label: "Programme" },
  { id: "field", label: "Cultural field" },
  { id: "opportunity", label: "Opportunity" },
  { id: "test", label: "Test" },
];

// ─── Small display helpers ────────────────────────────────────────────────

function domainLabel(domain: string | null | undefined): string {
  if (!domain) return "unknown domain";
  return domain.replace("urn:entity:", "").replace(/_/g, " ");
}

function affinityPct(value: number | null | undefined): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value * 100)));
}

// ─── Main App ───────────────────────────────────────────────────────────────

export default function Home() {
  const [activeChapter, setActiveChapter] = useState("cinema");
  const [selectedFilm, setSelectedFilm] = useState(FILMS[0]);
  const [menuOpen, setMenuOpen] = useState(false);

  // Analysis state
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [analysing, setAnalysing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [request, setRequest] = useState<{ city: string; venue: string; programme: ProgrammeItemInput[] } | null>(null);
  const [requestMode, setRequestMode] = useState<"live" | "fixture" | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  // Intersection observer for active chapter
  useEffect(() => {
    const sections = document.querySelectorAll<HTMLElement>("[data-chapter]");
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActiveChapter((visible.target as HTMLElement).dataset.chapter ?? "cinema");
      },
      { threshold: [0.18, 0.36], rootMargin: "-8% 0px -12% 0px" }
    );
    sections.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, []);

  // Cleanup SSE on unmount
  useEffect(() => { return () => cleanupRef.current?.(); }, []);

  // ── Typed views of the current result (no `any`: this is the API contract) ──
  const result: AdjacentRunResult | null = run?.result ?? null;
  const dataStatus = result?.data_status ?? null;
  const programme = result?.programme ?? null;
  const tasteTags = result?.taste_dna?.tags ?? [];
  const ranked = result?.cohorts?.ranked ?? [];
  const rejected = result?.cohorts?.rejected ?? [];
  const geography = result?.geography ?? null;
  const geoCells = geography ? (geography.highest_affinity_cells ?? geography.cells ?? []) : [];
  const bet = result?.programme_bet ?? null;
  const testCard = result?.test_card ?? null;
  const evidence = result?.evidence ?? null;
  const progItems = programme?.items ?? [];

  // Map active chapter to nav id
  const activeNavId = activeChapter === "where" || activeChapter === "bet"
    ? "opportunity"
    : activeChapter;

  const traceEvents = events.filter((e) => e.event === "trace");
  const insufficient = run?.status === "insufficient" || run?.stop_reason === "insufficiency";
  const failed = run?.status === "failed";

  function startStream(id: string) {
    const cleanup = streamRun(
      id,
      (event) => {
        setEvents((prev) => [...prev, event]);
        if (event.event === "done" || event.event === "insufficiency") {
          cleanupRef.current?.();
          getRun(id)
            .then((finalRun) => { setRun(finalRun); setAnalysing(false); })
            .catch(() => { setError("Could not load the completed analysis"); setAnalysing(false); });
        }
        if (event.event === "error") {
          cleanupRef.current?.();
          setError(String(event.data?.message || "Analysis failed"));
          getRun(id).then(setRun).catch(() => undefined);
          setAnalysing(false);
        }
      },
      (err) => { setError(err.message); setAnalysing(false); }
    );
    cleanupRef.current = cleanup;
  }

  // The live path: exactly the values entered in the intake form are submitted.
  async function handleAnalyse(city: string, venue: string, programmeItems: ProgrammeItemInput[]) {
    setError(null);
    setAnalysing(true);
    setRun(null);
    setEvents([]);
    setRequest({ city, venue, programme: programmeItems });
    setRequestMode("live");

    try {
      const response = await createRun({ city, venue_name: venue, programme: programmeItems });
      setRunId(response.run_id);
      setRun(response);
      document.getElementById("field")?.scrollIntoView({ behavior: "smooth", block: "start" });
      startStream(response.run_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
      setAnalysing(false);
    }
  }

  // The fixture path: an explicit, labelled offline demo — never a silent fallback.
  async function handleDemo() {
    setError(null);
    setAnalysing(true);
    setRun(null);
    setEvents([]);
    setRequest(null);
    setRequestMode("fixture");

    try {
      const response = await createDemoRun();
      setRunId(response.run_id);
      setRun(response);
      document.getElementById("field")?.scrollIntoView({ behavior: "smooth", block: "start" });
      startStream(response.run_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start the fixture demo");
      setAnalysing(false);
    }
  }

  function resetAnalysis() {
    cleanupRef.current?.();
    setRunId(null);
    setRun(null);
    setEvents([]);
    setError(null);
    setRequest(null);
    setRequestMode(null);
    setAnalysing(false);
    document.getElementById("programme")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const statusIsMeasured = dataStatus === "measured";
  const statusLabel = statusIsMeasured
    ? "MEASURED QLOO DATA"
    : dataStatus === "fixture"
      ? "FIXTURE DEMO — NOT LIVE QLOO DATA"
      : "SOURCE NOT REPORTED";

  return (
    <main style={{ overflow: "clip", background: "#090909" }}>
      {/* ─── Header ─────────────────────────────────────────────────── */}
      <header className="site-header">
        <a className="header-brand" href="#cinema" onClick={() => setMenuOpen(false)}>
          <span className="header-wordmark">ADJACENT</span>
          <span className="header-descriptor">CULTURAL INTELLIGENCE<br />FOR INDEPENDENT CINEMAS</span>
        </a>
        <button
          className="mobile-menu-toggle"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((o) => !o)}
        >
          <span style={{ display: "block", width: 18, height: 1.5, background: "#e7e1d7", marginBottom: 4, transition: "transform 0.2s", ...(menuOpen ? { transform: "rotate(45deg) translate(3px, 3px)" } : {}) }} />
          <span style={{ display: "block", width: 18, height: 1.5, background: "#e7e1d7", marginBottom: 4, ...(menuOpen ? { opacity: 0 } : {}) }} />
          <span style={{ display: "block", width: 18, height: 1.5, background: "#e7e1d7", transition: "transform 0.2s", ...(menuOpen ? { transform: "rotate(-45deg) translate(3px, -3px)" } : {}) }} />
        </button>
          <nav className={`main-nav${menuOpen ? " is-open" : ""}`} aria-label="Story chapters">
            <a href="/" style={{ color: "var(--amber)" }}>
              <span className="nav-index">✦</span>
              Home
            </a>
            <a href="/creator" style={{ color: "var(--amber)" }}>
              <span className="nav-index">✦</span>
              Creator Mode
            </a>
          {NAV_ITEMS.map((item, i) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className={activeNavId === item.id ? "is-current" : ""}
              onClick={() => setMenuOpen(false)}
            >
              <span className="nav-index">0{i + 1}</span>
              {item.label}
            </a>
          ))}
        </nav>
      </header>

      {/* ─── 01 CINEMA / Hero ───────────────────────────────────────── */}
      <section id="cinema" className="hero-section" data-chapter="cinema">
        <div className="hero-image-wrap" aria-hidden="true">
          <img
            className="hero-image"
            src="https://images.pexels.com/photos/15510029/pexels-photo-15510029.jpeg?auto=compress&cs=tinysrgb&fit=crop&w=2200&h=1450"
            alt=""
            fetchPriority="high"
          />
        </div>
        <div className="hero-shade" aria-hidden="true" />
        <div className="hero-content">
          <p className="eyebrow hero-eyebrow"><span>01</span> CINEMA / A CULTURAL FIELD NOTE</p>
          <h1 className="hero-title">
            Find the audience<br /><em>you haven&rsquo;t met yet.</em>
          </h1>
          <p className="hero-deck">
            Discover cultural territory adjacent to the films you already programme.
          </p>
          <a className="text-link" href="#programme">
            <span>Enter your programme</span>
            <span className="link-arrow" aria-hidden="true">&rarr;</span>
          </a>
        </div>
        <div className="hero-footer">
          <div>
            <span className="micro-label" style={{ fontSize: 8 }}>{request ? "ANALYSIS RUNNING FOR" : "BUILT FOR"}</span>
            <strong>{request ? request.venue : "Your cinema"}</strong>
            <span style={{ color: "#bcb6aa", fontSize: 9, letterSpacing: "0.11em", textTransform: "uppercase" }}>
              {request ? request.city : "Any city / any programme"}
            </span>
          </div>
          <div className="hero-foot-note">
            <span className="micro-label" style={{ fontSize: 8 }}>A DIFFERENT KIND OF PROGRAMME INTELLIGENCE</span>
            <span style={{ color: "#bcb6aa", fontSize: 9 }}>Films in / cultural connections out</span>
          </div>
        </div>
      </section>

      {/* ─── 02 PROGRAMME ───────────────────────────────────────────── */}
      <section id="programme" className="programme-section" data-chapter="programme">
        <div className="section-shell">
          <div className="programme-head">
            <div>
              <p className="eyebrow"><span>02</span> THE STARTING POINT</p>
              <h2>What you already<br /><em>programme.</em></h2>
            </div>
            <div className="programme-intro">
              <p>Before looking outward, read the shape of the programme already in the room.</p>
              <span className="mono-note">EDITORIAL SAMPLE / ILLUSTRATIVE — NOT AN ANALYSIS</span>
            </div>
          </div>

          <div className="filmstrip" aria-label="Illustrative programme sample">
            {FILMS.map((film, index) => (
              <article key={film.id} className={`film-item${selectedFilm.id === film.id ? " is-selected" : ""}`}>
                <button
                  className="film-image-button"
                  type="button"
                  onClick={() => setSelectedFilm(film)}
                  aria-pressed={selectedFilm.id === film.id}
                >
                  <img src={film.img} alt={`${film.title} editorial photography`} loading="lazy" />
                  <span className="film-image-shade" aria-hidden="true" />
                  <span className="film-number">0{index + 1}</span>
                  <span className="film-hover-meta">
                    <span>{film.director}</span>
                    <span>{film.genre}</span>
                  </span>
                </button>
                <div className="film-caption">
                  <div className="film-title-line">
                    <h3>{film.title}</h3>
                    <span>{film.year}</span>
                  </div>
                  <p>{film.genre}</p>
                  <a href={film.creditUrl} target="_blank" rel="noreferrer" className="film-credit">
                    PHOTO / {film.credit}
                  </a>
                </div>
              </article>
            ))}
          </div>

          <div className="programme-bottom">
            <div className="film-detail">
              <span className="micro-label">IN THE SAMPLE / {selectedFilm.year}</span>
              <span className="film-detail-name">{selectedFilm.title}</span>
              <span className="film-detail-note">{selectedFilm.note}</span>
            </div>
            <div className="strip-instruction">
              <span>CLICK TO EXPLORE</span>
              <span aria-hidden="true">&harr;</span>
            </div>
          </div>
          <p className="image-note">Editorial photography, not official film stills. Image credits link to their Pexels source. The strip above is an illustrative sample — the analysis below runs on what YOU enter.</p>

          {/* ─── The real intake ─────────────────────────────────────── */}
          <IntakeForm onSubmit={handleAnalyse} loading={analysing} />
        </div>
      </section>

      {/* ─── 03 CULTURAL FIELD ──────────────────────────────────────── */}
      <section id="field" className="field-section" data-chapter="field"
        style={{ padding: "clamp(120px, 14vh, 175px) 0 60px" }}
      >
        <div className="section-shell">
          <div style={{ display: "flex", alignItems: "end", justifyContent: "space-between", gap: 48, marginBottom: 23 }}>
            <div>
              <p className="eyebrow"><span>03</span> CULTURAL FIELD</p>
              <h2 style={{
                margin: "20px 0 0", color: "var(--paper)",
                fontFamily: "var(--display)", fontSize: "clamp(56px, 6.1vw, 94px)",
                fontWeight: 400, letterSpacing: "-0.045em", lineHeight: 0.88
              }} >
                A programme is<br />a <em style={{ color: "#bcb4a7" }}>cultural fingerprint.</em>
              </h2>
            </div>
            <p style={{ maxWidth: 310, margin: 0, color: "#a7a39b", fontSize: 14, lineHeight: 1.8 }}>
              Follow the relationships outward. The useful signal is not a movie to recommend; it is a cultural territory the cinema could choose to enter.
            </p>
          </div>

          {/* Analysis status / controls */}
          <div style={{ padding: "40px 0", borderTop: "1px solid var(--rule)", marginTop: 32 }}>
            <p className="eyebrow" style={{ marginBottom: 16 }}><span>&#9656;</span> LIVE ANALYSIS</p>

            {!run && !analysing && (
              <>
                <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.85, maxWidth: 560, marginBottom: 24 }}>
                  Enter your cinema and recent programme in <a href="#programme" style={{ color: "var(--amber)", borderBottom: "1px solid rgba(194,154,110,0.4)" }}>02 / Programme</a>.
                  The engine resolves each film, queries Qloo for cultural adjacency signals, and produces an
                  explainable Programme Bet with a measurable Test Card.
                </p>
                <button onClick={handleDemo} className="intake-sample-btn" style={{ marginRight: 12 }}>
                  View labelled fixture demo (offline)
                </button>
                <span className="mono-note">NO API KEY REQUIRED FOR THE FIXTURE DEMO — IT IS ALWAYS LABELLED, NEVER PRESENTED AS LIVE</span>
              </>
            )}

            {error && (
              <div style={{ padding: "12px 16px", background: "rgba(138,80,72,0.15)", border: "1px solid rgba(138,80,72,0.4)", borderRadius: 8, marginBottom: 16, color: "#e8c4b8", fontSize: 12, maxWidth: 720 }}>
                <strong style={{ display: "block", marginBottom: 4, fontFamily: "var(--mono)", fontSize: 9, letterSpacing: "0.1em" }}>ANALYSIS ERROR — YOUR ENTRIES ARE PRESERVED IN 02 / PROGRAMME</strong>
                {error}
              </div>
            )}

            {analysing && (
              <div>
                <p style={{ color: "#d8b48a", fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.12em", marginBottom: 8 }}>
                  ANALYSING{requestMode === "fixture" ? " FIXTURE DEMO" : ""}… {events.length > 0 ? `${events.length} EVENTS RECEIVED` : "CONNECTING"}
                </p>
                <div className="progress-rail">
                  {traceEvents.slice(-6).map((e, i) => (
                    <div className="progress-line" key={i}>
                      <span className="phase">{String(e.data?.phase ?? "…")}</span>
                      <span>{String(e.data?.message ?? "")}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {run && !analysing && (
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                <button onClick={resetAnalysis} className="intake-sample-btn">
                  Reset &amp; analyse another programme
                </button>
                {requestMode !== "fixture" && (
                  <button onClick={handleDemo} className="intake-sample-btn">
                    View labelled fixture demo (offline)
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Insufficiency — a finding, not an error */}
          {run && !analysing && insufficient && (
            <div className="insufficient-panel" style={{ marginTop: 32 }}>
              <h3>Insufficient cultural evidence</h3>
              <p>
                {run.stop_message || "Qloo does not return enough verified cultural signal for this programme to name an adjacent audience."}
              </p>
              <p style={{ marginTop: 14 }} className="mono-note">
                THIS IS THE PRODUCT WORKING — A REFUSAL IS AN HONEST RESULT, NOT A FAILURE.
              </p>
            </div>
          )}

          {/* Failure without a result */}
          {run && !analysing && failed && !result && (
            <div className="insufficient-panel" style={{ marginTop: 32, borderColor: "rgba(138,80,72,0.45)", background: "rgba(138,80,72,0.08)" }}>
              <h3 style={{ color: "#d4a89e" }}>The run could not complete</h3>
              <p>{run.error || run.stop_message || "Unknown failure."}</p>
            </div>
          )}

          {/* Results */}
          {result && (
            <div style={{ marginTop: 32 }}>
              {/* Data status */}
              <div style={{ marginBottom: 24, padding: "10px 14px", background: statusIsMeasured ? "rgba(62,122,76,0.12)" : "rgba(194,154,110,0.12)", border: `1px solid ${statusIsMeasured ? "rgba(62,122,76,0.3)" : "rgba(194,154,110,0.3)"}`, borderRadius: 6 }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 9, letterSpacing: "0.1em", textTransform: "uppercase", color: statusIsMeasured ? "#7aba8a" : "#c29a6e" }}>
                  {statusLabel}
                </span>
                {request && (
                  <span style={{ marginLeft: 16, color: "#908c84", fontSize: 11 }}>
                    {request.venue} · {request.city} · {request.programme.length} film(s) submitted
                  </span>
                )}
              </div>

              {/* Programme profile */}
              <div className="evidence-panel">
                <h3>Programme Profile</h3>
                <span className="mono-note" style={{ display: "block", marginBottom: 16 }}>
                  {programme?.resolved_count ?? 0}/{programme?.total_count ?? 0} FILMS RESOLVED AGAINST QLOO
                </span>
                <div style={{ display: "grid", gap: 6 }}>
                  {progItems.map((item, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, flexWrap: "wrap" }}>
                      <span style={{ color: item.resolved ? "#7aba8a" : "#c97a6a" }}>
                        {item.resolved ? "✓" : "✕"}
                      </span>
                      <span style={{ color: "#e9e3d8" }}>{item.title}</span>
                      {item.year != null && <span style={{ color: "#88837a" }}>({item.year})</span>}
                      {item.resolved && item.qloo_name && item.qloo_name !== item.title && (
                        <span style={{ color: "#88837a", fontSize: 10 }}>→ {item.qloo_name}</span>
                      )}
                      {!item.resolved && (
                        <span style={{ color: "#8a847a", fontSize: 10, fontFamily: "var(--mono)" }}>UNRESOLVED — EXCLUDED FROM EVIDENCE, NEVER GUESSED</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Taste DNA */}
              {tasteTags.length > 0 && (
                <div className="evidence-panel">
                  <h3>Taste DNA</h3>
                  <span className="mono-note" style={{ display: "block", marginBottom: 16 }}>
                    {result.taste_dna?.tag_count ?? tasteTags.length} TAGS · QLOO AFFINITY 0–1 · {statusIsMeasured ? "MEASURED" : "FIXTURE"}
                  </span>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
                    {tasteTags.slice(0, 16).map((tag, i) => (
                      <div key={tag.tag_id || i} style={{ padding: "10px 12px", background: "rgba(232,226,213,0.04)", border: "1px solid var(--rule)", borderRadius: 6 }}>
                        <div style={{ color: "#e7e1d7", fontSize: 12, fontWeight: 500 }}>{tag.name}</div>
                        <div style={{ color: "#88837a", fontSize: 10, marginTop: 4 }}>
                          Affinity: {typeof tag.affinity === "number" ? tag.affinity.toFixed(4) : "—"} · {tag.band || "—"}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Ranked cohorts — the cultural field, ranked */}
              {ranked.length > 0 && (
                <div className="evidence-panel">
                  <h3>Adjacent Cohorts, Ranked</h3>
                  <span className="mono-note" style={{ display: "block", marginBottom: 16 }}>
                    {ranked.length} RANKED · {rejected.length} REJECTED WITH REASONS · AFFINITY = QLOO CULTURAL SIMILARITY, NOT AUDIENCE SIZE
                  </span>
                  <div style={{ display: "grid", gap: 14 }}>
                    {ranked.map((cohort) => (
                      <div key={cohort.cohort_id} style={{ padding: "16px 18px", border: "1px solid var(--rule)", borderRadius: 7, background: "rgba(232,226,213,0.02)" }}>
                        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 10 }}>
                          <span style={{ fontFamily: "var(--display)", fontSize: 22, color: "#e9e3d8" }}>
                            <span style={{ color: "var(--amber)", fontFamily: "var(--mono)", fontSize: 10, marginRight: 10 }}>0{cohort.rank}</span>
                            {domainLabel(cohort.domain)}
                          </span>
                          <span className="mono-note">
                            {cohort.member_count} MEMBERS · MEAN AFFINITY {typeof cohort.score?.mean_affinity === "number" ? cohort.score.mean_affinity.toFixed(2) : "—"}
                            {" · "}{cohort.verdict ?? ""}
                          </span>
                        </div>
                        <div style={{ display: "grid", gap: 6 }}>
                          {cohort.members.slice(0, 5).map((m, mi) => (
                            <div className="bar-row" key={m.entity_id || mi} style={{ gridTemplateColumns: "minmax(140px, 1.2fr) 2fr auto" }}>
                              <span className="bar-label">{m.name}</span>
                              <div className="bar-track">
                                <div className="bar-fill adjacent" style={{ width: `${affinityPct(m.affinity)}%` }} />
                              </div>
                              <span className="bar-value">
                                {typeof m.affinity === "number" ? m.affinity.toFixed(2) : "—"}{m.band ? ` · ${m.band}` : ""}
                              </span>
                            </div>
                          ))}
                        </div>
                        {(cohort.excluded_members?.length ?? 0) > 0 && (
                          <details style={{ marginTop: 10 }}>
                            <summary className="mono-note" style={{ cursor: "pointer" }}>
                              {cohort.qualifying_count ?? cohort.members.length} OF {cohort.member_count} MEMBERS QUALIFY · {cohort.excluded_members?.length} CONSIDERED BUT EXCLUDED — AND WHY
                            </summary>
                            <div style={{ display: "grid", gap: 4, marginTop: 8 }}>
                              {cohort.excluded_members?.map((ex, ei) => (
                                <div key={ex.entity_id || ei} style={{ color: "#8a847a", fontSize: 11 }}>
                                  {ex.name ?? ex.entity_id} — {ex.reason_code}
                                  {typeof ex.affinity === "number" ? ` (affinity ${ex.affinity.toFixed(2)})` : ""}
                                </div>
                              ))}
                            </div>
                          </details>
                        )}
                      </div>
                    ))}
                  </div>
                  {rejected.length > 0 && (
                    <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--rule)" }}>
                      <span className="micro-label" style={{ marginBottom: 8 }}>REJECTED — AND WHY</span>
                      <div style={{ display: "grid", gap: 4 }}>
                        {rejected.map((r, ri) => (
                          <div key={r.cohort_id || ri} style={{ color: "#8a847a", fontSize: 11 }}>
                            {domainLabel(r.domain)} — {r.rejection_reason ?? "rejected"}{r.rejection_detail ? ` (${r.rejection_detail})` : ""}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Geography — with its limits stated */}
              {geography && (
                <div className="evidence-panel">
                  <h3>Where the affinity concentrates</h3>
                  <span className="mono-note" style={{ display: "block", marginBottom: 4 }}>
                    {geography.city_display || geography.city} · {geography.total_cells} HEATMAP CELLS · CALL {geography.call_id ?? "—"} · {geography.data_status === "measured" ? "MEASURED" : "FIXTURE"}
                  </span>
                  {!geography.sufficient && (
                    <p style={{ color: "#c29a6e", fontSize: 11, margin: "8px 0 0", lineHeight: 1.7 }}>
                      {geography.note || "Too few cells for a geographic claim — treat as directional only."}
                    </p>
                  )}
                  <div className="geo-list">
                    {geoCells.slice(0, 5).map((cell, ci) => (
                      <div className="geo-row" key={ci}>
                        <span className="geo-rank">#{cell.affinity_rank ?? ci + 1}</span>
                        <span className="geo-name">{cell.geohash ?? "cell"}</span>
                        <span className="geo-coords">{cell.latitude.toFixed(3)}, {cell.longitude.toFixed(3)}</span>
                        <span className="geo-affinity">{cell.affinity.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                  <p className="mono-note" style={{ marginTop: 12, lineHeight: 1.8 }}>
                    GEOHASH CELL CENTROIDS FROM A QLOO HEATMAP — A CULTURAL-AFFINITY CONCENTRATION SIGNAL, NOT A POPULATION, CATCHMENT OR DEMAND MODEL.
                  </p>
                </div>
              )}

              {/* Programme Bet */}
              {bet && (
                <div style={{ marginBottom: 32, padding: 24, background: "rgba(194,154,110,0.06)", border: "1px solid rgba(194,154,110,0.25)", borderRadius: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, gap: 12, flexWrap: "wrap" }}>
                    <span className="eyebrow" style={{ color: "var(--amber)" }}>&#127919; PROGRAMME BET</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 8, letterSpacing: "0.1em", textTransform: "uppercase", color: bet.data_status === "measured" ? "#7aba8a" : "#c29a6e", padding: "3px 8px", background: "rgba(194,154,110,0.1)", borderRadius: 4 }}>
                      {bet.data_status === "measured" ? "MEASURED QLOO" : `DATA STATUS: ${String(bet.data_status ?? "unknown").toUpperCase()}`}
                    </span>
                  </div>
                  <h3 style={{ margin: "0 0 8px", fontFamily: "var(--display)", fontSize: 32, fontWeight: 400, color: "#e9e3d8" }}>
                    {bet.primary?.cohort_name}
                  </h3>
                  <p style={{ color: "#a7a39b", fontSize: 12, lineHeight: 1.7, marginBottom: 16 }}>
                    {domainLabel(bet.primary?.domain)} · {bet.primary?.member_count} entities
                    {typeof bet.primary?.mean_affinity === "number" ? ` · mean affinity ${bet.primary.mean_affinity.toFixed(2)}` : ""}
                    {bet.primary?.call_id ? ` · call ${bet.primary.call_id}` : ""}
                    {bet.primary?.cohort_id ? ` · built from ranked cohort ${bet.primary.cohort_id} above` : ""}
                  </p>
                  {bet.two_sided_signals && (
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 16 }}>
                      <div style={{ padding: "10px 12px", border: "1px solid var(--rule)", borderRadius: 6 }}>
                        <span className="micro-label">PROGRAMME ADJACENCY</span>
                        <span style={{ display: "block", color: "#e9e3d8", fontSize: 14, marginTop: 4 }}>
                          {typeof bet.two_sided_signals.programme_adjacency === "number" ? bet.two_sided_signals.programme_adjacency.toFixed(2) : "—"}
                          {bet.two_sided_signals.adjacency_band ? ` · ${bet.two_sided_signals.adjacency_band}` : ""}
                        </span>
                      </div>
                      <div style={{ padding: "10px 12px", border: "1px solid var(--rule)", borderRadius: 6 }}>
                        <span className="micro-label">COHORT BREADTH</span>
                        <span style={{ display: "block", color: "#e9e3d8", fontSize: 14, marginTop: 4 }}>
                          {typeof bet.two_sided_signals.cohort_breadth === "number" ? bet.two_sided_signals.cohort_breadth.toFixed(2) : "—"}
                          {bet.two_sided_signals.breadth_band ? ` · ${bet.two_sided_signals.breadth_band}` : ""}
                        </span>
                      </div>
                    </div>
                  )}
                  <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, marginBottom: 12 }}>
                    {bet.why}
                  </p>
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
                  {bet.falsification_condition && (
                    <div style={{ marginTop: 16, padding: "12px 14px", background: "rgba(138,80,72,0.1)", border: "1px solid rgba(138,80,72,0.25)", borderRadius: 6 }}>
                      <span className="micro-label" style={{ color: "#c97a6a", marginBottom: 6, display: "block" }}>&#9888; FALSIFICATION CONDITION</span>
                      <p style={{ color: "#d4a89e", fontSize: 12, lineHeight: 1.7, margin: 0 }}>
                        {bet.falsification_condition}
                      </p>
                    </div>
                  )}
                  {bet.runner_up && (
                    <p className="mono-note" style={{ marginTop: 12, lineHeight: 1.8 }}>
                      RUNNER-UP: {bet.runner_up.cohort_name ?? domainLabel(bet.runner_up.domain)}
                      {typeof bet.runner_up.mean_affinity === "number" ? ` · AFFINITY ${bet.runner_up.mean_affinity.toFixed(2)}` : ""}
                    </p>
                  )}
                </div>
              )}

              {/* Evidence / provenance */}
              {evidence && (
                <div style={{ padding: 20, border: "1px solid var(--rule)", borderRadius: 8 }}>
                  <span className="micro-label" style={{ marginBottom: 14, display: "block" }}>PROVENANCE / EVIDENCE</span>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 16 }}>
                    {([
                      ["Qloo calls", evidence.qloo_calls],
                      ["Trace rows", evidence.trace_rows],
                      ["Stop reason", evidence.stop_reason],
                      ["Run status", run?.status],
                      ["Run ID", runId],
                    ] as [string, unknown][]).map(([label, value]) => (
                      <div key={label}>
                        <span className="micro-label">{label}</span>
                        <span style={{ display: "block", color: "#e9e3d8", fontSize: 13, marginTop: 4, overflowWrap: "anywhere" }}>{String(value ?? "—")}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {/* ─── 04 OPPORTUNITY ─────────────────────────────────────────── */}
      <section id="opportunity" className="gap-section" data-chapter="opportunity">
        <div className="section-shell">
          <div style={{ display: "flex", alignItems: "end", justifyContent: "space-between", gap: 48, marginBottom: 48 }}>
            <div>
              <p className="eyebrow"><span>04</span> THE OPPORTUNITY / A PROGRAMME GAP</p>
              <h2 style={{
                margin: "28px 0 0", color: "var(--paper)",
                fontFamily: "var(--display)", fontSize: "clamp(56px, 6.1vw, 94px)",
                fontWeight: 400, letterSpacing: "-0.045em", lineHeight: 0.88,
              }} >
                The cultural territory<br />you are <em style={{ color: "#bcb4a7" }}>not yet exploring.</em>
              </h2>
            </div>
            <p style={{ maxWidth: 310, margin: 0, color: "#a7a39b", fontSize: 14, lineHeight: 1.8 }}>
              An adjacent direction should feel close enough to belong, and new enough to create a reason to visit.
            </p>
          </div>

          {!result && (
            <div className="insufficient-panel">
              <h3>No numbers before evidence</h3>
              <p>
                Adjacent never displays territory scores it has not measured. Run an analysis on your
                programme in <a href="#programme" style={{ color: "var(--amber)" }}>02 / Programme</a> —
                this panel will then show your programme&rsquo;s expressed taste profile beside the
                highest-ranked adjacent cohorts, each value taken directly from the Qloo response.
              </p>
            </div>
          )}

          {result && insufficient && (
            <div className="insufficient-panel">
              <h3>Insufficient evidence for a territory claim</h3>
              <p>
                {run?.stop_message || "Qloo did not return enough verified cultural signal for this programme."}
              </p>
            </div>
          )}

          {result && !insufficient && (
            <>
              <div className="opportunity-grid">
                {/* Expressed — from measured taste tags */}
                <div>
                  <span className="micro-label" style={{ marginBottom: 12, display: "block" }}>01 / EXPRESSED · YOUR TASTE PROFILE</span>
                  <h3 style={{ fontFamily: "var(--display)", fontSize: "clamp(28px, 3vw, 42px)", fontWeight: 400, margin: "0 0 24px", lineHeight: 1 }}>
                    What your programme<br /><em style={{ color: "#bcb4a7" }}>already expresses.</em>
                  </h3>
                  {tasteTags.length > 0 ? tasteTags.slice(0, 5).map((tag, i) => (
                    <div className="bar-row" key={tag.tag_id || i}>
                      <span className="bar-label">{tag.name}</span>
                      <div className="bar-track">
                        <div className="bar-fill" style={{ width: `${affinityPct(tag.affinity)}%` }} />
                      </div>
                      <span className="bar-value">
                        {typeof tag.affinity === "number" ? tag.affinity.toFixed(2) : "—"}{tag.band ? ` · ${tag.band}` : ""}
                      </span>
                    </div>
                  )) : (
                    <p style={{ color: "#8a847a", fontSize: 12 }}>No taste tags returned for this programme.</p>
                  )}
                </div>

                {/* Bridge arrow */}
                <div className="opportunity-bridge">
                  <span className="mono-note" style={{ color: "var(--amber)" }}>EXTEND</span>
                  <span style={{ fontSize: 24 }}>&rarr;</span>
                </div>

                {/* Adjacent — from ranked cohorts */}
                <div>
                  <span className="micro-label" style={{ marginBottom: 12, display: "block" }}>02 / ADJACENT · RANKED COHORTS</span>
                  <h3 style={{ fontFamily: "var(--display)", fontSize: "clamp(28px, 3vw, 42px)", fontWeight: 400, margin: "0 0 24px", lineHeight: 1 }}>
                    Adjacent<br /><em style={{ color: "#bcb4a7" }}>territory.</em>
                  </h3>
                  {ranked.length > 0 ? ranked.slice(0, 5).map((cohort) => (
                    <div className="bar-row" key={cohort.cohort_id}>
                      <span className="bar-label" title={cohort.domain}>{domainLabel(cohort.domain)}</span>
                      <div className="bar-track">
                        <div className="bar-fill adjacent" style={{ width: `${affinityPct(cohort.score?.mean_affinity)}%` }} />
                      </div>
                      <span className="bar-value">
                        {typeof cohort.score?.mean_affinity === "number" ? cohort.score.mean_affinity.toFixed(2) : "—"} · {cohort.member_count} ENT
                      </span>
                    </div>
                  )) : (
                    <p style={{ color: "#8a847a", fontSize: 12 }}>No adjacent cohorts cleared the evidence gate.</p>
                  )}
                </div>
              </div>

              <div style={{ textAlign: "center", padding: "48px 0 0", borderTop: "1px solid var(--rule)", marginTop: 48 }}>
                <span className="micro-label" style={{ marginBottom: 12, display: "block" }}>HOW TO READ THESE BARS · {statusIsMeasured ? "MEASURED QLOO DATA" : "FIXTURE DEMO DATA"}</span>
                <p style={{ fontFamily: "var(--display)", fontSize: "clamp(20px, 2.3vw, 30px)", fontWeight: 400, margin: "0 0 14px", lineHeight: 1.35 }}>
                  Affinity is a Qloo cultural-similarity score (0–1).<br />
                  <em style={{ color: "#bcb4a7" }}>It is not an audience size, an attendance forecast, or a conversion probability.</em>
                </p>
                <p className="mono-note" style={{ maxWidth: 640, margin: "0 auto", lineHeight: 1.9 }}>
                  LEFT: HIGHEST-AFFINITY TASTE TAGS OF YOUR PROGRAMME. RIGHT: HIGHEST-RANKED ADJACENT COHORTS BY MEAN MEMBER AFFINITY. EVERY VALUE COMES FROM THE QLOO RESPONSES OF THIS RUN — SEE PROVENANCE IN 03.
                </p>
              </div>
            </>
          )}
        </div>
      </section>

      {/* ─── 05 TEST ────────────────────────────────────────────────── */}
      <section id="test" className="test-section" data-chapter="test">
        <div className="test-shell">
          <div style={{ display: "flex", alignItems: "end", justifyContent: "space-between", gap: 48, marginBottom: 48 }}>
            <div>
              <p className="eyebrow"><span>05</span> TAKE IT INTO THE WORLD</p>
              <h2 style={{
                margin: "20px 0 0", color: "var(--paper)",
                fontFamily: "var(--display)", fontSize: "clamp(56px, 6.1vw, 94px)",
                fontWeight: 400, letterSpacing: "-0.045em", lineHeight: 0.88,
              }} >
                Programme<br /><em style={{ color: "#bcb4a7" }}>experiment.</em>
              </h2>
            </div>
            <p style={{ maxWidth: 310, margin: 0, color: "#a7a39b", fontSize: 14, lineHeight: 1.8 }}>
              A bounded test of a cultural adjacency. Not a new identity for the cinema.
            </p>
          </div>

          <article style={{ padding: 32, border: "1px solid var(--rule)", borderRadius: 8, background: "rgba(232,226,213,0.02)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24, paddingBottom: 16, borderBottom: "1px solid var(--rule)", gap: 12, flexWrap: "wrap" }}>
              <span className="micro-label">PROGRAMME EXPERIMENT · TEST CARD</span>
              <span className="mono-note">
                {testCard
                  ? `DATA STATUS: ${String(testCard.data_status ?? "unknown").toUpperCase()}`
                  : "RUN AN ANALYSIS ABOVE TO POPULATE"}
              </span>
            </div>

            {testCard ? (
              <>
                <div style={{ marginBottom: 24 }}>
                  <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>THE BET</span>
                  <h3 style={{ fontFamily: "var(--display)", fontSize: 32, fontWeight: 400, margin: 0, color: "#e9e3d8" }}>
                    {testCard.title}
                  </h3>
                </div>

                <div style={{ display: "grid", gap: 22 }}>
                  {testCard.programme_context && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>PROGRAMME CONTEXT</span>
                      <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, margin: 0 }}>{testCard.programme_context}</p>
                    </div>
                  )}
                  {testCard.audience_hypothesis && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>AUDIENCE HYPOTHESIS</span>
                      <p style={{ color: "#b3aea4", fontSize: 14, lineHeight: 1.8, margin: 0 }}>
                        &ldquo;{testCard.audience_hypothesis}&rdquo;
                      </p>
                    </div>
                  )}
                  {testCard.cultural_bridge && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>CULTURAL BRIDGE</span>
                      <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, margin: 0 }}>{testCard.cultural_bridge}</p>
                    </div>
                  )}
                  {testCard.geographic_signal && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>GEOGRAPHIC SIGNAL</span>
                      <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, margin: 0 }}>{testCard.geographic_signal}</p>
                    </div>
                  )}
                  {testCard.programming_direction && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>PROGRAMMING DIRECTION</span>
                      <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, margin: 0 }}>{testCard.programming_direction}</p>
                    </div>
                  )}
                  {testCard.primary_evidence && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>PRIMARY EVIDENCE</span>
                      <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, margin: 0 }}>{testCard.primary_evidence}</p>
                    </div>
                  )}
                  {testCard.runner_up && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>RUNNER-UP DIRECTION</span>
                      <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, margin: 0 }}>{testCard.runner_up}</p>
                    </div>
                  )}
                  {testCard.falsification_condition && (
                    <div style={{ padding: "12px 14px", background: "rgba(138,80,72,0.1)", border: "1px solid rgba(138,80,72,0.25)", borderRadius: 6 }}>
                      <span className="micro-label" style={{ color: "#c97a6a", marginBottom: 6, display: "block" }}>&#9888; FALSIFICATION CONDITION</span>
                      <p style={{ color: "#d4a89e", fontSize: 12, lineHeight: 1.7, margin: 0 }}>
                        {testCard.falsification_condition}
                      </p>
                    </div>
                  )}
                  {testCard.success_criteria && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>OBSERVABLE SUCCESS CRITERIA</span>
                      <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, margin: 0 }}>{testCard.success_criteria}</p>
                    </div>
                  )}
                  {testCard.observation_window && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>OBSERVATION WINDOW</span>
                      <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, margin: 0 }}>{testCard.observation_window}</p>
                    </div>
                  )}
                  {testCard.provenance && (
                    <div>
                      <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>PROVENANCE</span>
                      <div style={{ display: "grid", gap: 4 }}>
                        {Object.entries(testCard.provenance).map(([k, v]) => (
                          <div key={k} className="mono-note" style={{ lineHeight: 1.8 }}>
                            {k.toUpperCase()}: {String(v ?? "—")}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div style={{ textAlign: "center", padding: "48px 0", color: "#6b6964" }}>
                <p style={{ fontFamily: "var(--display)", fontSize: 24, margin: "0 0 12px", color: "#88837a" }}>
                  Run a cultural analysis above to populate this test card.
                </p>
                <p style={{ fontSize: 12, lineHeight: 1.7 }}>
                  The engine will resolve your programme, query Qloo, and produce<br />
                  an explainable Programme Bet with a measurable Test Card.
                </p>
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--rule)", gap: 12, flexWrap: "wrap" }}>
              <span className="mono-note">NO ATTENDANCE TARGETS / NO CONVERSION CLAIMS</span>
              <span className="mono-note">REVIEW AFTER THE EXPERIMENT</span>
            </div>
          </article>

          <footer style={{ display: "flex", justifyContent: "space-between", marginTop: 48, paddingTop: 24, borderTop: "1px solid var(--rule)", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: 8, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6b6964" }}>
              ADJACENT / CULTURAL INTELLIGENCE FOR INDEPENDENT CINEMAS
            </span>
            <span style={{ fontFamily: "var(--mono)", fontSize: 8, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6b6964" }}>
              HERE IS THE DECISION. NOW GO TEST IT.
            </span>
          </footer>
        </div>
      </section>
    </main>
  );
}
