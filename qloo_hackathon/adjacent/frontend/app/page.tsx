"use client";

import { useState, useEffect, useRef } from "react";
import {
  createRun,
  streamRun,
  getRun,
  DEMO_PROGRAMME,
  type ProgrammeItemInput,
  type RunResponse,
  type SSEEvent,
} from "@/lib/api";

// ─── Film data (illustrative programme sample) ──────────────────────────

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

// ─── Main App ───────────────────────────────────────────────────────────

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

  const result = run?.result as any;
  const programme = result?.programme as any;
  const tasteDna = result?.taste_dna as any;
  const tasteDnaTags = (tasteDna?.tags ?? []) as any[];
  const bet = result?.programme_bet as any;
  const betPrimary = bet?.primary as any;
  const testCard = result?.test_card as any;
  const evidence = result?.evidence as any;
  const dataStatus = String(result?.data_status ?? "unknown");
  const progItems = (programme?.items ?? []) as any[];
    // Map active chapter to nav id
  const activeNavId = activeChapter === "where" || activeChapter === "bet"
    ? "opportunity"
    : activeChapter;

  async function handleAnalyse() {
    setError(null);
    setAnalysing(true);
    setRun(null);
    setEvents([]);

    try {
      const programme: ProgrammeItemInput[] = FILMS.map(f => ({ title: f.title, year: f.year }));
      const response = await createRun({
        city: "London, UK",
        venue_name: "Prince Charles Cinema",
        programme,
      });
      setRunId(response.run_id);

      const cleanup = streamRun(
        response.run_id,
        (event) => {
          setEvents((prev) => [...prev, event]);
          if (event.event === "done" || event.event === "insufficiency") {
            cleanupRef.current?.();
            getRun(response.run_id)
              .then((finalRun) => { setRun(finalRun); setAnalysing(false); })
              .catch(() => { setError("Could not load completed analysis"); setAnalysing(false); });
          }
          if (event.event === "error") {
            cleanupRef.current?.();
            setError(String(event.data?.message || "Analysis failed"));
            setAnalysing(false);
          }
        },
        (err) => { setError(err.message); setAnalysing(false); }
      );
      cleanupRef.current = cleanup;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
      setAnalysing(false);
    }
  }

  function resetAnalysis() {
    cleanupRef.current?.();
    setRunId(null);
    setRun(null);
    setEvents([]);
    setError(null);
    setAnalysing(false);
  }

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
            <span>Enter cinema</span>
            <span className="link-arrow" aria-hidden="true">&rarr;</span>
          </a>
        </div>
        <div className="hero-footer">
          <div>
            <span className="micro-label" style={{ fontSize: 8 }}>A DEMO FOR</span>
            <strong>Prince Charles Cinema</strong>
            <span style={{ color: "#bcb6aa", fontSize: 9, letterSpacing: "0.11em", textTransform: "uppercase" }}>
              LONDON / UK
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
              <span className="mono-note">RECENT SCREENINGS / ILLUSTRATIVE SAMPLE</span>
            </div>
          </div>

          <div className="filmstrip" aria-label="Recent programme">
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
          <p className="image-note">Editorial photography, not official film stills. Image credits link to their Pexels source.</p>
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
              }}>
                A programme is<br />a <em style={{ color: "#bcb4a7" }}>cultural fingerprint.</em>
              </h2>
            </div>
            <p style={{ maxWidth: 310, margin: 0, color: "#a7a39b", fontSize: 14, lineHeight: 1.8 }}>
              Follow the relationships outward. The useful signal is not a movie to recommend; it is a cultural territory the cinema could choose to enter.
            </p>
          </div>

          {/* Analysis trigger */}
          <div style={{ padding: "48px 0", borderTop: "1px solid var(--rule)", marginTop: 32 }}>
            <p className="eyebrow" style={{ marginBottom: 16 }}><span>&#9656;</span> LIVE ANALYSIS</p>
            <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.85, maxWidth: 520, marginBottom: 24 }}>
              Run a real Qloo cultural intelligence analysis on this programme.
              The engine resolves each film, queries Qloo for cultural adjacency signals,
              and produces an explainable Programme Bet.
            </p>

            {error && (
              <div style={{ padding: "12px 16px", background: "rgba(138,80,72,0.15)", border: "1px solid rgba(138,80,72,0.4)", borderRadius: 8, marginBottom: 16, color: "#e8c4b8", fontSize: 12 }}>
                {error}
              </div>
            )}

            {!run && (
              <button
                onClick={handleAnalyse}
                disabled={analysing}
                style={{
                  padding: "12px 28px", background: "var(--amber)", color: "#111",
                  fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.12em",
                  textTransform: "uppercase", borderRadius: 4,
                  opacity: analysing ? 0.6 : 1,
                }}
              >
                {analysing ? `Analysing${events.length > 0 ? ` (${events.length} events)` : "…"}` : "Analyse programme with Qloo"}
              </button>
            )}

            {run && (
              <button
                onClick={resetAnalysis}
                style={{
                  padding: "10px 20px", background: "transparent",
                  color: "var(--muted)", border: "1px solid var(--rule)",
                  fontFamily: "var(--mono)", fontSize: 9, letterSpacing: "0.1em",
                  textTransform: "uppercase", borderRadius: 4,
                }}
              >
                Reset &amp; re-run
              </button>
            )}
          </div>

          {/* Results */}
          {run?.result && (
            <div style={{ marginTop: 32 }}>
              {/* Data status */}
              <div style={{ marginBottom: 24, padding: "10px 14px", background: dataStatus === "measured" ? "rgba(62,122,76,0.12)" : "rgba(194,154,110,0.12)", border: `1px solid ${dataStatus === "measured" ? "rgba(62,122,76,0.3)" : "rgba(194,154,110,0.3)"}`, borderRadius: 6 }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 9, letterSpacing: "0.1em", textTransform: "uppercase", color: dataStatus === "measured" ? "#7aba8a" : "#c29a6e" }}>
                  {dataStatus === "measured" ? "MEASURED QLOO DATA" : dataStatus === "fixture" ? "FIXTURE DEMO (NOT LIVE)" : "SOURCE NOT REPORTED"}
                </span>
              </div>

              {/* Programme profile */}
              <div style={{ marginBottom: 32, padding: 24, border: "1px solid var(--rule)", borderRadius: 8 }}>
                <h3 style={{ margin: "0 0 16px", fontFamily: "var(--display)", fontSize: 28, fontWeight: 400 }}>
                  Programme Profile
                </h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 16 }}>
                  <div>
                    <span className="micro-label">VENUE</span>
                    <span style={{ color: "#e9e3d8", fontSize: 13 }}>{run.venue_name || "—"}</span>
                  </div>
                  <div>
                    <span className="micro-label">CITY</span>
                    <span style={{ color: "#e9e3d8", fontSize: 13 }}>{run.city}</span>
                  </div>
                  <div>
                    <span className="micro-label">FILMS</span>
                    <span style={{ color: "#e9e3d8", fontSize: 13 }}>{Number(programme?.total_count ?? 0)}</span>
                  </div>
                  <div>
                    <span className="micro-label">RESOLVED</span>
                    <span style={{ color: "#7aba8a", fontSize: 13 }}>
                      {Number(programme?.resolved_count ?? 0)}/{Number(programme?.total_count ?? 0)}
                    </span>
                  </div>
                </div>
                <div style={{ display: "grid", gap: 6 }}>
                  {progItems?.map((item: Record<string, unknown>, i: number) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                      <span style={{ color: item.resolved ? "#7aba8a" : "#c97a6a" }}>
                        {item.resolved ? "✓" : "✕"}
                      </span>
                      <span style={{ color: "#e9e3d8" }}>{String(item.title)}</span>
                      {item.year != null && <span style={{ color: "#88837a" }}>({String(item.year)})</span>}
                    </div>
                  ))}
                </div>
              </div>

              {/* Taste DNA */}
              {tasteDnaTags.length > 0 && (
                <div style={{ marginBottom: 32, padding: 24, border: "1px solid var(--rule)", borderRadius: 8 }}>
                  <h3 style={{ margin: "0 0 4px", fontFamily: "var(--display)", fontSize: 28, fontWeight: 400 }}>
                    Taste DNA
                  </h3>
                  <span className="mono-note" style={{ display: "block", marginBottom: 16 }}>
                    {Number(tasteDna?.tag_count ?? 0)} TAGS / {dataStatus === "measured" ? "MEASURED" : "FIXTURE"}
                  </span>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
                    {tasteDnaTags.slice(0, 16).map((tag: Record<string, unknown>) => (
                      <div key={String(tag.tag_id)} style={{ padding: "10px 12px", background: "rgba(232,226,213,0.04)", border: "1px solid var(--rule)", borderRadius: 6 }}>
                        <div style={{ color: "#e7e1d7", fontSize: 12, fontWeight: 500 }}>{String(tag.name)}</div>
                        <div style={{ color: "#88837a", fontSize: 10, marginTop: 4 }}>
                          Affinity: {typeof tag.affinity === "number" ? tag.affinity.toFixed(4) : "—"} · {String(tag.band || "—")}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Programme Bet */}
              {bet && (
                <div style={{ marginBottom: 32, padding: 24, background: "rgba(194,154,110,0.06)", border: "1px solid rgba(194,154,110,0.25)", borderRadius: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                    <span className="eyebrow" style={{ color: "var(--amber)" }}>&#127919; PROGRAMME BET</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 8, letterSpacing: "0.1em", textTransform: "uppercase", color: bet.data_status === "measured" ? "#7aba8a" : "#c29a6e", padding: "3px 8px", background: "rgba(194,154,110,0.1)", borderRadius: 4 }}>
                      {String(bet?.data_status ?? "unknown") === "measured" ? "MEASURED QLOO" : "FIXTURE"}
                    </span>
                  </div>
                  <h3 style={{ margin: "0 0 8px", fontFamily: "var(--display)", fontSize: 32, fontWeight: 400, color: "#e9e3d8" }}>
                    {bet.primary?.cohort_name}
                  </h3>
                  <p style={{ color: "#a7a39b", fontSize: 12, lineHeight: 1.7, marginBottom: 16 }}>
                    {bet.primary?.domain} · {bet.primary?.member_count} entities · affinity {bet.primary?.mean_affinity?.toFixed(2)}
                  </p>
                  <p style={{ color: "#b3aea4", fontSize: 13, lineHeight: 1.8, marginBottom: 12 }}>
                    {String(bet?.why ?? "")}
                  </p>
                  {String(bet?.falsification_condition ?? "") && (
                    <div style={{ marginTop: 16, padding: "12px 14px", background: "rgba(138,80,72,0.1)", border: "1px solid rgba(138,80,72,0.25)", borderRadius: 6 }}>
                      <span className="micro-label" style={{ color: "#c97a6a", marginBottom: 6, display: "block" }}>&#9888; FALSIFICATION CONDITION</span>
                      <p style={{ color: "#d4a89e", fontSize: 12, lineHeight: 1.7, margin: 0 }}>
                        {String(bet?.falsification_condition ?? "")}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Test Card */}
              {testCard && (
                <div style={{ marginBottom: 32, padding: 24, border: "1px solid rgba(130,100,170,0.25)", borderRadius: 8, background: "rgba(130,100,170,0.04)" }}>
                  <span className="eyebrow" style={{ color: "#b09aca", marginBottom: 12, display: "block" }}>&#128300; TEST CARD</span>
                  <h3 style={{ margin: "0 0 16px", fontFamily: "var(--display)", fontSize: 28, fontWeight: 400, color: "#ddd0ec" }}>
                    {String(testCard?.title ?? "")}
                  </h3>
                  {[
                    ["Programme", String(testCard?.programme_context ?? "")],
                    ["Audience Hypothesis", String(testCard?.audience_hypothesis ?? "")],
                    ["Cultural Bridge", String(testCard?.cultural_bridge ?? "")],
                    ["Programming Direction", String(testCard?.programming_direction ?? "")],
                    ["Falsification", String(testCard?.falsification_condition ?? "")],
                  ].filter(([, v]) => v).map(([label, value]) => (
                    <div key={String(label)} style={{ marginBottom: 12 }}>
                      <span className="micro-label">{String(label)}</span>
                      <p style={{ color: "#c5bcd4", fontSize: 12, lineHeight: 1.7, margin: "4px 0 0" }}>{String(value)}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Ranked Cohorts */}
              {result?.cohorts?.ranked?.length > 0 && (
                <div style={{ marginBottom: 24, padding: 20, border: "1px solid var(--rule)", borderRadius: 8 }}>
                  <h3 style={{ margin: "0 0 16px", fontFamily: "var(--display)", fontSize: 22, fontWeight: 400 }}>Ranked Cultural Opportunities</h3>
                  <div style={{ display: "grid", gap: 10 }}>
                    {result.cohorts.ranked.map((cohort: any) => (
                      <div key={cohort.cohort_id} style={{ padding: "12px 16px", border: "1px solid var(--rule)", borderRadius: 6 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <div>
                            <span style={{ fontFamily: "var(--mono)", fontSize: 9, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--amber)", marginRight: 12 }}>#{cohort.rank}</span>
                            <span style={{ color: "#e7e1d7", fontSize: 13, fontWeight: 500 }}>{cohort.domain}</span>
                          </div>
                          <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "#88837a" }}>{cohort.member_count} members · {cohort.verdict}</span>
                        </div>
                        {cohort.score && (
                          <div style={{ marginTop: 8, display: "flex", gap: 16, fontSize: 10, color: "#969187" }}>
                            <span>Affinity: {cohort.score.mean_affinity?.toFixed(4) ?? "—"}</span>
                            <span>Novelty: {cohort.score.novelty_proxy?.toFixed(4) ?? "—"}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Evidence */}
              <div style={{ padding: 24, border: "1px solid var(--rule)", borderRadius: 8 }}>
                <h3 style={{ margin: "0 0 16px", fontFamily: "var(--display)", fontSize: 28, fontWeight: 400 }}>Evidence</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
                  {[
                    ["Qloo calls", evidence?.qloo_calls],
                    ["Trace rows", evidence?.trace_rows],
                    ["Stop reason", evidence?.stop_reason],
                    ["Status", run.status],
                  ].map(([label, value]) => (
                    <div key={String(label)}>
                      <span className="micro-label">{String(label)}</span>
                      <span style={{ display: "block", color: "#e9e3d8", fontSize: 14, marginTop: 4 }}>{String(value ?? "—")}</span>
                    </div>
                  ))}
                </div>
              </div>
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
              }}>
                The cultural territory<br />you are <em style={{ color: "#bcb4a7" }}>not yet exploring.</em>
              </h2>
            </div>
            <p style={{ maxWidth: 310, margin: 0, color: "#a7a39b", fontSize: 14, lineHeight: 1.8 }}>
              An adjacent direction should feel close enough to belong, and new enough to create a reason to visit.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 32, alignItems: "start" }}>
            {/* Expressed */}
            <div>
              <span className="micro-label" style={{ marginBottom: 12, display: "block" }}>01 / EXPRESSED</span>
              <h3 style={{ fontFamily: "var(--display)", fontSize: "clamp(28px, 3vw, 42px)", fontWeight: 400, margin: "0 0 24px", lineHeight: 1 }}>
                What the cinema<br /><em style={{ color: "#bcb4a7" }}>already programmes.</em>
              </h3>
              {[
                ["Independent film", "92%"], ["Auteur-led work", "80%"],
                ["Contemporary stories", "72%"], ["Drama / romance", "63%"],
                ["Visual authorship", "57%"],
              ].map(([label, width]) => (
                <div key={String(label)} style={{ display: "grid", gridTemplateColumns: "120px 1fr 60px", gap: 10, alignItems: "center", marginBottom: 10 }}>
                  <span style={{ color: "#b3aea4", fontSize: 11 }}>{String(label)}</span>
                  <div style={{ height: 3, background: "rgba(232,226,213,0.08)", borderRadius: 2 }}>
                    <div style={{ width: String(width), height: "100%", background: "var(--amber)", borderRadius: 2 }} />
                  </div>
                  <span className="mono-note" style={{ fontSize: 8 }}>PRESENT</span>
                </div>
              ))}
            </div>

            {/* Bridge arrow */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, padding: "48px 0", color: "var(--amber)" }}>
              <span className="mono-note" style={{ color: "var(--amber)" }}>EXTEND</span>
              <span style={{ fontSize: 24 }}>&rarr;</span>
            </div>

            {/* Adjacent */}
            <div>
              <span className="micro-label" style={{ marginBottom: 12, display: "block" }}>02 / NEIGHBOURING</span>
              <h3 style={{ fontFamily: "var(--display)", fontSize: "clamp(28px, 3vw, 42px)", fontWeight: 400, margin: "0 0 24px", lineHeight: 1 }}>
                Adjacent<br /><em style={{ color: "#bcb4a7" }}>territory.</em>
              </h3>
              {[
                ["Contemporary classical", "86%"], ["Live performance", "78%"],
                ["Composer-led events", "69%"], ["Experimental sound", "62%"],
                ["Cultural venues", "55%"],
              ].map(([label, width]) => (
                <div key={String(label)} style={{ display: "grid", gridTemplateColumns: "140px 1fr 60px", gap: 10, alignItems: "center", marginBottom: 10 }}>
                  <span style={{ color: "#b3aea4", fontSize: 11 }}>{String(label)}</span>
                  <div style={{ height: 3, background: "rgba(232,226,213,0.08)", borderRadius: 2 }}>
                    <div style={{ width: String(width), height: "100%", background: "rgba(194,154,110,0.5)", borderRadius: 2 }} />
                  </div>
                  <span className="mono-note" style={{ fontSize: 8 }}>ADJACENT</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ textAlign: "center", padding: "48px 0 0", borderTop: "1px solid var(--rule)", marginTop: 48 }}>
            <span className="micro-label" style={{ marginBottom: 12, display: "block" }}>A DISTINCTION THAT MATTERS</span>
            <p style={{ fontFamily: "var(--display)", fontSize: "clamp(22px, 2.5vw, 32px)", fontWeight: 400, margin: 0, lineHeight: 1.3 }}>
              We are not predicting an audience.<br />
              <em style={{ color: "#bcb4a7" }}>We are identifying a cultural direction worth testing.</em>
            </p>
          </div>
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
              }}>
                Programme<br /><em style={{ color: "#bcb4a7" }}>experiment.</em>
              </h2>
            </div>
            <p style={{ maxWidth: 310, margin: 0, color: "#a7a39b", fontSize: 14, lineHeight: 1.8 }}>
              A bounded test of a cultural adjacency. Not a new identity for the cinema.
            </p>
          </div>

          <article style={{ padding: 32, border: "1px solid var(--rule)", borderRadius: 8, background: "rgba(232,226,213,0.02)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24, paddingBottom: 16, borderBottom: "1px solid var(--rule)" }}>
              <span className="micro-label">PROGRAMME EXPERIMENT</span>
              <span className="mono-note">RUN ANALYSIS ABOVE TO POPULATE</span>
            </div>

            {run?.result?.test_card ? (
              <>
                <div style={{ marginBottom: 24 }}>
                  <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>THE BET</span>
                  <h3 style={{ fontFamily: "var(--display)", fontSize: 32, fontWeight: 400, margin: "0 0 8px", color: "#e9e3d8" }}>
                    {String(testCard?.title ?? "")}
                  </h3>
                </div>
                {String(testCard?.audience_hypothesis ?? "") && (
                  <div style={{ marginBottom: 24 }}>
                    <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>HYPOTHESIS</span>
                    <p style={{ color: "#b3aea4", fontSize: 14, lineHeight: 1.8, margin: 0 }}>
                      &ldquo;{String(testCard?.audience_hypothesis ?? "")}&rdquo;
                    </p>
                  </div>
                )}
                {String(testCard?.falsification_condition ?? "") && (
                  <div style={{ marginBottom: 24 }}>
                    <span className="micro-label" style={{ marginBottom: 8, display: "block" }}>FAILURE CONDITIONS</span>
                    <p style={{ color: "#c97a6a", fontSize: 13, lineHeight: 1.7, margin: 0 }}>
                      {String(testCard?.falsification_condition ?? "")}
                    </p>
                  </div>
                )}
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

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--rule)" }}>
              <span className="mono-note">NO ATTENDANCE TARGETS / NO CONVERSION CLAIMS</span>
              <span className="mono-note">REVIEW AFTER THE EXPERIMENT</span>
            </div>
          </article>

          <footer style={{ display: "flex", justifyContent: "space-between", marginTop: 48, paddingTop: 24, borderTop: "1px solid var(--rule)" }}>
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