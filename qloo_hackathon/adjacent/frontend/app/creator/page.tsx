"use client";

/**
 * Creator Studio — composition ported from the source ZIP (`pages/Creator.tsx`):
 * seven numbered chapters, a sticky journey rail, editorial intake with a
 * dossier aside, a stage ledger, the cultural fingerprint, the multiverse
 * arena, the decision brief, the paper Test Card and the archive.
 *
 * Everything result-bearing is bound to this application's real backend:
 * `createCreatorRun` / `createCreatorDemoRun`, the run SSE stream,
 * `buildPositioningMultiverse` over the returned cohorts, `saveExperiment`, the
 * observations/evaluations API and the optional provider-gated synthesis.
 * The ZIP's local timers and `saltLight*` fixtures are not used: the only
 * fixture that can appear is the backend's own labelled demo run.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Plus, Trash2 } from "lucide-react";
import {
  createCreatorDemoRun,
  createCreatorRun,
  getHealth,
  getRun,
  listExperiments,
  saveExperiment,
  streamRun,
  type BackendHealth,
  type CreatorRunRequest,
  type ExperimentRecord,
  type RunResponse,
  type SSEEvent,
} from "@/lib/api";
import type { AdjacentRunResult, InvestigationData, TraceRow } from "@/types/adjacent";
import { watchRunWithRecovery } from "@/lib/runRecovery";
import {
  createTestDesign,
  readSavedTestDesign,
  testDesignExportSections,
  updateTestDesign,
  type TestDesign,
  type TestDesignField,
} from "@/lib/testCardDesign";
import { downloadTextFile, formatTestCardText, safeTextFilename } from "@/lib/testCardExport";
import {
  DEFAULT_POSITIONING_POLICY,
  buildPositioningMultiverse,
  orderPositioningStrategies,
  readSavedPositioningSnapshot,
  type PositioningPolicy,
  type PositioningStrategy,
} from "@/lib/positioningArena";
import { buildFingerprintNodes, buildStageViews, filmTitleOf, stageStatusLabel } from "@/lib/nfData";
import { photos } from "@/lib/photos";
import { PhotoFrame } from "@/components/nf/PhotoFrame";
import { Field, TextArea, TextInput } from "@/components/nf/Field";
import { CulturalFingerprint } from "@/components/nf/CulturalFingerprint";
import { PositioningArena } from "@/components/nf/PositioningArena";
import { TestCard } from "@/components/nf/TestCard";
import { CreatorArchive } from "@/components/nf/CreatorArchive";
import { SynthesisPanel } from "@/components/nf/SynthesisPanel";
import { ComparablesAuditPanel } from "@/components/nf/ComparablesAudit";
import { WhyThisResult } from "@/components/nf/WhyThisResult";
import { ClaimChip, DataChip, RunChip } from "@/components/nf/Chips";
import { EvidenceReferences, EvidenceTraceLog } from "@/components/EvidenceTrace";
import { cn } from "@/lib/cn";

type SectionId = "film" | "investigation" | "fingerprint" | "arena" | "brief" | "test" | "archive";

const SECTIONS: { id: SectionId; label: string; needsRun: boolean }[] = [
  { id: "film", label: "Your film", needsRun: false },
  { id: "investigation", label: "Investigation", needsRun: true },
  { id: "fingerprint", label: "Cultural fingerprint", needsRun: true },
  { id: "arena", label: "Cultural multiverse", needsRun: true },
  { id: "brief", label: "Decision brief", needsRun: true },
  { id: "test", label: "Test card", needsRun: true },
  { id: "archive", label: "Archive", needsRun: false },
];

type Brief = {
  title: string;
  logline: string;
  genre: string;
  language: string;
  themes: string;
  comparables: { title: string; year: string }[];
  releaseGoal: string;
  location: string;
};

/** Pre-registration fields, in the exported and frozen order. */
const DESIGN_FIELDS: [string, TestDesignField][] = [
  ["Comparison protocol", "comparison_protocol"],
  ["Primary measure and denominator", "primary_measure"],
  ["Your decision rule / meaningful threshold", "decision_rule"],
  ["Observation window", "observation_window"],
];

/** Keep the UI counter and submit-time guard aligned. */
const MAX_CREATOR_THEMES = 5;

const emptyBrief: Brief = {
  title: "",
  logline: "",
  genre: "",
  language: "",
  themes: "",
  comparables: [{ title: "", year: "" }],
  releaseGoal: "",
  location: "",
};

/** The labelled backend fixture demo's own sample brief (never sent as live). */
const fixtureBrief: Brief = {
  title: "Neon Harbour",
  logline: "A dockside night-shift romance told in three silent vignettes.",
  genre: "drama",
  language: "English",
  themes: "isolation, night workers, coastal towns",
  comparables: [
    { title: "Chungking Express", year: "1994" },
    { title: "In the Mood for Love", year: "2000" },
  ],
  releaseGoal: "YouTube premiere after festival window",
  location: "Portland, Oregon",
};

