"use client";

/**
 * Cinema Mode — composition ported from the source ZIP (`pages/Cinema.tsx`):
 * photographic opening chapter, sticky chapter rail, house notes,
 * programme contact sheet, cultural field, opportunity, decision challenge and
 * Test Card. The Challenge chapter sits between the recommendation and the test
 * on purpose: that is the moment a sceptical programmer asks "why should I
 * believe this?", and the answer has to be checkable before anything is
 * pre-registered.
 *
 * The programme is submitted to the real `/run` endpoint (or to the explicit
 * `/run/demo` fixture route); the fingerprint, geography, Programme Bet and
 * Test Card are the backend's own responses, and the four pre-registration
 * fields the venue edits are exported verbatim.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Plus, Trash2 } from "lucide-react";
import {
  DEMO_PROGRAMME,
  createDemoRun,
  createRun,
  getHealth,
  getRun,
  streamRun,
  type ProgrammeItemInput,
  type RunResponse,
  type SSEEvent,
} from "@/lib/api";
import type { AdjacentRunResult } from "@/types/adjacent";
import { watchRunWithRecovery } from "@/lib/runRecovery";
import {
  createTestDesign,
  testDesignExportSections,
  updateTestDesign,
  type TestDesign,
  type TestDesignField,
} from "@/lib/testCardDesign";
import { downloadTextFile, formatTestCardText, safeTextFilename } from "@/lib/testCardExport";
import { buildFingerprintNodes, buildStageViews, stageStatusLabel } from "@/lib/nfData";
import { photos } from "@/lib/photos";
import { PhotoFrame } from "@/components/nf/PhotoFrame";
import { Field, TextInput } from "@/components/nf/Field";
import { CulturalFingerprint } from "@/components/nf/CulturalFingerprint";
import { TestCard } from "@/components/nf/TestCard";
import { ClaimChip, DataChip, RunChip } from "@/components/nf/Chips";
import { ChallengeSummary, DecisionChallenge } from "@/components/nf/DecisionChallenge";
import { WhyThisResult } from "@/components/nf/WhyThisResult";
import { buildChallengeView, challengeExportSections, formatDecisionReceipt } from "@/lib/challengeView";
import { EvidenceTraceLog } from "@/components/EvidenceTrace";
import GeographyMap from "@/components/GeographyMap";
import { cn } from "@/lib/cn";

type ChapterId = "cinema" | "programme" | "cultural-field" | "opportunity" | "challenge" | "test";

const CHAPTERS: { id: ChapterId; label: string; needsRun: boolean }[] = [
  { id: "cinema", label: "Cinema", needsRun: false },
  { id: "programme", label: "Programme", needsRun: false },
  { id: "cultural-field", label: "Cultural field", needsRun: true },
  { id: "opportunity", label: "Opportunity", needsRun: true },
  { id: "challenge", label: "Challenge", needsRun: true },
  { id: "test", label: "Test", needsRun: true },
];

type ProgrammeRow = { title: string; year: string; imdbId: string; note: string };

const blankProgramme: ProgrammeRow[] = [
  { title: "", year: "", imdbId: "", note: "" },
  { title: "", year: "", imdbId: "", note: "" },
  { title: "", year: "", imdbId: "", note: "" },
];

const CONTACT_SHEET = [
  photos.cinemaSeats,
  photos.urbanPuddle,
  photos.columns,
  photos.soho,
  photos.nightAlley,
  photos.lanternStreet,
];

export default function CinemaPage() {
  const [venue, setVenue] = useState("");
  const [city, setCity] = useState("");
  const [programme, setProgramme] = useState<ProgrammeRow[]>(blankProgramme);
  const [selected, setSelected] = useState(0);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [analysing, setAnalysing] = useState(false);
  const [mode, setMode] = useState<"fixture" | "live" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chapter, setChapter] = useState<ChapterId>("cinema");

  const [experimentDesign, setExperimentDesign] = useState<TestDesign | null>(null);
  const [editingCard, setEditingCard] = useState(false);

  const stopStream = useRef<(() => void) | null>(null);
  const runGeneration = useRef(0);
  const activeRunId = useRef<string | null>(null);

  const result: AdjacentRunResult | null = useMemo(() => {
    const candidate = (run?.result as AdjacentRunResult | null) ?? null;
    if (!candidate) return null;
    return candidate.data_status === "measured" || candidate.data_status === "fixture"
      ? candidate
      : null;
  }, [run?.result]);

  const completed = run?.status === "completed" && Boolean(result);
  const failed = run?.status === "failed";
  const insufficient = run?.status === "insufficient";
  const traceRows = run?.trace ?? [];

  const stages = useMemo(
    () => buildStageViews({ started: Boolean(runId), status: run?.status ?? null, events }),
    [runId, run?.status, events],
  );

  useEffect(() => {
    const card = result?.test_card;
    if (!card) {
      setExperimentDesign(null);
      return;
    }
    setExperimentDesign(createTestDesign(card));
  }, [runId, result?.test_card]);

  useEffect(() => {
    const targets = CHAPTERS.map((item) => document.getElementById(item.id)).filter(
      (element): element is HTMLElement => element instanceof HTMLElement,
    );
    if (!targets.length || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target instanceof HTMLElement) setChapter(visible.target.id as ChapterId);
      },
      { rootMargin: "-25% 0px -60% 0px", threshold: [0, 0.2, 0.5] },
    );
    targets.forEach((target) => observer.observe(target));
    return () => observer.disconnect();
  }, [runId, run?.status]);

  useEffect(() => {
    return () => {
      runGeneration.current += 1;
      activeRunId.current = null;
      stopStream.current?.();
      stopStream.current = null;
    };
  }, []);

  const watchRun = useCallback((id: string) => {
    const generation = ++runGeneration.current;
    activeRunId.current = id;
    stopStream.current?.();
    setRunId(id);
    setAnalysing(true);
    setEvents([]);

    const isCurrent = () => runGeneration.current === generation && activeRunId.current === id;
    stopStream.current = watchRunWithRecovery(id, {
      isCurrent,
      stream: streamRun,
      fetchRun: getRun,
      onEvent: (event) => {
        if (isCurrent()) setEvents((previous) => [...previous, event]);
      },
      onRun: (response) => {
        if (!isCurrent()) return;
        setRun(response);
        if (["completed", "failed", "insufficient"].includes(response.status)) setAnalysing(false);
      },
      onExhausted: () => {
        if (!isCurrent()) return;
        setError("The stream disconnected and the run status could not be confirmed. Retry.");
        setAnalysing(false);
      },
    });
  }, []);

  const cancelRunWatch = useCallback(() => {
    runGeneration.current += 1;
    activeRunId.current = null;
    stopStream.current?.();
    stopStream.current = null;
  }, []);

  function loadSampleProgramme() {
    setVenue("The Light House");
    setCity("Brighton, United Kingdom");
    setProgramme(
      DEMO_PROGRAMME.map((item) => ({
        title: item.title,
        year: item.year ? String(item.year) : "",
        imdbId: item.imdb_id ?? "",
        note: "",
      })),
    );
  }

  function validate(): ProgrammeItemInput[] | null {
    if (!venue.trim()) {
      setFormError("A venue is required before an analysis.");
      return null;
    }
    if (!city.trim()) {
      setFormError("A city is required before an analysis.");
      return null;
    }
    const items: ProgrammeItemInput[] = [];
    for (const [index, row] of programme.entries()) {
      const title = row.title.trim();
      const imdbId = row.imdbId.trim();
      if (!title) {
        if (row.year.trim() || imdbId || row.note.trim()) {
          setFormError(`Row ${index + 1} has a year, IMDb ID, or note but no title.`);
          return null;
        }
        continue;
      }
      const year = row.year.trim() ? Number(row.year) : undefined;
      if (
        row.year.trim() &&
        (!Number.isInteger(year) || Number(year) < 1888 || Number(year) > 2100)
      ) {
        setFormError(`Row ${index + 1}: year must be between 1888 and 2100.`);
        return null;
      }
      items.push({ title, year, imdb_id: imdbId || undefined });
    }
    if (items.length === 0) {
      setFormError("Enter at least one film title.");
      return null;
    }
    if (items.length > 12) {
      setFormError("The engine accepts at most twelve titles per programme.");
      return null;
    }
    setFormError(null);
    return items;
  }

  function startFixture() {
    cancelRunWatch();
    setError(null);
    setNotice(null);
    setRun(null);
    setRunId(null);
    setMode("fixture");
    setAnalysing(true);
    if (!programme.some((row) => row.title.trim())) loadSampleProgramme();
    if (!venue.trim()) setVenue("The Light House");
    if (!city.trim()) setCity("Brighton, United Kingdom");
    document.getElementById("programme")?.scrollIntoView({ behavior: "smooth", block: "start" });
    createDemoRun()
      .then((response) => watchRun(response.run_id))
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Failed to start the fixture run");
        setAnalysing(false);
      });
  }

  // Live analysis is a server-side decision (public-demo gate + a configured
  // Qloo key). Ask once so the button reflects it instead of failing on click.
  const [liveNotice, setLiveNotice] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    getHealth()
      .then((backend) => {
        if (!active) return;
        if (backend.public_demo && backend.live_creator_available === false) {
          setLiveNotice(
            "Live analysis is disabled for this deployment. The labelled fixture run stays available and is clearly marked as a fixture.",
          );
        } else if (backend.qloo_configured === false) {
          setLiveNotice(
            "This backend has no Qloo key configured, so a live analysis will stop with a configuration error. The labelled fixture run is available.",
          );
        } else {
          setLiveNotice(null);
        }
      })
      .catch(() => {
        if (active) setLiveNotice(null);
      });
    return () => {
      active = false;
    };
  }, []);

  function startLive() {
    const items = validate();
    if (!items) return;
    cancelRunWatch();
    setError(null);
    setNotice(null);
    setRun(null);
    setRunId(null);
    setMode("live");
    setAnalysing(true);
    document.getElementById("programme")?.scrollIntoView({ behavior: "smooth", block: "start" });
    createRun({ city: city.trim(), venue_name: venue.trim(), programme: items })
      .then((response) => watchRun(response.run_id))
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Failed to start the analysis");
        setAnalysing(false);
      });
  }

  const enteredProgramme = programme.filter((row) => row.title.trim());
  const returnedProgramme = result?.programme?.items ?? [];
  const displayProgramme =
    returnedProgramme.length > 0
      ? returnedProgramme.map((item) => ({
          title: item.title,
          year: item.year ? String(item.year) : "",
          note: enteredProgramme.find((row) => row.title === item.title)?.note ?? "",
          resolved: Boolean(item.resolved),
          qlooName: item.qloo_name ?? null,
        }))
      : enteredProgramme.map((row) => ({
          title: row.title,
          year: row.year,
          note: row.note,
          resolved: false,
          qlooName: null,
        }));

  const geography = result?.geography ?? null;
  const geographyCells = (geography?.highest_affinity_cells ?? geography?.cells ?? []).filter(
    (cell): cell is typeof cell & { affinity: number } => typeof cell.affinity === "number",
  );
  const hasGeography = Boolean(geography?.sufficient && geographyCells.length > 0);

  const fingerprintNodes = useMemo(
    () => (completed ? buildFingerprintNodes(result, venue || "This programme", traceRows) : []),
    [completed, result, venue, traceRows],
  );

  const bet = result?.programme_bet ?? null;
  const card = result?.test_card ?? null;
  const challenge = result?.challenge ?? null;

  function exportReceipt() {
    const text = formatDecisionReceipt(challenge);
    downloadTextFile(safeTextFilename(`decision-receipt-${runId ?? "run"}`) + ".txt", text);
    setNotice("Decision receipt exported as plain text.");
  }

  function goToTest() {
    document.getElementById("test")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function exportTestCard() {
    if (!card) return;
    const activeDesign = experimentDesign ?? createTestDesign(card);
    const text = formatTestCardText({
      title: card.title,
      context: `CINEMA: ${venue || "Unnamed venue"} · ${city || "City not supplied"}`,
      dataStatus: card.data_status,
      sections: [
        { label: "Programme context", value: card.programme_context },
        { label: "Audience hypothesis", value: card.audience_hypothesis },
        { label: "Cultural bridge", value: card.cultural_bridge },
        { label: "Geographic signal", value: card.geographic_signal },
        { label: "Programming direction", value: card.programming_direction },
        { label: "Primary evidence", value: card.primary_evidence },
        { label: "Runner-up direction", value: card.runner_up },
        { label: "Observable success criteria", value: card.success_criteria },
        ...testDesignExportSections(activeDesign),
        { label: "Falsification condition", value: card.falsification_condition },
        // The decision's fragility travels with the test: an experiment recorded
        // without it would be judged against a recommendation whose basis was
        // never stated.
        ...challengeExportSections(challenge),
      ],
      provenance: card.provenance,
      footerNote:
        "This is a bounded programming hypothesis, not a new identity for the cinema. Affinity is not an attendance or conversion forecast.",
    });
    downloadTextFile(safeTextFilename(card.title) + ".txt", text);
    setNotice("Cinema test card exported as plain text.");
  }

  const PREREG_FIELDS: Array<{ label: string; field: TestDesignField; rows: number; note?: string }> = [
    { label: "COMPARISON PROTOCOL · EDIT BEFORE EXPORT", field: "comparison_protocol", rows: 4 },
    { label: "PRIMARY MEASURE · EDIT BEFORE EXPORT", field: "primary_measure", rows: 4 },
    {
      label: "DECISION RULE · PROPOSED PROMPT, SET BEFORE SCREENING",
      field: "decision_rule",
      rows: 4,
      note: "Adjacent suggests no numerical threshold. Enter one only if the venue has chosen it before the screening.",
    },
    { label: "OBSERVATION WINDOW · EDIT BEFORE EXPORT", field: "observation_window", rows: 3 },
  ];

  return (
    <div>
      {/* CHAPTER — CINEMA */}
      <section id="cinema" className="relative min-h-[70vh] scroll-mt-36 overflow-hidden">
        <div className="absolute inset-0">
          <PhotoFrame photo={photos.cinemaCurtain} className="h-full" credit={false} priority />
          <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/55 to-ink/30" />
        </div>
        <div className="relative z-10 mx-auto flex min-h-[70vh] max-w-[1440px] flex-col justify-end px-4 pb-12 pt-28 md:px-8">
          <p className="type-kicker">Cinema Mode</p>
          <h1 className="font-display mt-4 max-w-[16ch] text-5xl leading-[0.92] md:text-7xl">
            A programmer&apos;s cultural atlas.
          </h1>
          <p className="mt-5 max-w-lg text-sm leading-relaxed text-paper-2 md:text-base">
            Venue, city, a programme of films. Curation rather than a poster wall. Geography only
            when coordinates actually exist.
          </p>
          <p className="caption mt-6">Photo · {photos.cinemaCurtain.credit} / Pexels</p>
        </div>
      </section>

      <nav
        className="sticky top-[64px] z-40 border-b border-line bg-ink/95 backdrop-blur"
        aria-label="Cinema chapters"
      >
        <div className="mx-auto flex max-w-[1440px] gap-1 overflow-x-auto px-4 py-2 md:px-8">
          {CHAPTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() =>
                document
                  .getElementById(item.id)
                  ?.scrollIntoView({ behavior: "smooth", block: "start" })
              }
              aria-current={chapter === item.id ? "true" : undefined}
              className={cn(
                "shrink-0 border-b-2 px-4 py-2 font-mono text-[0.62rem] uppercase tracking-[0.16em] transition-colors",
                chapter === item.id
                  ? "border-amber text-paper"
                  : "border-transparent text-mute hover:text-paper-2",
                item.needsRun && !completed && "opacity-60",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      {(error || formError || notice) && (
        <div className="border-b border-amber/30 bg-amber/10" role="status" aria-live="polite">
          <p className="mx-auto max-w-[1440px] px-4 py-3 text-sm text-amber md:px-8">
            {formError ?? error ?? notice}
          </p>
        </div>
      )}

      <section className="mx-auto grid max-w-[1440px] gap-10 px-4 py-16 md:grid-cols-12 md:px-8">
        <div className="md:col-span-5">
          <p className="type-kicker">House notes</p>
          <h2 className="font-display mt-3 text-3xl md:text-4xl">The desk</h2>
          <div className="mt-8 space-y-6">
            <Field label="Venue">
              <TextInput
                maxLength={120}
                value={venue}
                onChange={(event) => setVenue(event.target.value)}
                placeholder="The Light House"
              />
            </Field>
            <Field
              label="City"
              hint="Geography appears only when the run returns usable coordinates."
            >
              <TextInput
                maxLength={120}
                value={city}
                onChange={(event) => setCity(event.target.value)}
                placeholder="Brighton, United Kingdom"
              />
            </Field>
          </div>
          <div className="mt-8 flex flex-wrap gap-3">
            <button type="button" className="btn-primary" onClick={startFixture} disabled={analysing}>
              Run labelled fixture
              <ArrowRight size={16} />
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={startLive}
              disabled={analysing || liveNotice !== null}
              aria-disabled={analysing || liveNotice !== null}
            >
              Analyse programme (live)
            </button>
            <button type="button" className="btn-ghost" onClick={loadSampleProgramme}>
              Load sample programme
            </button>
          </div>
          {liveNotice && (
            <p role="status" className="mt-4 max-w-xl text-xs leading-relaxed text-mute">
              {liveNotice}
            </p>
          )}
          <div className="mt-6 flex flex-wrap items-center gap-2">
            <RunChip status={run?.status ?? (analysing ? "running" : "idle")} />
            {mode === "fixture" && <DataChip status="fixture" />}
            {mode === "live" && !completed && !analysing && <DataChip status="unavailable" />}
            {result && <DataChip status={result.data_status} />}
            {runId && <span className="caption">Run {runId}</span>}
          </div>
        </div>
        <div className="md:col-span-7">
          <p className="field-label">Programme</p>
          <p className="mb-4 text-xs text-dim">
            Titles and years. IMDb IDs help resolve films precisely, but are optional: Qloo
            title/year search is verified by the backend, and ambiguous matches are reported rather than
            guessed. Notes stay with your own record; photography here is atmospheric — not official artwork.
          </p>
          <ul className="space-y-3">
            {programme.map((row, index) => (
              <li
                key={index}
                className="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(10rem,1.4fr)_5.5rem_8.5rem_minmax(10rem,1fr)_2.5rem]"
              >
                <TextInput
                  aria-label={`Film title ${index + 1}`}
                  maxLength={200}
                  placeholder="Perfect Days"
                  value={row.title}
                  onChange={(event) => {
                    const next = [...programme];
                    next[index] = { ...row, title: event.target.value };
                    setProgramme(next);
                  }}
                />
                <TextInput
                  aria-label={`Year ${index + 1}`}
                  maxLength={4}
                  inputMode="numeric"
                  placeholder="2023"
                  value={row.year}
                  onChange={(event) => {
                    const next = [...programme];
                    next[index] = { ...row, year: event.target.value };
                    setProgramme(next);
                  }}
                />
                <TextInput
                  aria-label={`IMDb ID ${index + 1}`}
                  maxLength={20}
                  placeholder="IMDb ID (e.g. tt1234567)"
                  value={row.imdbId}
                  onChange={(event) => {
                    const next = [...programme];
                    next[index] = { ...row, imdbId: event.target.value };
                    setProgramme(next);
                  }}
                />
                <TextInput
                  aria-label={`Curatorial note ${index + 1}`}
                  maxLength={160}
                  placeholder="Curatorial note"
                  value={row.note}
                  onChange={(event) => {
                    const next = [...programme];
                    next[index] = { ...row, note: event.target.value };
                    setProgramme(next);
                  }}
                />
                <button
                  type="button"
                  className="flex h-10 items-center justify-center text-mute hover:text-blood"
                  aria-label={`Remove title ${index + 1}`}
                  onClick={() => setProgramme(programme.filter((_, rowIndex) => rowIndex !== index))}
                >
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="btn-ghost mt-4"
            disabled={programme.length >= 12}
            onClick={() => setProgramme([...programme, { title: "", year: "", imdbId: "", note: "" }])}
          >
            <Plus size={14} />
            {programme.length >= 12 ? "12 title limit reached" : "Add title"}
          </button>
        </div>
      </section>

      {/* CHAPTER — PROGRAMME */}
      <section id="programme" className="scroll-mt-36 border-t border-line bg-ink-2">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="type-kicker">Programme · contact sheet</p>
              <h2 className="font-display mt-2 text-3xl md:text-5xl">
                The programme as a strip, not a store.
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {run?.status === "running" && <RunChip status="running" />}
              {mode === "fixture" && <DataChip status="fixture" />}
              {result && <DataChip status={result.data_status} />}
            </div>
          </div>

          {(analysing || runId) && (
            <ol className="mt-8 grid gap-x-8 md:grid-cols-2">
              {stages.map((stage) => (
                <li key={stage.id} className="flex justify-between border-t border-line py-3 text-sm">
                  <span>{stage.label}</span>
                  <span
                    className={cn(
                      "font-mono text-[0.62rem]",
                      stage.state === "done" && "text-sage",
                      stage.state === "now" && "text-amber",
                      stage.state === "wait" && "text-dim",
                      stage.state === "skipped" && "text-blood",
                    )}
                  >
                    {stageStatusLabel(stage.state)}
                  </span>
                </li>
              ))}
            </ol>
          )}

          {(failed || insufficient) && (
            <div className="mt-8 border border-dashed border-line-strong p-6">
              <span className="chip chip-warn">{insufficient ? "Insufficient evidence" : "Run failed"}</span>
              <p className="mt-3 text-sm leading-relaxed text-paper-2">
                No map or cohort was drawn to hide the gap. A fixture run is optional and labelled.
                {run?.stop_message ? ` ${run.stop_message}` : ""}
              </p>
              {runId && (
                <button
                  type="button"
                  className="btn-ghost mt-4"
                  onClick={() => {
                    setError(null);
                    watchRun(runId);
                  }}
                >
                  Retry loading this run
                </button>
              )}
            </div>
          )}

          <p className="mt-10 max-w-xl text-sm text-mute">
            Images are atmospheric references. They are not posters, stills, or rights-cleared
            artwork for the titles listed.
          </p>

          {displayProgramme.length === 0 ? (
            <p className="mt-6 text-sm text-dim">
              No titles entered yet. The contact sheet appears once the programme has entries.
            </p>
          ) : (
            <div className="mt-6 flex gap-3 overflow-x-auto pb-4">
              {displayProgramme.map((item, index) => (
                <button
                  key={`${item.title}-${index}`}
                  type="button"
                  onClick={() => setSelected(index)}
                  aria-pressed={selected === index}
                  className={cn(
                    "w-44 shrink-0 text-left",
                    selected === index ? "opacity-100" : "opacity-70 hover:opacity-100",
                  )}
                >
                  <PhotoFrame
                    photo={CONTACT_SHEET[index % CONTACT_SHEET.length]}
                    className="aspect-[3/4]"
                    credit={false}
                    gate
                  />
                  <p className="mt-3 font-display text-xl">{item.title}</p>
                  <p className="caption mt-1">
                    {item.year || "year not given"} · {item.note || "no note"}
                  </p>
                  {result && (
                    <p className="caption mt-1">
                      {item.resolved
                        ? `Resolved · ${item.qlooName ?? "provider entity"}`
                        : "Unresolved — not admitted to the profile"}
                    </p>
                  )}
                </button>
              ))}
            </div>
          )}
          {displayProgramme[selected] && (
            <p className="mt-2 text-sm text-paper-2">
              Selected · {displayProgramme[selected].title} (
              {displayProgramme[selected].year || "year not given"}) —{" "}
              {displayProgramme[selected].note || "no curatorial note yet"}
            </p>
          )}

          {result && (
            <p className="mt-4 font-mono text-[0.62rem] text-dim">
              RESOLVED {result.programme.resolved_count} / {result.programme.total_count} · QLOO
              CALLS {result.evidence.qloo_calls} · TRACE ROWS {result.evidence.trace_rows} · STOP{" "}
              {result.evidence.stop_reason}
            </p>
          )}
        </div>
      </section>

      {/* CHAPTER — CULTURAL FIELD */}
      <section id="cultural-field" className="scroll-mt-36 border-t border-line">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="type-kicker">Cultural field</p>
              <h2 className="font-display mt-2 text-4xl md:text-5xl">Returned worlds</h2>
            </div>
            {result && <DataChip status={result.data_status} />}
          </div>

          {completed ? (
            <>
              <div className="mt-8">
                <CulturalFingerprint
                  nodes={fingerprintNodes}
                  filmTitle={venue || "This programme"}
                  dataStatus={result?.data_status}
                  emptyBody="The run completed without a usable cultural field. An empty field is reported as empty rather than illustrated."
                />
              </div>

              {(result?.cohorts.ranked.length ?? 0) > 0 && (
                <div className="mt-8 border border-line p-5 md:p-6">
                  <p className="type-kicker">Winning cohort · provider attribution</p>
                  <p className="mt-2 max-w-2xl text-xs leading-relaxed text-mute">
                    {result?.cohorts.ranked[0]?.domain.replace("urn:entity:", "")} ·{" "}
                    {result?.cohorts.ranked[0]?.members.length ?? 0} members. Attribution is
                    provider-reported contribution, not an audience or revenue estimate.
                  </p>
                  <WhyThisResult
                    members={result?.cohorts.ranked[0]?.members}
                    programme={result?.programme}
                    bounded={result?.evidence?.bounded_attribution}
                  />
                </div>
              )}

              <div className="mt-10 grid gap-8 border border-line p-6 md:grid-cols-2">
                <div>
                  <p className="type-kicker">Geography</p>
                  <h3 className="font-display mt-3 text-3xl">
                    {hasGeography
                      ? "Coordinates returned by this run."
                      : "City context without a fake heat map."}
                  </h3>
                  <p className="mt-4 text-sm leading-relaxed text-mute">
                    {hasGeography
                      ? `${city || geography?.city_display || "The city"} is drawn from ${geographyCells.length} returned affinity cell(s). Affinity is a cultural-similarity signal, not attendance.`
                      : `${city || "The city"} is recorded as venue context. This run did not return usable coordinates${
                          geography?.note ? ` — ${geography.note}` : ""
                        }, so no choropleth, pins or attendance surface is rendered.`}
                  </p>
                  {geography?.call_id && (
                    <p className="mt-3 font-mono text-[0.62rem] text-dim">CALL {geography.call_id}</p>
                  )}
                </div>
                {hasGeography && geography ? (
                  <div className="min-h-[280px] overflow-hidden border border-line">
                    <GeographyMap geography={geography} />
                  </div>
                ) : (
                  <div className="flex min-h-[200px] items-end border border-dashed border-line-strong p-4">
                    <p className="caption">Map withheld · insufficient geographic evidence</p>
                  </div>
                )}
              </div>

              {hasGeography && geographyCells.length > 0 && (
                <div className="mt-4 overflow-auto border border-line">
                  <table className="w-full text-left text-sm">
                    <caption className="caption px-4 py-2 text-left">
                      Returned affinity cells · not attendance, not reachable audience
                    </caption>
                    <thead>
                      <tr className="border-b border-line font-mono text-[0.58rem] uppercase tracking-[0.12em] text-dim">
                        <th className="px-4 py-2">Geohash</th>
                        <th className="px-4 py-2">Latitude</th>
                        <th className="px-4 py-2">Longitude</th>
                        <th className="px-4 py-2">Affinity</th>
                        <th className="px-4 py-2">Rank</th>
                      </tr>
                    </thead>
                    <tbody>
                      {geographyCells.slice(0, 24).map((cell, index) => (
                        <tr key={`${cell.geohash ?? "cell"}-${index}`} className="border-b border-line">
                          <td className="px-4 py-2 font-mono text-[0.62rem] text-mute">
                            {cell.geohash ?? "—"}
                          </td>
                          <td className="px-4 py-2 text-paper-2">{cell.latitude.toFixed(3)}</td>
                          <td className="px-4 py-2 text-paper-2">{cell.longitude.toFixed(3)}</td>
                          <td className="px-4 py-2 text-amber">{cell.affinity.toFixed(2)}</td>
                          <td className="px-4 py-2 text-mute">{cell.affinity_rank ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {traceRows.length > 0 && (
                <div className="mt-8 border border-line p-5">
                  <p className="type-kicker">Evidence trace</p>
                  <p className="mt-2 text-xs text-mute">
                    Every recorded provider call for this run. Parameters are redacted server-side.
                  </p>
                  <div className="mt-3 max-h-[360px] overflow-auto pr-1">
                    <EvidenceTraceLog rows={traceRows} scope="cinema-run" />
                  </div>
                </div>
              )}
            </>
          ) : (
            <Locked
              title="No cultural field yet."
              body="Ranked cohorts, rejected worlds and geographic evidence appear only after a completed run. Empty is not a graph."
              action="Run labelled fixture"
              onAction={startFixture}
            />
          )}
        </div>
      </section>

      {/* CHAPTER — OPPORTUNITY */}
      <section id="opportunity" className="scroll-mt-36 border-t border-line bg-ink-2">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <p className="type-kicker">Opportunity · programming direction</p>
          {completed && bet ? (
            <div className="mt-6 grid gap-10 md:grid-cols-12">
              <div className="md:col-span-7">
                <ClaimChip kind="HYPOTHESIS" />
                <h2 className="font-display mt-5 text-3xl leading-tight md:text-5xl">
                  The {bet.primary.domain.replace("urn:entity:", "")} world — via{" "}
                  {bet.primary.cohort_name}
                </h2>
                <p className="mt-5 text-sm leading-relaxed text-paper-2">{bet.why}</p>
                {bet.cultural_bridge && (
                  <p className="mt-4 text-sm leading-relaxed text-paper-2">
                    <span className="text-amber">Bridge · </span>
                    {bet.cultural_bridge}
                  </p>
                )}
                {bet.programming_direction && (
                  <p className="mt-3 text-sm leading-relaxed text-paper-2">
                    <span className="text-amber">Direction · </span>
                    {bet.programming_direction}
                  </p>
                )}
                <p className="mt-4 font-mono text-[0.65rem] text-dim">
                  {bet.primary.member_count} entities
                  {typeof bet.primary.mean_affinity === "number"
                    ? ` · mean affinity ${bet.primary.mean_affinity.toFixed(2)}`
                    : " · no mean affinity"}
                  {bet.primary.call_id ? ` · call ${bet.primary.call_id}` : ""}
                  {` · ${String(bet.data_status).toUpperCase()}`}
                </p>
                {bet.falsification_condition && (
                  <div className="mt-6 border border-blood/40 bg-blood/10 p-4">
                    <p className="caption text-warn">Falsification condition</p>
                    <p className="mt-2 text-sm leading-relaxed text-paper-2">
                      {bet.falsification_condition}
                    </p>
                  </div>
                )}
                <ul className="mt-6 space-y-3">
                  {bet.rejected_candidates.map((candidate) => (
                    <li key={candidate.cohort_id} className="text-sm text-mute">
                      — Rejected · {candidate.domain.replace("urn:entity:", "")} — {candidate.reason}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="md:col-span-5">
                <PhotoFrame photo={photos.cinemaAisle} className="aspect-[4/5]" />
                {bet.two_sided_signals?.methodology_note && (
                  <p className="caption mt-4">{bet.two_sided_signals.methodology_note}</p>
                )}
              </div>
            </div>
          ) : completed ? (
            <div className="mt-6 border border-dashed border-line-strong p-8">
              <span className="chip chip-warn">No supported direction</span>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                This run completed without a Programme Bet. Nothing is substituted for a missing
                recommendation.
              </p>
            </div>
          ) : (
            <Locked
              title="No programming direction yet."
              body="The proposed direction is an interpretation written over ranked cohorts. Without a run there is nothing to interpret."
              action="Run labelled fixture"
              onAction={startFixture}
            />
          )}
        </div>
      </section>

      {/* CHAPTER — CHALLENGE */}
      <section id="challenge" className="scroll-mt-36 border-t border-line bg-ink-2">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="type-kicker">Challenge · necessity and stability</p>
              <p className="mt-2 max-w-xl text-sm text-mute">
                Two questions asked of the recommendation above, answered from this run&rsquo;s own
                cached evidence. No extra Qloo calls, and no forecast of what an audience will do.
              </p>
            </div>
          </div>

          {completed ? (
            <DecisionChallenge
              challenge={challenge}
              onExportReceipt={exportReceipt}
              onGoToTest={goToTest}
            />
          ) : (
            <Locked
              title="Nothing to challenge yet."
              body="The challenge compares the recommendation against counterfactuals computed from the same evidence. Without a completed run there is no recommendation to test."
              action="Run labelled fixture"
              onAction={startFixture}
            />
          )}
        </div>
      </section>

      {/* CHAPTER — TEST */}
      <section id="test" className="scroll-mt-36 border-t border-line">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="type-kicker">Test · cinema test card</p>
              <p className="mt-2 max-w-xl text-sm text-mute">
                A bounded test of a cultural adjacency. Not a new identity for the cinema.
              </p>
            </div>
            {completed && card && (
              <button type="button" className="test-card-export" onClick={exportTestCard}>
                <span>Export test card</span>
                <small>PLAIN TEXT · .TXT</small>
              </button>
            )}
          </div>

          {completed && card && experimentDesign ? (
            <div className="grid gap-8 lg:grid-cols-12">
              <div className="border border-line p-5 lg:col-span-4">
                <p className="type-kicker text-amber">Pre-register before export</p>
                <div className="mt-4 grid gap-4">
                  {PREREG_FIELDS.map((entry) => (
                    <label key={entry.field} className="block">
                      <span className="field-label">{entry.label}</span>
                      <textarea
                        className="mt-2 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                        aria-label={`Cinema ${entry.field.replaceAll("_", " ")}`}
                        rows={entry.rows}
                        maxLength={2000}
                        value={experimentDesign[entry.field]}
                        onChange={(event) =>
                          setExperimentDesign((current) =>
                            updateTestDesign(current, card, entry.field, event.target.value),
                          )
                        }
                      />
                      {entry.note && <span className="caption mt-1 block">{entry.note}</span>}
                    </label>
                  ))}
                </div>
              </div>
              <div className="lg:col-span-8">
                <ChallengeSummary challenge={challenge} />
                <div className="mt-6">
                <TestCard
                  card={card}
                  design={experimentDesign}
                  editing={editingCard}
                  hypothesis={card.audience_hypothesis}
                  hypothesisNote="Returned cinema Test Card hypothesis"
                  onChange={(field: TestDesignField, value: string) =>
                    setExperimentDesign((current) => updateTestDesign(current, card, field, value))
                  }
                  onToggleEdit={() => setEditingCard((value) => !value)}
                  onExport={exportTestCard}
                />
                </div>
              </div>
            </div>
          ) : (
            <Locked
              title="No Test Card yet."
              body="The cinema Test Card is drafted from the programming direction and stays editable before it is exported. Export remains unavailable until a completed run returns one."
              action="Run labelled fixture"
              onAction={startFixture}
            />
          )}
        </div>
      </section>
    </div>
  );
}

function Locked({
  title,
  body,
  action,
  onAction,
}: {
  title: string;
  body: string;
  action: string;
  onAction: () => void;
}) {
  return (
    <div className="mt-6 flex flex-col items-start gap-6 border border-dashed border-line-strong p-8 md:flex-row md:items-center md:justify-between">
      <div className="max-w-xl">
        <p className="chip chip-warn">Requires completed analysis</p>
        <h3 className="font-display mt-4 text-3xl">{title}</h3>
        <p className="mt-3 text-sm leading-relaxed text-mute">{body}</p>
      </div>
      <button type="button" className="btn-ghost shrink-0" onClick={onAction}>
        {action}
        <ArrowRight size={14} />
      </button>
    </div>
  );
}