export default function CreatorPage() {
  const [brief, setBrief] = useState<Brief>(emptyBrief);
  const [isFixtureMode, setIsFixtureMode] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [analysing, setAnalysing] = useState(false);
  const [requestMode, setRequestMode] = useState<"live" | "fixture" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);

  const [experimentDesign, setExperimentDesign] = useState<TestDesign | null>(null);
  const [editingCard, setEditingCard] = useState(false);
  const [saveState, setSaveState] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savingPlan, setSavingPlan] = useState(false);
  const [savedStrategyId, setSavedStrategyId] = useState<string | null>(null);
  const [savedSnapshot, setSavedSnapshot] = useState<Record<string, unknown> | null>(null);
  const [savedDesign, setSavedDesign] = useState<Record<TestDesignField, string | null> | null>(null);

  const [positioningPolicy, setPositioningPolicy] = useState<PositioningPolicy>({
    ...DEFAULT_POSITIONING_POLICY,
  });
  const [selectedPositioningId, setSelectedPositioningId] = useState<PositioningStrategy["id"] | null>(
    null,
  );

  const [activeSection, setActiveSection] = useState<SectionId>("film");

  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [experimentsLoading, setExperimentsLoading] = useState(false);
  const [experimentsError, setExperimentsError] = useState<string | null>(null);

  const stopStream = useRef<(() => void) | null>(null);
  const runGeneration = useRef(0);
  const activeRunId = useRef<string | null>(null);

  const result: AdjacentRunResult | null = (run?.result as AdjacentRunResult | null) ?? null;
  const validResult =
    result && (result.data_status === "measured" || result.data_status === "fixture") ? result : null;
  const completed = run?.status === "completed" && Boolean(validResult);
  const failed = run?.status === "failed";
  const insufficient = run?.status === "insufficient";
  const traceRows: TraceRow[] = run?.trace ?? [];
  const filmTitle = filmTitleOf(validResult, brief.title);

  const positioningMultiverse = useMemo(
    () =>
      completed && validResult
        ? buildPositioningMultiverse(validResult, traceRows, runId, run?.status ?? null)
        : null,
    [completed, validResult, traceRows, runId, run?.status],
  );
  const positioningOrdering = useMemo(
    () =>
      positioningMultiverse
        ? orderPositioningStrategies(positioningMultiverse, positioningPolicy)
        : null,
    [positioningMultiverse, positioningPolicy],
  );
  const selectedStrategy =
    positioningMultiverse?.strategies.find(
      (strategy) => strategy.id === selectedPositioningId && strategy.availability === "available",
    ) ?? null;

  const fingerprintNodes = useMemo(
    () => (completed ? buildFingerprintNodes(validResult, filmTitle, traceRows) : []),
    [completed, validResult, filmTitle, traceRows],
  );

  const stages = useMemo(
    () => buildStageViews({ started: Boolean(runId), status: run?.status ?? null, events }),
    [runId, run?.status, events],
  );

  useEffect(() => {
    if (!positioningMultiverse) return;
    setPositioningPolicy({ ...DEFAULT_POSITIONING_POLICY });
    const anchor = positioningMultiverse.strategies.find(
      (strategy) => strategy.id === "anchor" && strategy.availability === "available",
    );
    const firstAvailable = positioningMultiverse.strategies.find(
      (strategy) => strategy.availability === "available",
    );
    setSelectedPositioningId(anchor?.id ?? firstAvailable?.id ?? null);
  }, [positioningMultiverse]);

  useEffect(() => {
    const card = validResult?.test_card;
    if (!card) {
      setExperimentDesign(null);
      return;
    }
    setExperimentDesign(createTestDesign(card));
  }, [runId, validResult?.test_card]);

  useEffect(() => {
    const targets = SECTIONS.map((section) => document.getElementById(section.id)).filter(
      (element): element is HTMLElement => element instanceof HTMLElement,
    );
    if (!targets.length || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target instanceof HTMLElement) setActiveSection(visible.target.id as SectionId);
      },
      { rootMargin: "-25% 0px -60% 0px", threshold: [0, 0.2, 0.5] },
    );
    targets.forEach((target) => observer.observe(target));
    return () => observer.disconnect();
  }, [runId, run?.status]);

  const publicDemo = Boolean(backendHealth?.public_demo);
  const liveDisabled = Boolean(backendHealth?.public_demo && !backendHealth.live_creator_available);
  const enteredThemeCount = brief.themes
    .split(",")
    .map((theme) => theme.trim())
    .filter(Boolean).length;

  // Validation used to set a banner above the form without bringing it into
  // view. When a submit is rejected, move the feedback into the viewport so
  // the user doesn't mistake a local validation return for a dead button.
  useEffect(() => {
    if (!formError && !error) return;
    document.getElementById("creator-feedback")?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }, [formError, error]);

  const refreshExperiments = useCallback(async () => {
    if (publicDemo) return;
    setExperimentsLoading(true);
    setExperimentsError(null);
    try {
      setExperiments(await listExperiments());
    } catch (reason) {
      setExperimentsError(
        reason instanceof Error ? reason.message : "Could not load the research log.",
      );
    } finally {
      setExperimentsLoading(false);
    }
  }, [publicDemo]);

  useEffect(() => {
    void getHealth()
      .then((health) => {
        setBackendHealth(health);
      })
      .catch(() => setBackendHealth(null));
    return () => {
      runGeneration.current += 1;
      activeRunId.current = null;
      stopStream.current?.();
      stopStream.current = null;
    };
  }, []);

  useEffect(() => {
    if (backendHealth && !backendHealth.public_demo) void refreshExperiments();
  }, [backendHealth, refreshExperiments]);

  const watchRun = useCallback((id: string) => {
    const generation = ++runGeneration.current;
    activeRunId.current = id;
    stopStream.current?.();
    setRunId(id);
    setAnalysing(true);
    setEvents([]);
    setSaveState(null);
    setSaveError(null);
    setSavedStrategyId(null);

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
        if (["completed", "failed", "insufficient"].includes(response.status)) {
          setAnalysing(false);
          void refreshExperiments();
        }
      },
      onExhausted: () => {
        if (!isCurrent()) return;
        setError(
          "The stream disconnected and the run status could not be confirmed. Retry loading this run.",
        );
        setAnalysing(false);
      },
    });
  }, [refreshExperiments]);

  const cancelRunWatch = useCallback(() => {
    runGeneration.current += 1;
    activeRunId.current = null;
    stopStream.current?.();
    stopStream.current = null;
  }, []);

  const startDemoRun = useCallback(
    (payload?: CreatorRunRequest) => {
      cancelRunWatch();
      setError(null);
      setRun(null);
      setRunId(null);
      setSaveState(null);
      setSaveError(null);
      setIsFixtureMode(true);
      setRequestMode("fixture");
      setAnalysing(true);

      const params = new URLSearchParams(window.location.search);
      if (params.get("demo") !== "fixture") {
        params.set("demo", "fixture");
        const query = params.toString();
        window.history.replaceState({}, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
      }

      createCreatorDemoRun(payload)
        .then((response) => watchRun(response.run_id))
        .catch((reason: unknown) => {
          setError(
            reason instanceof Error ? reason.message : "Failed to start the labelled fixture run",
          );
          setAnalysing(false);
        });
    },
    [cancelRunWatch, watchRun],
  );

  // URL intent: the home page links to /creator?demo=fixture.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "fixture") {
      setBrief((current) => (current.title ? current : fixtureBrief));
      startDemoRun();
    }
    // Intentionally runs once for the initial URL intent.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function startLiveInvestigation() {
    setIsFixtureMode(false);
    if (!brief.title.trim()) {
      setFormError("A working title is required before a live investigation.");
      return;
    }
    const references = brief.comparables
      .map((row) => ({ title: row.title.trim(), year: row.year.trim() ? Number(row.year) : null }))
      .filter((row) => row.title);
    const themes = brief.themes
      .split(",")
      .map((theme) => theme.trim())
      .filter(Boolean);
    const badYear = brief.comparables.some(
      (row) =>
        row.year.trim() &&
        (!Number.isInteger(Number(row.year)) || Number(row.year) < 1888 || Number(row.year) > 2100),
    );
    if (badYear) {
      setFormError("Reference years must be between 1888 and 2100.");
      return;
    }
    if (references.length > 5) {
      setFormError("Use at most five reference works.");
      return;
    }
    if (themes.length > MAX_CREATOR_THEMES) {
      setFormError(`Use at most ${MAX_CREATOR_THEMES} themes.`);
      return;
    }
    if (themes.some((theme) => theme.length > 120)) {
      setFormError("Each theme must be 120 characters or fewer.");
      return;
    }
    if (references.some((reference) => reference.title.length > 160)) {
      setFormError("Each reference title must be 160 characters or fewer.");
      return;
    }
    if (references.length === 0 && themes.length === 0) {
      setFormError("Add at least one reference work or theme — the analysis needs cultural seeds.");
      return;
    }

    setFormError(null);
    setError(null);
    setNotice(null);
    cancelRunWatch();
    setRun(null);
    setRunId(null);
    setSaveState(null);
    setSaveError(null);
    setRequestMode("live");
    setAnalysing(true);

    const payload: CreatorRunRequest = {
      title: brief.title.trim(),
      logline: brief.logline.trim(),
      genre: brief.genre.trim(),
      language: brief.language.trim(),
      themes,
      references,
      release_goal: brief.releaseGoal.trim(),
      city: brief.location.trim(),
    };

    createCreatorRun(payload)
      .then((response) => watchRun(response.run_id))
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Failed to start the analysis");
        setAnalysing(false);
      });
  }

  function runFixture() {
    setFormError(null);
    setError(null);
    setNotice(null);
    setBrief((current) => (current.title ? current : fixtureBrief));
    startDemoRun({
      title: brief.title.trim() || fixtureBrief.title,
      logline: brief.logline.trim(),
      genre: brief.genre.trim(),
      language: brief.language.trim(),
      themes: brief.themes
        .split(",")
        .map((theme) => theme.trim())
        .filter(Boolean),
      references: brief.comparables
        .filter((row) => row.title.trim())
        .map((row) => ({ title: row.title.trim(), year: row.year.trim() ? Number(row.year) : null })),
      release_goal: brief.releaseGoal.trim(),
      city: brief.location.trim(),
    });
  }

  async function savePlan(source: "test-card" | "arena" = "test-card"): Promise<boolean> {
    if (!validResult || !runId) {
      setSaveError("A completed investigation is required before a plan can be saved.");
      return false;
    }
    if (publicDemo) {
      setSaveError(
        "Saving shared experiments is disabled in public-demo mode. This run remains temporary.",
      );
      return false;
    }
    const card = validResult.test_card;
    if (!card) {
      setSaveError("This run did not return a Test Card, so there is no plan to save.");
      return false;
    }

    setSavingPlan(true);
    setSaveError(null);
    setSaveState(null);
    try {
      const investigation = validResult.investigation as Record<string, unknown> | undefined;
      const investigationHypothesis = ((investigation?.hypotheses as Record<string, unknown> | undefined)
        ?.primary ?? null) as Record<string, unknown> | null;
      const investigationSummary = investigation
        ? {
            investigation_id: investigation.investigation_id,
            data_status: investigation.data_status,
            primary_hypothesis: investigationHypothesis?.statement ?? null,
            limitations: (investigation.limitations as string[]) ?? [],
            open_questions: (investigation.open_questions as string[]) ?? [],
          }
        : null;
      const investigationRefs =
        ((investigation?.provenance as Record<string, unknown> | undefined)?.call_ids ?? []) as string[];
      const frozenDesign = {
        comparison_protocol: experimentDesign?.comparison_protocol ?? card.comparison_protocol ?? null,
        primary_measure: experimentDesign?.primary_measure ?? card.primary_measure ?? null,
        decision_rule: experimentDesign?.decision_rule ?? card.decision_rule ?? null,
        observation_window: experimentDesign?.observation_window ?? card.observation_window ?? null,
      };
      const positioningSnapshot =
        positioningMultiverse && positioningOrdering && selectedStrategy
          ? {
              snapshot_version: "cultural-positioning-snapshot-v1",
              calculation_version: positioningMultiverse.calculation_version,
              source_run_id: runId,
              original_data_status: validResult.data_status,
              original_test_card: card,
              strategies: positioningMultiverse.strategies,
              selected_strategy_id: selectedStrategy.id,
              selected_strategy: selectedStrategy,
              policy: {
                formula_version: positioningOrdering.formula_version,
                values: positioningOrdering.policy,
                ordering: positioningOrdering.entries,
                notes: positioningOrdering.notes,
              },
              experiment_design: frozenDesign,
              limitations: positioningMultiverse.source_limitations,
            }
          : null;

      const response = await saveExperiment({
        request_id: `exp-${runId}`,
        film_title: filmTitle || brief.title,
        hypothesis: selectedStrategy?.falsifiable_hypothesis ?? card.audience_hypothesis,
        success_criteria: selectedStrategy
          ? "Evaluate only against the creator-selected primary measure and pre-set decision rule. Missing or non-comparable observations remain inconclusive."
          : card.success_criteria ?? "",
        observation_window: frozenDesign.observation_window ?? "",
        action_plan: selectedStrategy?.creative_direction ?? card.programming_direction,
        data_status: validResult.data_status,
        source_run_id: runId,
        source_bet: {
          ...((validResult.programme_bet ?? {}) as Record<string, unknown>),
          experiment_design: frozenDesign,
          ...(positioningSnapshot ? { cultural_multiverse_snapshot: positioningSnapshot } : {}),
        },
        provenance: (card.provenance ?? {}) as Record<string, unknown>,
        film_context: (validResult.film ?? {}) as Record<string, unknown>,
        ...(investigationSummary
          ? { investigation_summary: investigationSummary, evidence_refs: investigationRefs }
          : {}),
      });
      // Read the frozen decision back from the stored record, not from local state.
      setSavedSnapshot(readSavedPositioningSnapshot(response.experiment.source_bet));
      setSavedDesign(
        readSavedTestDesign(response.experiment.source_bet, response.experiment.observation_window),
      );
      if (selectedStrategy) setSavedStrategyId(selectedStrategy.id);
      setSaveState(
        response.duplicate
          ? "This run already has a saved decision — showing the original. Nothing was overwritten."
          : source === "arena"
            ? "Decision frozen: strategy, policy and experiment design saved as a planned experiment."
            : "Saved as a planned experiment. Record what actually happens in the archive.",
      );
      void refreshExperiments();
      return true;
    } catch (reason) {
      setSaveError(reason instanceof Error ? reason.message : "Could not save the plan");
      return false;
    } finally {
      setSavingPlan(false);
    }
  }

  function exportTestCard() {
    if (!validResult?.test_card) return;
    const card = validResult.test_card;
    const activeDesign = experimentDesign ?? createTestDesign(card);
    const text = formatTestCardText({
      title: selectedStrategy ? `${selectedStrategy.type} strategy · ${card.title}` : card.title,
      context: "FILM: " + (filmTitle || brief.title || "Unsaved brief"),
      dataStatus: validResult.data_status,
      sections: [
        ...(selectedStrategy
          ? [
              { label: "Selected cultural strategy", value: selectedStrategy.thesis },
              { label: "Creative direction", value: selectedStrategy.creative_direction },
              { label: "Falsifiable hypothesis", value: selectedStrategy.falsifiable_hypothesis },
              {
                label: "Strategy evidence",
                value: selectedStrategy.evidence_refs
                  .map((item) => `${item.description} Calls: ${item.call_ids.join(", ")}.`)
                  .join(" "),
              },
              {
                label: "Policy formula and priorities",
                value: positioningOrdering
                  ? `${positioningOrdering.formula_version}; fit=${positioningOrdering.policy.fit}, exploration=${positioningOrdering.policy.exploration}, breadth=${positioningOrdering.policy.breadth}. The preference index is not a prediction.`
                  : "Unavailable",
              },
              { label: "Strategy limitations", value: selectedStrategy.tradeoffs.join(" ") },
            ]
          : []),
        { label: "Programme context", value: card.programme_context },
        { label: "Audience hypothesis", value: card.audience_hypothesis },
        { label: "Cultural bridge", value: card.cultural_bridge },
        { label: "Geographic signal", value: card.geographic_signal },
        { label: "Positioning direction", value: card.programming_direction },
        { label: "Primary evidence", value: card.primary_evidence },
        { label: "Runner-up direction", value: card.runner_up },
        { label: "Observable success criteria", value: card.success_criteria },
        ...testDesignExportSections(activeDesign),
        { label: "Falsification condition", value: card.falsification_condition },
      ],
      provenance: {
        ...(card.provenance ?? {}),
        ...(selectedStrategy
          ? {
              selected_strategy_id: selectedStrategy.id,
              strategy_source_cohort_ids: selectedStrategy.source_cohort_ids.join(", "),
              strategy_supporting_call_ids:
                selectedStrategy.evidence_challenge.supporting_call_ids.join(", "),
            }
          : {}),
      },
      footerNote: `${
        validResult.data_status === "fixture"
          ? "Fixture demonstration, not a live provider result. "
          : ""
      }Cultural affinity is not a forecast of views, attendance, revenue, or audience demand. ${
        selectedStrategy?.tradeoffs.join(" ") ?? ""
      }`,
    });
    downloadTextFile(safeTextFilename(card.title) + ".txt", text);
    setNotice("Test card exported as plain text. A file was created in your browser.");
  }

  const card = validResult?.test_card ?? null;
  const bet = validResult?.programme_bet ?? null;
  const investigation = (validResult?.investigation ?? null) as InvestigationData | null;
  const showUnavailablePanels = (failed || insufficient) && !analysing;

  // A failed or insufficient run stays navigable so its honest "unavailable"
  // panel can be read, but a step is never offered before its evidence exists.
  const canInvestigate = result || (failed && !analysing);
  const canFingerprint = result?.cohorts || (failed && !analysing);
  const canBrief = result?.investigation || (failed && !analysing);
  const sectionAvailability: Partial<Record<SectionId, boolean>> = {
    investigation: Boolean(canInvestigate),
    fingerprint: Boolean(canFingerprint),
    arena: Boolean(positioningMultiverse),
    brief: Boolean(canBrief),
    test: Boolean(card),
  };

  return (
    <div className="bg-ink">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-end justify-between gap-4 px-4 py-8 md:px-8">
          <div>
            <p className="type-kicker">Creator Studio</p>
            <h1 className="font-display mt-2 text-4xl md:text-6xl">
              Position your film in its <span className="italic text-amber">cultural world.</span>
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <RunChip status={run?.status ?? (analysing ? "running" : "idle")} />
            {requestMode === "fixture" && <DataChip status="fixture" />}
            {validResult && <DataChip status={validResult.data_status} />}
          </div>
        </div>
      </header>

      <nav
        className="sticky top-[64px] z-40 border-b border-line bg-ink/95 backdrop-blur"
        aria-label="Creator journey"
      >
        <div className="mx-auto flex max-w-[1440px] gap-1 overflow-x-auto px-4 py-2 md:px-8">
          {SECTIONS.map((section, index) => {
            const enabled = !section.needsRun || sectionAvailability[section.id] !== false;
            const content = (
              <>
                <span className="text-amber">{String(index + 1).padStart(2, "0")}</span>
                {section.label}
              </>
            );
            return enabled ? (
              <button
                key={section.id}
                type="button"
                onClick={() =>
                  document
                    .getElementById(section.id)
                    ?.scrollIntoView({ behavior: "smooth", block: "start" })
                }
                aria-current={activeSection === section.id ? "true" : undefined}
                className={cn(
                  "flex shrink-0 items-center gap-2 border-b-2 px-3 py-2 font-mono text-[0.62rem] uppercase tracking-[0.14em] transition-colors",
                  activeSection === section.id
                    ? "border-amber text-paper"
                    : "border-transparent text-mute hover:text-paper-2",
                )}
              >
                {content}
              </button>
            ) : (
              <span
                key={section.id}
                aria-disabled="true"
                className="flex shrink-0 cursor-not-allowed items-center gap-2 border-b-2 border-transparent px-3 py-2 font-mono text-[0.62rem] uppercase tracking-[0.14em] text-dim opacity-60"
              >
                {content}
              </span>
            );
          })}
        </div>
      </nav>

      {publicDemo && (
        <div className="border-b border-amber/30 bg-amber/10">
          <p className="mx-auto max-w-[1440px] px-4 py-3 text-sm text-amber md:px-8">
            PUBLIC DEMO MODE ·{" "}
            {backendHealth?.live_creator_available
              ? "bounded live Creator requests are enabled; upstream Qloo may still fail honestly."
              : "live Creator requests are disabled on this deployment."}{" "}
            Shared experiments, synthesis and YouTube storage are unavailable; run records are
            temporary.
          </p>
        </div>
      )}

      {(notice || error || formError) && (
        <div id="creator-feedback" className="border-b border-amber/30 bg-amber/10" role="status" aria-live="polite">
          <p className="mx-auto max-w-[1440px] px-4 py-3 text-sm text-amber md:px-8">
            {formError ?? error ?? notice}
          </p>
        </div>
      )}

      {/* 01 — YOUR FILM */}
      <section id="film" className="scroll-mt-36 border-b border-line">
        <div className="mx-auto grid max-w-[1440px] gap-10 px-4 py-14 md:grid-cols-12 md:px-8">
          <div className="md:col-span-7">
            {isFixtureMode && (
              <div className="mb-6 border border-amber/40 bg-amber/10 px-4 py-3" role="status">
                <strong className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-amber">
                  FIXTURE DEMO MODE ACTIVE · OFFLINE DETERMINISTIC ANALYSIS
                </strong>
                <p className="mt-2 text-sm leading-relaxed text-paper-2">
                  Requests here run against the backend&apos;s labelled fixture evidence without
                  calling upstream Qloo. Results are never presented as live data.
                </p>
              </div>
            )}

            <div className="border border-line p-5 md:p-8">
              <p className="type-kicker">The film</p>
              <p className="mt-2 text-xs text-dim">
                Only the title is required. Everything else strengthens the evidence.
              </p>
              <div className="mt-8 space-y-7">
                <Field label="Working title *">
                  <TextInput
                    required
                    maxLength={160}
                    value={brief.title}
                    onChange={(event) => setBrief({ ...brief, title: event.target.value })}
                    placeholder="Neon Harbour"
                  />
                </Field>
                <Field
                  label="Logline"
                  hint="Used as context, never as a substitute for resolved entities."
                >
                  <TextArea
                    maxLength={2000}
                    value={brief.logline}
                    onChange={(event) => setBrief({ ...brief, logline: event.target.value })}
                    placeholder="A dockside night-shift romance told in three silent vignettes."
                  />
                </Field>
                <div className="grid gap-6 sm:grid-cols-2">
                  <Field label="Genre">
                    <TextInput
                      maxLength={120}
                      value={brief.genre}
                      onChange={(event) => setBrief({ ...brief, genre: event.target.value })}
                    />
                  </Field>
                  <Field label="Language">
                    <TextInput
                      maxLength={80}
                      value={brief.language}
                      onChange={(event) => setBrief({ ...brief, language: event.target.value })}
                    />
                  </Field>
                </div>
              </div>
            </div>

            <div className="mt-6 border border-line p-5 md:p-8">
              <p className="type-kicker">Cultural references</p>
              <div className="mt-8 space-y-7">
                <Field
                  label="Themes"
                  hint="Comma-separated concepts. Resolved as tags, never as extra film titles."
                >
                  <TextInput
                    maxLength={604}
                    value={brief.themes}
                    aria-invalid={enteredThemeCount > MAX_CREATOR_THEMES}
                    aria-describedby="creator-theme-count"
                    onChange={(event) => {
                      const value = event.target.value;
                      const count = value.split(",").map((theme) => theme.trim()).filter(Boolean).length;
                      setBrief({ ...brief, themes: value });
                      if (
                        count <= MAX_CREATOR_THEMES &&
                        formError === `Use at most ${MAX_CREATOR_THEMES} themes.`
                      ) {
                        setFormError(null);
                      }
                    }}
                    placeholder="isolation, night workers, coastal towns"
                  />
                  <p
                    id="creator-theme-count"
                    aria-live="polite"
                    className={cn(
                      "mt-2 text-xs",
                      enteredThemeCount > MAX_CREATOR_THEMES ? "text-warn" : "text-dim",
                    )}
                  >
                    {enteredThemeCount} / {MAX_CREATOR_THEMES} themes
                    {enteredThemeCount > MAX_CREATOR_THEMES
                      ? " · Remove one or more themes before analysing."
                      : ""}
                  </p>
                </Field>
                <div>
                  <span className="field-label">Comparable works</span>
                  <p className="mb-4 text-xs text-dim">
                    Title and year where known. Unresolved titles stay unresolved.
                  </p>
                  <ul className="space-y-3">
                    {brief.comparables.map((row, index) => (
                      <li key={index} className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_6rem_2.5rem]">
                        <TextInput
                          aria-label={`Comparable title ${index + 1}`}
                          maxLength={160}
                          placeholder="Chungking Express"
                          value={row.title}
                          onChange={(event) => {
                            const next = [...brief.comparables];
                            next[index] = { ...row, title: event.target.value };
                            setBrief({ ...brief, comparables: next });
                          }}
                        />
                        <TextInput
                          aria-label={`Year ${index + 1}`}
                          maxLength={4}
                          placeholder="1994"
                          inputMode="numeric"
                          value={row.year}
                          onChange={(event) => {
                            const next = [...brief.comparables];
                            next[index] = { ...row, year: event.target.value };
                            setBrief({ ...brief, comparables: next });
                          }}
                        />
                        <button
                          type="button"
                          className="flex h-10 items-center justify-center text-mute hover:text-blood"
                          aria-label={`Remove comparable ${index + 1}`}
                          onClick={() =>
                            setBrief({
                              ...brief,
                              comparables: brief.comparables.filter(
                                (_, rowIndex) => rowIndex !== index,
                              ),
                            })
                          }
                        >
                          <Trash2 size={15} />
                        </button>
                      </li>
                    ))}
                  </ul>
                  <button
                    type="button"
                    className="btn-ghost mt-4"
                    disabled={brief.comparables.length >= 5}
                    onClick={() =>
                      setBrief({
                        ...brief,
                        comparables:
                          brief.comparables.length < 5
                            ? [...brief.comparables, { title: "", year: "" }]
                            : brief.comparables,
                      })
                    }
                  >
                    <Plus size={14} />
                    {brief.comparables.length >= 5 ? "5 reference limit reached" : "Add reference"}
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-6 border border-line p-5 md:p-8">
              <p className="type-kicker">Release context</p>
              <div className="mt-8 grid gap-6 sm:grid-cols-2">
                <Field label="Release goal">
                  <TextInput
                    maxLength={300}
                    value={brief.releaseGoal}
                    onChange={(event) => setBrief({ ...brief, releaseGoal: event.target.value })}
                    placeholder="Festival, then limited theatrical"
                  />
                </Field>
                <Field
                  label="Location (optional)"
                  hint="Enables geography only when the run returns usable place data."
                >
                  <TextInput
                    maxLength={120}
                    value={brief.location}
                    onChange={(event) => setBrief({ ...brief, location: event.target.value })}
                    placeholder="Portland, Oregon"
                  />
                </Field>
              </div>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <button
                type="button"
                className="btn-primary"
                disabled={analysing || (!isFixtureMode && liveDisabled)}
                onClick={() => (isFixtureMode ? runFixture() : startLiveInvestigation())}
              >
                {analysing
                  ? "Analysing…"
                  : isFixtureMode
                    ? "Analyse cultural position (fixture demo)"
                    : liveDisabled
                      ? "Live Creator disabled in public demo"
                      : "Analyse cultural position"}
                <ArrowRight size={16} />
              </button>
              {isFixtureMode ? (
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={analysing}
                  onClick={() => setIsFixtureMode(false)}
                >
                  Switch to live analysis
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={analysing}
                  onClick={runFixture}
                >
                  View labelled fixture demo (offline)
                </button>
              )}
              <button type="button" className="btn-ghost" onClick={() => setBrief(fixtureBrief)}>
                Load sample brief
              </button>
            </div>
            <p className="caption mt-4">
              The fixture and the live path are separate requests. A failed live request never falls
              back to fixture data.
            </p>
          </div>

          <aside className="md:col-span-5">
            <PhotoFrame photo={photos.screenplay} className="aspect-[4/5]" />
            <div className="mt-6 border border-line p-5">
              <p className="type-kicker">Dossier summary</p>
              <dl className="mt-4 space-y-3 text-sm">
                <Row k="Title" v={brief.title || "—"} />
                <Row k="Genre / lang." v={`${brief.genre || "—"} · ${brief.language || "—"}`} />
                <Row
                  k="Comparables"
                  v={
                    brief.comparables
                      .filter((row) => row.title)
                      .map((row) => row.title)
                      .join(", ") || "—"
                  }
                />
                <Row k="Location" v={brief.location || "not set"} />
              </dl>
              <p className="caption mt-6">
                Live never becomes fixture silently. Fixture runs stay labelled at every layer.
              </p>
            </div>
          </aside>
        </div>
      </section>

      {/* 02 — INVESTIGATION */}
      <section id="investigation" className="scroll-mt-36 border-b border-line">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="type-kicker">02 · Investigation</p>
              <h2 className="font-display mt-2 text-3xl md:text-5xl">
                {!runId && "No run yet."}
                {analysing && "The room is working."}
                {completed && "Investigation complete."}
                {insufficient && "Not enough evidence."}
                {failed && "The run failed."}
                {run?.status === "cancelled" && "The run was interrupted."}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <RunChip status={run?.status ?? (analysing ? "running" : "idle")} />
              {validResult && <DataChip status={validResult.data_status} />}
              {runId && <span className="caption">Run {runId}</span>}
            </div>
          </div>

          {requestMode === "fixture" && (
            <p className="mt-3 text-sm text-amber">
              FIXTURE DEMONSTRATION — NOT A LIVE QLOO ANALYSIS · no live Qloo calls are being made.
            </p>
          )}

          <ol className="mt-10 grid gap-x-8 md:grid-cols-2">
            {stages.map((stage) => (
              <li key={stage.id} className="grid grid-cols-[5.5rem_1fr] gap-4 border-t border-line py-4">
                <span
                  className={cn(
                    "font-mono text-[0.62rem] tracking-[0.14em]",
                    stage.state === "now" && "text-amber",
                    stage.state === "done" && "text-sage",
                    stage.state === "wait" && "text-dim",
                    stage.state === "skipped" && "text-blood",
                  )}
                >
                  {stageStatusLabel(stage.state)}
                </span>
                <div>
                  <p className="text-paper">{stage.label}</p>
                  <p className="mt-1 text-sm text-mute">{stage.detail}</p>
                </div>
              </li>
            ))}
          </ol>

          {analysing && (
            <p className="mt-6 text-sm text-mute" role="status" aria-live="polite">
              Waiting for the backend to report progress. Stages mark the first unobserved step as
              current; the backend does not stream a per-stage phase.
            </p>
          )}

          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            <div className="border border-line p-5">
              <p className="type-kicker">Run status</p>
              <dl className="mt-4 space-y-2 text-sm">
                <Row k="Status" v={run?.status ?? "idle"} />
                <Row k="Data status" v={validResult?.data_status ?? "not returned"} />
                <Row k="Stop reason" v={run?.stop_reason ?? "—"} />
                <Row k="Qloo calls" v={String(validResult?.evidence?.qloo_calls ?? "—")} />
                <Row k="Trace rows" v={String(validResult?.evidence?.trace_rows ?? traceRows.length)} />
              </dl>
              {run?.stop_message && (
                <p className="mt-4 text-sm leading-relaxed text-paper-2">{run.stop_message}</p>
              )}
              {(failed || insufficient || run?.status === "cancelled") && (
                <p className="mt-4 text-sm leading-relaxed text-mute">
                  Failure is a legitimate terminal state. Nothing was substituted, and no fixture
                  result was promoted to a measured one.
                </p>
              )}
            </div>

            <div className="border border-line p-5">
              <p className="type-kicker">Recorded trace</p>
              <p className="mt-2 text-xs leading-relaxed text-mute">
                Provider calls are recorded server-side with redacted parameters. {events.length}{" "}
                live event(s) received.
              </p>
              {traceRows.length > 0 ? (
                <div className="mt-3 max-h-[320px] overflow-auto pr-1">
                  <EvidenceTraceLog rows={traceRows} scope="creator-run" />
                </div>
              ) : (
                <p className="mt-3 text-sm text-mute">
                  No trace rows are attached yet. An empty trace is not a successful call record.
                </p>
              )}
            </div>
          </div>

          {error && (
            <div role="alert" className="mt-6 border border-blood/40 bg-blood/10 p-4">
              <p className="text-sm leading-relaxed text-paper-2">{error}</p>
              {runId && (
                <button
                  type="button"
                  className="btn-ghost mt-3"
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

          {showUnavailablePanels && (
            <section
              id="analysis"
              aria-labelledby="analysis-unavailable-title"
              className="mt-8 border border-blood/40 bg-blood/5 p-5"
            >
              <h3 id="analysis-unavailable-title" className="font-display text-2xl">
                Investigation unavailable
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-paper-2">
                The run failed before a structured investigation could be produced. No findings or
                hypotheses are being inferred from a failed run. You can retry the analysis or run
                the labelled fixture deliberately.
              </p>
            </section>
          )}
        </div>
      </section>

      {/* 03 — CULTURAL FINGERPRINT */}
      <section className="scroll-mt-36 border-b border-line">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="type-kicker">03 · Cultural fingerprint</p>
              <h2 className="font-display mt-2 text-3xl md:text-5xl">{filmTitle || "Your film"}</h2>
            </div>
            {validResult && <DataChip status={validResult.data_status} />}
          </div>

          {completed ? (
            <div id="fingerprint">
              <CulturalFingerprint
                nodes={fingerprintNodes}
                filmTitle={filmTitle || "Your film"}
                dataStatus={validResult?.data_status}
              />

              {(validResult?.cohorts.ranked.length ?? 0) > 0 && (
                <div className="mt-10 border border-line p-5 md:p-6">
                  <p className="type-kicker">Cohort members · provider attribution</p>
                  <p className="mt-2 max-w-2xl text-xs leading-relaxed text-mute">
                    Member affinities are the scores this run actually returned. Qloo input
                    attribution is provider-reported contribution weight, not causal effects or
                    audience-size evidence. A member without attribution is unknown rather than
                    absent — missing attribution is not a zero score.
                  </p>
                  <div className="mt-5 grid gap-6 md:grid-cols-2">
                    {validResult?.cohorts.ranked.slice(0, 2).map((cohort) => (
                      <div key={cohort.cohort_id}>
                        <p className="font-display text-xl">
                          {cohort.domain.replace("urn:entity:", "")}
                        </p>
                        <p className="caption mt-1">
                          {cohort.member_count} members · mean affinity{" "}
                          {typeof cohort.score?.mean_affinity === "number"
                            ? cohort.score.mean_affinity.toFixed(2)
                            : "—"}
                        </p>
                        <ul className="mt-3 space-y-2">
                          {cohort.members.slice(0, 5).map((member) => (
                            <li key={member.entity_id} className="border-t border-line pt-2 text-sm">
                              <div className="flex items-baseline justify-between gap-3">
                                <span className="text-paper-2">
                                  {member.name ?? member.entity_id}
                                </span>
                                <span className="font-mono text-[0.62rem] text-dim">
                                  {typeof member.affinity === "number"
                                    ? member.affinity.toFixed(2)
                                    : "—"}
                                  {member.band ? ` · ${member.band}` : ""}
                                </span>
                              </div>
                              {(member.qloo_attributions?.length ?? 0) > 0 ? (
                                <details className="mt-1">
                                  <summary className="cursor-pointer font-mono text-[0.58rem] uppercase tracking-[0.12em] text-amber">
                                    QLOO INPUT ATTRIBUTION · {member.qloo_attributions?.length}{" "}
                                    SEED(S) ·{" "}
                                    {member.qloo_attribution_origin === "bounded"
                                      ? `BOUNDED FOLLOW-UP · SCORE CALL ${member.call_id ?? "UNAVAILABLE"}`
                                      : `SCORE CALL ${member.call_id ?? "UNAVAILABLE"}`}
                                  </summary>
                                  <ul className="mt-1 space-y-1">
                                    {member.qloo_attributions?.map((attribution) => (
                                      <li
                                        key={attribution.entity_id}
                                        className="font-mono text-[0.58rem] text-mute"
                                      >
                                        {attribution.entity_id} · WEIGHT{" "}
                                        {attribution.score.toFixed(3)}
                                      </li>
                                    ))}
                                  </ul>
                                </details>
                              ) : (
                                <p className="mt-1 font-mono text-[0.58rem] uppercase tracking-[0.12em] text-dim">
                                  {member.qloo_attribution_status === "unsupported"
                                    ? "OPTIONAL QLOO EXPLAINABILITY UNSUPPORTED · CORE SCORE KEPT · SCORE CALL "
                                    : "NO ATTRIBUTION RETURNED · ABSENCE IS NOT ZERO · SCORE CALL "}
                                  {member.call_id ?? "UNAVAILABLE"}
                                </p>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {(validResult?.cohorts.ranked.length ?? 0) > 0 && (
                <WhyThisResult
                  members={validResult?.cohorts.ranked[0]?.members}
                  programme={validResult?.programme}
                  bounded={validResult?.evidence?.bounded_attribution}
                />
              )}

              <ComparablesAuditPanel audit={validResult?.comparables_audit} />
            </div>
          ) : (
            <div
              id="fingerprint"
              role="region"
              aria-labelledby="fingerprint-unavailable-title"
              className="border border-dashed border-line-strong p-8"
            >
              <span className="chip chip-warn">Requires completed analysis</span>
              <h3 id="fingerprint-unavailable-title" className="font-display mt-4 text-3xl">
                The fingerprint waits for evidence.
              </h3>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                A fingerprint requires verified cultural cohorts. A completed investigation places
                this film at the centre with the cohorts it actually returned — no substitute or fixture fingerprint is shown before then.
              </p>
              <button
                type="button"
                className="btn-ghost mt-5"
                onClick={() =>
                  document
                    .getElementById("investigation")
                    ?.scrollIntoView({ behavior: "smooth", block: "start" })
                }
              >
                Go to investigation
                <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>
      </section>

      {/* 04 — CULTURAL MULTIVERSE / POSITIONING ARENA */}
      <section id="arena" className="scroll-mt-36 border-b border-line bg-ink-3/40">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="type-kicker">04 · Cultural multiverse</p>
              <h2 className="font-display mt-2 text-3xl md:text-5xl">
                Compare defensible directions.
              </h2>
            </div>
            <p className="max-w-md text-sm leading-relaxed text-mute">
              Anchor, Bridge and Frontier are derived from this completed run only. A direction the
              evidence cannot support is shown as unavailable rather than written into the stage.
            </p>
          </div>

          {completed && positioningMultiverse && positioningOrdering ? (
            <PositioningArena
              multiverse={positioningMultiverse}
              policy={positioningPolicy}
              ordering={positioningOrdering}
              selectedId={selectedPositioningId}
              onPolicyChange={setPositioningPolicy}
              onSelect={(strategyId) => {
                setSelectedPositioningId(strategyId);
                const strategy = positioningMultiverse.strategies.find(
                  (item) => item.id === strategyId,
                );
                if (strategy?.availability === "available") setExperimentDesign(strategy.suggested_test);
              }}
              experimentDesign={experimentDesign}
              sourceLabel={filmTitle}
              freeze={{
                busy: savingPlan,
                disabledReason: selectedStrategy
                  ? null
                  : "Select a strategy that is available in this run before freezing a decision.",
                message: saveState ?? saveError,
                savedStrategyId,
                onSave: () => {
                  void savePlan("arena");
                },
              }}
            />
          ) : (
            <div className="border border-dashed border-line-strong p-8">
              <span className="chip chip-warn">Requires completed analysis</span>
              <h3 className="font-display mt-4 text-3xl">
                {showUnavailablePanels
                  ? "The arena needs a completed run."
                  : "The multiverse opens after a run."}
              </h3>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                Strategies are computed from ranked cohorts returned by your investigation. Without
                that evidence there is nothing to compare, and no illustrative strategy is shown in
                its place.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* 05 — DECISION BRIEF */}
      <section className="scroll-mt-36 border-b border-line">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <p className="type-kicker">05 · Decision brief</p>

          {completed && (bet || investigation) ? (
            <div id="brief" className="mt-6 grid gap-10 lg:grid-cols-12">
              <div className="lg:col-span-7">
                <ClaimChip kind="HYPOTHESIS" />
                <h2 className="font-display mt-6 text-3xl leading-[1.05] md:text-5xl">
                  {investigation?.hypotheses.primary?.statement ??
                    (bet
                      ? `The ${bet.primary.domain.replace("urn:entity:", "")} world — via ${bet.primary.cohort_name}`
                      : "No supported hypothesis was returned.")}
                </h2>
                {bet && (
                  <>
                    <p className="mt-6 text-sm leading-relaxed text-paper-2">{bet.why}</p>
                    <p className="mt-4 font-mono text-[0.65rem] text-dim">
                      {bet.primary.member_count} entities
                      {typeof bet.primary.mean_affinity === "number"
                        ? ` · mean affinity ${bet.primary.mean_affinity.toFixed(2)}`
                        : " · no mean affinity"}
                      {bet.primary.call_id ? ` · call ${bet.primary.call_id}` : ""}
                      {` · data status ${String(bet.data_status).toUpperCase()}`}
                    </p>
                  </>
                )}
                {investigation?.hypotheses.primary && (
                  <div className="mt-5">
                    <p className="caption">Hypothesis evidence</p>
                    <EvidenceReferences
                      refs={investigation.hypotheses.primary.evidence_refs ?? []}
                      traceRows={traceRows}
                      scope="decision-brief"
                    />
                  </div>
                )}
                {bet?.cultural_bridge && (
                  <p className="mt-5 text-sm leading-relaxed text-paper-2">
                    <span className="text-amber">Bridge · </span>
                    {bet.cultural_bridge}
                  </p>
                )}
                {bet?.programming_direction && (
                  <p className="mt-3 text-sm leading-relaxed text-paper-2">
                    <span className="text-amber">Direction · </span>
                    {bet.programming_direction}
                  </p>
                )}
                {bet?.geographic_signal && (
                  <p className="mt-3 text-sm leading-relaxed text-mute">{bet.geographic_signal}</p>
                )}
                {bet?.falsification_condition && (
                  <div className="mt-6 border border-blood/40 bg-blood/10 p-4">
                    <p className="caption text-warn">Falsification condition</p>
                    <p className="mt-2 text-sm leading-relaxed text-paper-2">
                      {bet.falsification_condition}
                    </p>
                  </div>
                )}
                {investigation?.hypotheses.alternatives.map((alternative, index) => (
                  <p
                    key={`${alternative.statement}-${index}`}
                    className="mt-4 text-sm leading-relaxed text-mute"
                  >
                    <span className="text-amber">Alternative · </span>
                    {alternative.statement}
                  </p>
                ))}
              </div>

              <div className="lg:col-span-5">
                <PhotoFrame photo={photos.analogDesk} className="aspect-[4/5]" />
                <div className="mt-6 border border-line p-5">
                  <p className="type-kicker">Limitations</p>
                  <ul className="mt-4 space-y-3">
                    {(investigation?.limitations?.length ?? 0) > 0 ? (
                      investigation?.limitations.map((limitation, index) => (
                        <li
                          key={`${limitation}-${index}`}
                          className="text-sm leading-relaxed text-mute"
                        >
                          {limitation}
                        </li>
                      ))
                    ) : (
                      <li className="text-sm leading-relaxed text-mute">
                        No limitations were recorded in this investigation.
                      </li>
                    )}
                    {bet?.rejected_candidates?.map((candidate) => (
                      <li key={candidate.cohort_id} className="text-sm leading-relaxed text-mute">
                        Rejected · {candidate.domain.replace("urn:entity:", "")} —{" "}
                        {candidate.reason}
                      </li>
                    ))}
                  </ul>
                  <p className="caption mt-5">Subject · {filmTitle || "—"}</p>
                </div>
                {(investigation?.open_questions?.length ?? 0) > 0 && (
                  <div className="mt-6 border border-line p-5">
                    <p className="type-kicker">Open questions</p>
                    <ul className="mt-3 space-y-2">
                      {investigation?.open_questions.map((question, index) => (
                        <li
                          key={`${question}-${index}`}
                          className="text-sm leading-relaxed text-mute"
                        >
                          {question}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {investigation && runId && !publicDemo && (
                <div className="lg:col-span-12">
                  <SynthesisPanel
                    runId={runId}
                    filmTitle={filmTitle || brief.title}
                    investigation={investigation}
                    traceRows={traceRows}
                    onSaved={(message) => {
                      setSaveState(message);
                      void refreshExperiments();
                    }}
                  />
                </div>
              )}
            </div>
          ) : (
            <div
              id="brief"
              role="region"
              aria-labelledby="brief-unavailable-title"
              className="mt-6 border border-dashed border-line-strong p-8"
            >
              <span className="chip chip-warn">Requires completed analysis</span>
              <h3 id="brief-unavailable-title" className="font-display mt-4 text-3xl">
                {showUnavailablePanels
                  ? "The decision brief is unavailable."
                  : "The Programme Bet needs a run."}
              </h3>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                The decision brief depends on the structured investigation above. An interpretation
                is written over the evidence that produced it; without that evidence there is
                nothing to interpret, and nothing is invented to fill the space.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* 06 — TEST CARD */}
      <section id="test" className="scroll-mt-36 border-b border-line">
        <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="type-kicker">06 · Test card</p>
              <h2 className="font-display mt-2 text-3xl md:text-5xl">A plan, not a result.</h2>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="btn-primary"
                disabled={!completed || !card || savingPlan}
                onClick={() => void savePlan("test-card")}
                title={
                  !card
                    ? "Requires a completed investigation with a returned Test Card"
                    : "Save a planned experiment"
                }
              >
                {savingPlan ? "Saving…" : "Save planned experiment"}
              </button>
              {completed && card && (
                <button type="button" className="test-card-export" onClick={exportTestCard}>
                  <span>Export test card</span>
                  <small>PLAIN TEXT · .TXT</small>
                </button>
              )}
            </div>
          </div>

          {(saveState || saveError) && (
            <p
              role={saveError ? "alert" : "status"}
              aria-live="polite"
              className={cn("mb-6 text-sm", saveError ? "text-warn" : "text-amber")}
            >
              {saveError ?? saveState}
            </p>
          )}

          {completed && card && experimentDesign ? (
            <>
              <div className="mb-8 border border-amber/25 bg-amber/5 p-5">
                <p className="type-kicker text-amber">PERSONALISE THE TEST BEFORE SAVING</p>
                <p className="mt-2 max-w-3xl text-sm leading-relaxed text-paper-2">
                  These are starting prompts, not a completed experiment. Replace them with your
                  actual comparison, one measure you can collect, your decision threshold and
                  observation window. Your edits are included in the export and in a newly saved snapshot; saving does not execute the test.
                </p>
                <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                  {DESIGN_FIELDS.map(([label, field]) => (
                    <div key={field} className="border-t border-line pt-2">
                      <dt className="caption">{label}</dt>
                      <dd className="mt-1 text-sm leading-relaxed text-mute">
                        {experimentDesign[field] || "— not yet written —"}
                      </dd>
                    </div>
                  ))}
                </dl>
                <p className="caption mt-4">
                  Saved test design · snapshot · not executed. Edit the card to change these values
                  before exporting or saving again.
                </p>
              </div>

              <TestCard
                card={card}
                design={experimentDesign}
                editing={editingCard}
                hypothesis={selectedStrategy?.falsifiable_hypothesis ?? card.audience_hypothesis}
                hypothesisNote={
                  selectedStrategy
                    ? `Selected strategy · ${selectedStrategy.type} · falsifiable hypothesis`
                    : "Returned Test Card hypothesis"
                }
                onChange={(field: TestDesignField, value: string) =>
                  setExperimentDesign((current) => updateTestDesign(current, card, field, value))
                }
                onToggleEdit={() => setEditingCard((value) => !value)}
                onExport={exportTestCard}
              />

              {savedDesign && (
                <div className="mt-8 border border-line p-5">
                  <p className="type-kicker">FROZEN CULTURAL POSITIONING</p>
                  <p className="mt-2 text-xs leading-relaxed text-mute">
                    Read back from the stored experiment record. This is the plan that was frozen —
                    a snapshot, not an executed experiment and not a result.
                  </p>
                  <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                    {DESIGN_FIELDS.map(([label, field]) => (
                      <div key={field} className="border-t border-line pt-2">
                        <dt className="caption">SAVED TEST DESIGN · {label}</dt>
                        <dd className="mt-1 text-sm leading-relaxed text-paper-2">
                          {savedDesign[field] ?? "— not recorded —"}
                        </dd>
                      </div>
                    ))}
                  </dl>
                  {savedSnapshot && (
                    <p className="caption mt-4">
                      Selected strategy ·{" "}
                      {typeof savedSnapshot.selected_strategy_id === "string"
                        ? savedSnapshot.selected_strategy_id
                        : "—"}{" "}
                      · calculation{" "}
                      {typeof savedSnapshot.calculation_version === "string"
                        ? savedSnapshot.calculation_version
                        : "—"}
                    </p>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="border border-dashed border-line-strong p-8">
              <span className="chip chip-warn">Requires completed analysis</span>
              <h3 className="font-display mt-4 text-3xl">No card to edit yet.</h3>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                The Test Card is drafted from a completed investigation, then yours to edit and
                export. Saving a plan never means the experiment has run.
              </p>
            </div>
          )}
        </div>
      </section>

      <CreatorArchive
        experiments={experiments}
        loading={experimentsLoading}
        error={experimentsError}
        onReload={() => void refreshExperiments()}
        publicDemo={publicDemo}
        liveFacetsUnavailable={publicDemo}
      />
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-line pb-2">
      <dt className="caption">{k}</dt>
      <dd className="text-right text-paper-2">{v}</dd>
    </div>
  );
}
