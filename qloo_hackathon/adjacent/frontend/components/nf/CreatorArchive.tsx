"use client";

/**
 * Creator Archive — the saved research log ported from the source ZIP's
 * `pages/Creator.tsx` (chapter seven) into this application's real experiment
 * API.
 *
 * Nothing here is simulated: plans are the rows returned by `/experiments`,
 * observations and evaluations are append-only records the creator writes,
 * YouTube analytics are fetched server-side, and the frozen strategy / test
 * design are read back from the stored `source_bet` snapshot. An evaluation is
 * never auto-filled, and an empty observation list is never rendered as zero.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, ChevronDown, RefreshCw } from "lucide-react";
import {
  addEvaluation,
  addObservation,
  beginYouTubeAuthorization,
  disconnectYouTube,
  getExperiment,
  getRun,
  recordYouTubeObservation,
  youtubeStatus,
  youtubeVideos,
  type EvaluationRecord,
  type ExperimentRecord,
  type ObservationRecord,
  type YouTubeStatus,
  type YouTubeVideo,
} from "@/lib/api";
import type { TraceRow } from "@/types/adjacent";
import { readSavedPositioningSnapshot } from "@/lib/positioningArena";
import { readSavedTestDesign } from "@/lib/testCardDesign";
import { EvidenceReferences, EvidenceTraceLog } from "@/components/EvidenceTrace";
import { cn } from "@/lib/cn";

type Detail = {
  experiment: ExperimentRecord;
  observations: ObservationRecord[];
  evaluations: EvaluationRecord[];
};

const DESIGN_ROWS = [
  ["Comparison protocol", "comparison_protocol"],
  ["Primary measure and denominator", "primary_measure"],
  ["Decision rule", "decision_rule"],
  ["Observation window", "observation_window"],
] as const;

export function CreatorArchive({
  experiments,
  loading,
  error,
  onReload,
  publicDemo,
  liveFacetsUnavailable,
}: {
  experiments: ExperimentRecord[];
  loading: boolean;
  error: string | null;
  onReload: () => void;
  publicDemo: boolean;
  liveFacetsUnavailable: boolean;
}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const detailRequest = useRef(0);

  const openExperiment = useCallback(async (experimentId: string) => {
    setOpenId((current) => (current === experimentId ? null : experimentId));
    setDetail(null);
    setDetailError(null);
    const requestId = ++detailRequest.current;
    setDetailLoading(true);
    try {
      const response = await getExperiment(experimentId);
      if (requestId === detailRequest.current) setDetail(response);
    } catch (err) {
      if (requestId === detailRequest.current) {
        setDetailError(err instanceof Error ? err.message : "Could not load this experiment.");
      }
    } finally {
      if (requestId === detailRequest.current) setDetailLoading(false);
    }
  }, []);

  async function refreshDetail(experimentId: string) {
    const response = await getExperiment(experimentId);
    setDetail(response);
    onReload();
  }

  return (
    <section id="archive" className="scroll-mt-36 border-b border-line">
      <div className="mx-auto max-w-[1440px] px-4 py-14 md:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="type-kicker">07 · Archive</p>
            <h2 className="font-display mt-2 text-3xl md:text-5xl">Planned, observed, concluded.</h2>
          </div>
          <button type="button" className="btn-ghost" onClick={onReload} disabled={loading}>
            <RefreshCw size={14} />
            {loading ? "Refreshing…" : "Refresh archive"}
          </button>
        </div>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-mute">
          Saving a plan does not execute it. Observations are recorded after release; evaluations
          are append-only and later evaluations supersede earlier ones without deleting them.
        </p>

        {publicDemo && (
          <div role="status" className="mt-6 border border-amber/30 bg-amber/10 p-5">
            <p className="type-kicker text-amber">Public demo</p>
            <p className="mt-2 text-sm leading-relaxed text-paper-2">
              Shared experiment history is intentionally unavailable to anonymous visitors; no
              shared records are read or written here. Run the backend as its operator to use the
              archive.
            </p>
          </div>
        )}

        {error && (
          <div role="alert" className="mt-6 border border-blood/40 bg-blood/10 p-4">
            <p className="text-sm leading-relaxed text-paper-2">
              The Research Log could not be loaded.{" "}
              {experiments.length > 0
                ? "Showing the last successfully loaded records."
                : "Saved records have not been checked, so this is not an empty-log result."}{" "}
              {error}
            </p>
            <button type="button" className="btn-ghost mt-3" onClick={onReload} disabled={loading}>
              {loading ? "Retrying…" : "Retry Research Log"}
            </button>
          </div>
        )}

        {loading && experiments.length === 0 && (
          <p role="status" aria-live="polite" className="mt-6 text-sm text-mute">
            Loading saved experiments…
          </p>
        )}

        {!publicDemo && !loading && !error && experiments.length === 0 && (
          <div className="mt-6 border border-dashed border-line-strong p-8">
            <span className="chip chip-warn">Nothing saved yet</span>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
              No saved experiments were returned. Run an analysis (or the labelled fixture demo) and
              explicitly save its test card as a planned experiment. Saving a plan does not execute
              it.
            </p>
          </div>
        )}

        <ul className="mt-8 grid gap-3">
          {experiments.map((experiment) => {
            const open = openId === experiment.experiment_id;
            return (
              <li key={experiment.experiment_id} className="border border-line">
                <button
                  type="button"
                  onClick={() => void openExperiment(experiment.experiment_id)}
                  aria-expanded={open}
                  aria-controls={`archive-detail-${experiment.experiment_id}`}
                  className="flex w-full flex-wrap items-baseline justify-between gap-3 px-4 py-3 text-left"
                >
                  <span className="font-display text-xl text-paper">{experiment.film_title}</span>
                  <span className="flex items-center gap-3 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-dim">
                    {String(experiment.data_status).toUpperCase()} ·{" "}
                    {experiment.latest_evaluation ?? "NO EVALUATION YET"} ·{" "}
                    {experiment.observation_count ?? 0} OBSERVATION(S)
                    <ChevronDown size={14} className={cn("transition-transform", open && "rotate-180")} />
                  </span>
                </button>
                <p className="border-t border-line px-4 py-2 text-xs leading-relaxed text-mute">
                  {experiment.hypothesis.slice(0, 180)}
                  {experiment.hypothesis.length > 180 ? "…" : ""}
                </p>
                <div id={`archive-detail-${experiment.experiment_id}`} hidden={!open}>
                  {open && (
                    <div className="border-t border-line px-4 py-5">
                      {detailLoading && (
                        <p role="status" className="text-sm text-mute">
                          Loading saved decision, observations and evaluation history…
                        </p>
                      )}
                      {detailError && (
                        <div role="alert" className="text-sm text-warn">
                          Could not load this experiment: {detailError}
                          <button
                            type="button"
                            className="btn-ghost mt-3"
                            onClick={() => void openExperiment(experiment.experiment_id)}
                          >
                            Retry loading this experiment
                          </button>
                        </div>
                      )}
                      {detail && detail.experiment.experiment_id === experiment.experiment_id && (
                        <ExperimentDetail
                          key={experiment.experiment_id}
                          detail={detail}
                          onChanged={() => refreshDetail(experiment.experiment_id)}
                          liveFacetsUnavailable={liveFacetsUnavailable}
                        />
                      )}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

function ExperimentDetail({
  detail,
  onChanged,
  liveFacetsUnavailable,
}: {
  detail: Detail;
  onChanged: () => Promise<void>;
  liveFacetsUnavailable: boolean;
}) {
  const { experiment, observations, evaluations } = detail;
  const savedDesign = readSavedTestDesign(experiment.source_bet, experiment.observation_window);
  const savedPositioning = readSavedPositioningSnapshot(experiment.source_bet);
  const savedStrategy =
    savedPositioning?.selected_strategy && typeof savedPositioning.selected_strategy === "object"
      ? (savedPositioning.selected_strategy as Record<string, unknown>)
      : null;
  const savedStrategies = Array.isArray(savedPositioning?.strategies)
    ? savedPositioning.strategies.filter(
        (strategy): strategy is Record<string, unknown> =>
          Boolean(strategy) && typeof strategy === "object" && !Array.isArray(strategy),
      )
    : [];
  const savedPolicy =
    savedPositioning?.policy && typeof savedPositioning.policy === "object"
      ? (savedPositioning.policy as Record<string, unknown>)
      : null;
  const savedPolicyValues =
    savedPolicy?.values && typeof savedPolicy.values === "object"
      ? (savedPolicy.values as Record<string, unknown>)
      : null;

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Source-run trace
  const [sourceTrace, setSourceTrace] = useState<TraceRow[]>([]);
  const [sourceTraceLoading, setSourceTraceLoading] = useState(Boolean(experiment.source_run_id));
  const [sourceTraceError, setSourceTraceError] = useState<string | null>(
    experiment.source_run_id ? null : "No source run reference was saved with this experiment.",
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
      const response = await getRun(experiment.source_run_id);
      if (requestId === sourceTraceRequest.current) setSourceTrace(response.trace ?? []);
    } catch (err) {
      if (requestId === sourceTraceRequest.current) {
        setSourceTraceError(
          err instanceof Error ? err.message : "Could not load the source run trace",
        );
      }
    } finally {
      if (requestId === sourceTraceRequest.current) setSourceTraceLoading(false);
    }
  }, [experiment.source_run_id]);

  useEffect(() => {
    void loadSourceTrace();
    return () => {
      sourceTraceRequest.current += 1;
    };
  }, [loadSourceTrace]);

  // Observation form
  const [kind, setKind] = useState("ANALYTICS");
  const [measurement, setMeasurement] = useState("OBSERVED");
  const [observedOn, setObservedOn] = useState("");
  const [views, setViews] = useState("");
  const [watchMinutes, setWatchMinutes] = useState("");
  const [interpretation, setInterpretation] = useState("");
  const [limitations, setLimitations] = useState("");

  // Evaluation form
  const [outcome, setOutcome] = useState<"SUPPORTED" | "CONTRADICTED" | "INCONCLUSIVE">(
    "INCONCLUSIVE",
  );
  const [rationale, setRationale] = useState("");
  const [unknowns, setUnknowns] = useState("");

  async function submitObservation() {
    setBusy(true);
    setMessage(null);
    const metrics: Record<string, number | null> = {};
    if (views.trim() !== "") metrics.views = Number(views);
    if (watchMinutes.trim() !== "") metrics.watch_time_minutes = Number(watchMinutes);
    try {
      const response = await addObservation(experiment.experiment_id, {
        request_id: `obs-${experiment.experiment_id}-${Date.now()}`,
        kind,
        measurement_status: measurement,
        observed_on: observedOn || null,
        metrics,
        interpretation: interpretation || null,
        limitations: limitations || null,
        source: "creator-reported",
      });
      setMessage(
        response.duplicate ? "That observation was already recorded." : "Observation recorded.",
      );
      setViews("");
      setWatchMinutes("");
      setInterpretation("");
      setLimitations("");
      setObservedOn("");
      await onChanged();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not record the observation.");
    } finally {
      setBusy(false);
    }
  }

  async function submitEvaluation() {
    if (!rationale.trim()) {
      setMessage("An evaluation needs a rationale — what did the observations actually show?");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await addEvaluation(experiment.experiment_id, {
        request_id: `eval-${experiment.experiment_id}-${Date.now()}`,
        outcome,
        rationale: rationale.trim(),
        observation_ids: observations.map((observation) => observation.observation_id),
        unknowns: unknowns || null,
      });
      setMessage("Evaluation recorded. Earlier evaluations remain in the history.");
      setRationale("");
      setUnknowns("");
      await onChanged();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not record the evaluation.");
    } finally {
      setBusy(false);
    }
  }

  const currentEvaluation = evaluations.length > 0 ? evaluations[evaluations.length - 1] : null;
  const provenance = experiment.provenance ?? {};
  const synthesisSnapshot =
    provenance.synthesis_snapshot &&
    typeof provenance.synthesis_snapshot === "object" &&
    !Array.isArray(provenance.synthesis_snapshot)
      ? (provenance.synthesis_snapshot as Record<string, unknown>)
      : null;
  const readRefs = (value: unknown): string[] =>
    Array.isArray(value) ? value.filter((ref): ref is string => typeof ref === "string") : [];
  const evidenceRefs = [
    ...new Set([...readRefs(provenance.evidence_refs), ...readRefs(synthesisSnapshot?.evidence_refs)]),
  ];
  const unresolvedEvidenceRefs = [
    ...new Set([
      ...readRefs(provenance.unresolved_evidence_refs),
      ...readRefs(synthesisSnapshot?.unresolved_evidence_refs),
    ]),
  ];

  return (
    <div className="grid gap-6">
      <div>
        <p className="field-label">Saved decision · snapshot, never rewritten, not executed</p>
        <p className="mt-2 text-sm leading-relaxed text-paper-2">{experiment.hypothesis}</p>
        {experiment.action_plan && (
          <p className="mt-2 text-sm leading-relaxed text-mute">
            <span className="text-amber">Planned action · </span>
            {experiment.action_plan}
          </p>
        )}
        {experiment.success_criteria && (
          <p className="mt-2 text-sm leading-relaxed text-mute">
            <span className="text-amber">Success criteria · </span>
            {experiment.success_criteria}
          </p>
        )}
        <p className="mt-3 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-dim">
          Source run {experiment.source_run_id ?? "—"} · data status{" "}
          {String(experiment.data_status).toUpperCase()}
        </p>
      </div>

      {savedPositioning && (
        <section aria-label="Frozen cultural strategy snapshot" className="border border-line p-4">
          <p className="type-kicker">Frozen cultural positioning · snapshot · not executed</p>
          <p className="mt-2 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-dim">
            Snapshot {String(savedPositioning.snapshot_version ?? "unknown")} · calculation{" "}
            {String(savedPositioning.calculation_version ?? "unknown")} · source status{" "}
            {String(savedPositioning.original_data_status ?? experiment.data_status).toUpperCase()}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-paper-2">
            {String(savedStrategy?.thesis ?? "Selected strategy details were not recorded.")}
          </p>
          <p className="mt-2 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-dim">
            Selected {String(savedPositioning.selected_strategy_id ?? "not recorded")} · policy{" "}
            {String(savedPolicy?.formula_version ?? "unknown")} · fit{" "}
            {String(savedPolicyValues?.fit ?? "—")} · exploration{" "}
            {String(savedPolicyValues?.exploration ?? "—")} · breadth{" "}
            {String(savedPolicyValues?.breadth ?? "—")}
          </p>
          {typeof savedStrategy?.falsifiable_hypothesis === "string" && (
            <p className="mt-2 text-sm leading-relaxed text-mute">
              Hypothesis · {savedStrategy.falsifiable_hypothesis}
            </p>
          )}
          <ul className="mt-3 space-y-1">
            {savedStrategies.map((strategy, index) => (
              <li
                key={`${String(strategy.id ?? index)}-${index}`}
                className="text-xs leading-relaxed text-dim"
              >
                {String(strategy.type ?? "strategy")} · {String(strategy.availability ?? "unknown")}
                {typeof strategy.unavailable_reason === "string"
                  ? ` · ${strategy.unavailable_reason}`
                  : ""}
                {typeof strategy.thesis === "string" ? ` · ${strategy.thesis}` : ""}
              </li>
            ))}
          </ul>
          {Array.isArray(savedPositioning.limitations) && (
            <p className="caption mt-2">Limits · {savedPositioning.limitations.map(String).join(" ")}</p>
          )}
        </section>
      )}

      <section aria-label="Saved experiment design" className="border border-line p-4">
        <p className="type-kicker">Saved test design · snapshot · not executed</p>
        <dl className="mt-3 grid gap-2">
          {DESIGN_ROWS.map(([label, key]) => {
            const value = savedDesign[key];
            return (
              <div key={key}>
                <dt className="caption">{label}</dt>
                <dd className="mt-1 text-sm leading-relaxed text-mute">
                  {value === null
                    ? "Not recorded in this saved experiment (older or partial snapshot)."
                    : value || "Blank when this snapshot was saved."}
                </dd>
              </div>
            );
          })}
        </dl>
      </section>

      <section className="border border-line p-4">
        <p className="type-kicker">Decision summary · hypothesised, observed, concluded</p>
        <dl className="mt-3 grid gap-4 text-sm">
          <div>
            <dt className="caption">Hypothesised (saved plan — not executed)</dt>
            <dd className="mt-1 leading-relaxed text-paper-2">{experiment.hypothesis}</dd>
          </div>
          <div>
            <dt className="caption">Saved evidence references</dt>
            <dd className="mt-1 leading-relaxed text-paper-2">
              {evidenceRefs.length > 0 ? (
                <EvidenceReferences
                  refs={evidenceRefs}
                  traceRows={sourceTrace}
                  scope={sourceTraceScope}
                  availability={
                    sourceTraceLoading ? "loading" : sourceTraceError ? "unavailable" : undefined
                  }
                />
              ) : (
                <span className="text-mute">
                  No call references are present in this saved provenance.
                </span>
              )}
              {unresolvedEvidenceRefs.length > 0 && (
                <span className="mt-1 block text-warn">
                  Unresolved, not stored as proof · {unresolvedEvidenceRefs.join(", ")}
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="caption">Observed (measured, never predicted)</dt>
            <dd className="mt-1 leading-relaxed text-paper-2">
              {observations.length === 0
                ? "Nothing observed yet."
                : `${observations.length} recorded observation(s).`}
            </dd>
          </div>
          <div>
            <dt className="caption">Concluded (latest evaluation, corrections kept)</dt>
            <dd className="mt-1 leading-relaxed text-paper-2">
              {currentEvaluation ? (
                <>
                  <span
                    className={cn(
                      currentEvaluation.outcome === "SUPPORTED" && "text-sage",
                      currentEvaluation.outcome === "CONTRADICTED" && "text-blood",
                      currentEvaluation.outcome === "INCONCLUSIVE" && "text-amber",
                    )}
                  >
                    {currentEvaluation.outcome}
                  </span>{" "}
                  — {currentEvaluation.rationale}
                </>
              ) : (
                <span className="text-mute">Not yet evaluated — record observations first.</span>
              )}
            </dd>
          </div>
          <div>
            <dt className="caption">Still missing</dt>
            <dd className="mt-1 leading-relaxed text-paper-2">
              {experiment.success_criteria
                ? `Success criteria to evaluate: ${experiment.success_criteria}`
                : "No success criteria recorded."}
              {currentEvaluation?.unknowns ? ` · Unknown: ${currentEvaluation.unknowns}` : ""}
            </dd>
          </div>
        </dl>
        <p className="caption mt-3">
          Measurements are observations, not proof of cause — cultural affinity is not viewership.
        </p>
      </section>

      {sourceTraceLoading && (
        <p role="status" className="text-sm text-mute">
          Loading the source run&apos;s recorded evidence trace…
        </p>
      )}
      {sourceTraceError && (
        <div role="status" className="border border-dashed border-line-strong p-4">
          <p className="text-sm leading-relaxed text-mute">
            The source run trace is unavailable here. Saved call IDs remain identifiers, not
            independently inspectable evidence in this view. {sourceTraceError}
          </p>
          {experiment.source_run_id && (
            <button type="button" className="btn-ghost mt-3" onClick={() => void loadSourceTrace()}>
              Retry source trace
            </button>
          )}
        </div>
      )}
      {!sourceTraceLoading && !sourceTraceError && (
        <div className="max-h-[420px] overflow-auto pr-1">
          <EvidenceTraceLog rows={sourceTrace} scope={sourceTraceScope} />
        </div>
      )}

      <section>
        <p className="field-label">
          Observations ({observations.length}) — zero is a result, empty is not
        </p>
        <ul className="mt-3 space-y-2">
          {observations.length === 0 && (
            <li className="text-sm text-mute">No observations recorded.</li>
          )}
          {observations.map((observation) => (
            <li key={observation.observation_id} className="border border-line p-3">
              <p className="font-mono text-[0.6rem] uppercase tracking-[0.12em] text-dim">
                {observation.kind} · {observation.measurement_status}
                {observation.observed_on ? ` · ${observation.observed_on}` : ""}
                {observation.supersedes_id ? " · correction" : ""}
              </p>
              <div className="mt-1 text-sm text-paper-2">
                {Object.entries(observation.metrics ?? {}).map(([metric, value]) => (
                  <span key={metric} className="mr-3">
                    {metric}: {value === null ? "—" : String(value)}
                  </span>
                ))}
                {Object.keys(observation.metrics ?? {}).length === 0 && (
                  <span className="text-dim">no metrics recorded</span>
                )}
              </div>
              {observation.interpretation && (
                <p className="mt-1 text-sm text-amber">
                  Creator interpretation · {observation.interpretation}
                </p>
              )}
              {observation.limitations && (
                <p className="mt-1 text-xs text-dim">Limitations · {observation.limitations}</p>
              )}
            </li>
          ))}
        </ul>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="field-label">Kind</span>
            <select
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={kind}
              onChange={(event) => setKind(event.target.value)}
            >
              <option value="ANALYTICS">Analytics</option>
              <option value="SCREENING">Screening</option>
              <option value="FEEDBACK">Feedback</option>
              <option value="NOTE">Note</option>
            </select>
          </label>
          <label className="block">
            <span className="field-label">Measurement status</span>
            <select
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={measurement}
              onChange={(event) => setMeasurement(event.target.value)}
            >
              <option value="OBSERVED">Observed</option>
              <option value="PARTIAL">Partial</option>
              <option value="MISSING">Missing</option>
              <option value="UNAVAILABLE">Unavailable</option>
              <option value="FAILED">Measurement failed</option>
            </select>
          </label>
          <label className="block">
            <span className="field-label">Observed on</span>
            <input
              type="date"
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={observedOn}
              onChange={(event) => setObservedOn(event.target.value)}
            />
          </label>
          <label className="block">
            <span className="field-label">Views · leave empty if unknown</span>
            <input
              inputMode="numeric"
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={views}
              onChange={(event) => setViews(event.target.value)}
            />
          </label>
          <label className="block">
            <span className="field-label">Watch time minutes · optional</span>
            <input
              inputMode="numeric"
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={watchMinutes}
              onChange={(event) => setWatchMinutes(event.target.value)}
            />
          </label>
          <label className="block">
            <span className="field-label">Your interpretation · kept separate</span>
            <input
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={interpretation}
              onChange={(event) => setInterpretation(event.target.value)}
            />
          </label>
          <label className="block sm:col-span-2">
            <span className="field-label">Limitations · what is missing</span>
            <input
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={limitations}
              onChange={(event) => setLimitations(event.target.value)}
            />
          </label>
        </div>
        <button
          type="button"
          className="btn-amber mt-3"
          onClick={() => void submitObservation()}
          disabled={busy}
        >
          Record observation
        </button>

        {liveFacetsUnavailable ? (
          <p className="caption mt-4">
            YouTube evidence is unavailable on this deployment; nothing was substituted.
          </p>
        ) : (
          <YouTubePanel experimentId={experiment.experiment_id} onChanged={onChanged} />
        )}
      </section>

      <section>
        <p className="field-label">
          Evaluations ({evaluations.length}) — append-only; corrections supersede
        </p>
        <ul className="mt-3 space-y-2">
          {evaluations.length === 0 && (
            <li className="text-sm text-mute">No evaluation recorded.</li>
          )}
          {evaluations.map((evaluation) => (
            <li key={evaluation.evaluation_id} className="border border-line p-3">
              <p
                className={cn(
                  "font-mono text-[0.6rem] uppercase tracking-[0.12em]",
                  evaluation.outcome === "SUPPORTED" && "text-sage",
                  evaluation.outcome === "CONTRADICTED" && "text-blood",
                  evaluation.outcome === "INCONCLUSIVE" && "text-amber",
                )}
              >
                {evaluation.outcome}
                {evaluation.supersedes_id ? " · supersedes earlier evaluation" : ""}
              </p>
              <p className="mt-1 text-sm leading-relaxed text-paper-2">{evaluation.rationale}</p>
              {evaluation.unknowns && (
                <p className="mt-1 text-xs text-dim">Unknown · {evaluation.unknowns}</p>
              )}
            </li>
          ))}
        </ul>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="field-label">Outcome</span>
            <select
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={outcome}
              onChange={(event) =>
                setOutcome(event.target.value as "SUPPORTED" | "CONTRADICTED" | "INCONCLUSIVE")
              }
            >
              <option value="SUPPORTED">Supported</option>
              <option value="CONTRADICTED">Contradicted</option>
              <option value="INCONCLUSIVE">Inconclusive</option>
            </select>
          </label>
          <label className="block">
            <span className="field-label">Rationale · what the observations showed</span>
            <input
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={rationale}
              onChange={(event) => setRationale(event.target.value)}
            />
          </label>
          <label className="block sm:col-span-2">
            <span className="field-label">What remains unknown</span>
            <input
              className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
              value={unknowns}
              onChange={(event) => setUnknowns(event.target.value)}
            />
          </label>
        </div>
        <button
          type="button"
          className="btn-amber mt-3"
          onClick={() => void submitEvaluation()}
          disabled={busy}
        >
          Record evaluation
        </button>
      </section>

      {message && (
        <p role="status" aria-live="polite" className="font-mono text-[0.62rem] text-amber">
          {message}
        </p>
      )}
    </div>
  );
}

function YouTubePanel({
  experimentId,
  onChanged,
}: {
  experimentId: string;
  onChanged: () => Promise<void>;
}) {
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
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const statusRequest = useRef(0);
  const videosRequest = useRef(0);

  const loadStatus = useCallback(async () => {
    const requestId = ++statusRequest.current;
    setStatusLoading(true);
    setStatus(null);
    setStatusError(null);
    try {
      const next = await youtubeStatus();
      if (requestId === statusRequest.current) setStatus(next);
    } catch (err) {
      if (requestId === statusRequest.current) {
        setStatus(null);
        setStatusError(err instanceof Error ? err.message : "Could not load YouTube status");
      }
    } finally {
      if (requestId === statusRequest.current) setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
    return () => {
      statusRequest.current += 1;
    };
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
        setVideosError(err instanceof Error ? err.message : "Could not list uploads");
      }
    } finally {
      if (requestId === videosRequest.current) setVideosLoading(false);
    }
  }, [status?.connected]);

  useEffect(() => {
    void loadVideos();
    return () => {
      videosRequest.current += 1;
    };
  }, [loadVideos]);

  async function record() {
    if (!videoId) {
      setMessage("Select the published video that corresponds to this experiment.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const response = await recordYouTubeObservation(experimentId, {
        request_id: `obs-yt-${experimentId}-${Date.now()}`,
        video_id: videoId,
        start_date: startDate,
        end_date: endDate,
      });
      setMessage(
        response.duplicate
          ? "That fetch was already recorded (duplicate request)."
          : response.observation.measurement_status === "OBSERVED"
            ? "Analytics recorded as an observation with full provenance."
            : "YouTube returned no rows — recorded as PARTIAL (ambiguous, not zero).",
      );
      await onChanged();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not record the YouTube observation");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await disconnectYouTube();
      setMessage(
        `Disconnected. Upstream revoked: ${result.revoked_upstream ? "yes" : "no"} · credentials deleted: ${
          result.credentials_deleted ? "yes" : "no"
        } · YouTube observations deleted: ${result.youtube_observations_deleted} · experiments tombstoned: ${result.experiments_tombstoned}.`,
      );
      await loadStatus();
      await onChanged();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not disconnect YouTube");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-5 border border-line p-4">
      <p className="type-kicker">YouTube evidence</p>
      {statusLoading && <p className="mt-2 text-sm text-mute">Checking connection…</p>}
      {statusError && (
        <p role="alert" className="mt-2 text-sm text-warn">
          {statusError}
        </p>
      )}
      {status && (
        <>
          <p className="mt-2 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-dim">
            Mode {status.mode} · connected {status.connected ? "yes" : "no"}
            {status.connection?.channel_title ? ` · ${status.connection.channel_title}` : ""}
          </p>
          {status.mode === "mock" && (
            <p className="mt-2 text-sm text-amber">
              MOCK YOUTUBE DATA · labelled mock analytics, not your channel. Nothing here is
              presented as real performance.
            </p>
          )}
          {!status.connected && (
            <div className="mt-2">
              <p className="text-sm leading-relaxed text-mute">
                {status.disabled_reason ??
                  "No YouTube connection. Authorize to record measured analytics as observations."}
              </p>
              <button
                type="button"
                className="btn-ghost mt-2"
                disabled={!status.configured}
                onClick={() => beginYouTubeAuthorization()}
              >
                Authorize YouTube
                <ArrowRight size={12} />
              </button>
            </div>
          )}
          {status.connected && (
            <>
              {videosLoading && <p className="mt-2 text-sm text-mute">Loading uploads…</p>}
              {videosError && (
                <p role="alert" className="mt-2 text-sm text-warn">
                  {videosError}
                </p>
              )}
              {videosNote && <p className="caption mt-2">{videosNote}</p>}
              {videos && videos.length > 0 && (
                <label className="mt-3 block">
                  <span className="field-label">Published video</span>
                  <select
                    className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                    value={videoId}
                    onChange={(event) => setVideoId(event.target.value)}
                  >
                    <option value="">Choose a video…</option>
                    {videos.map((video) => (
                      <option key={video.video_id} value={video.video_id}>
                        {video.title ?? video.video_id}
                        {video.published_at ? ` · ${video.published_at.slice(0, 10)}` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {videos && videos.length === 0 && (
                <p className="mt-2 text-sm text-mute">
                  No uploads were returned for this channel. That is a finding, not a metrics
                  result.
                </p>
              )}
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <label className="block">
                  <span className="field-label">Start date</span>
                  <input
                    type="date"
                    className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                    value={startDate}
                    onChange={(event) => setStartDate(event.target.value)}
                  />
                </label>
                <label className="block">
                  <span className="field-label">End date</span>
                  <input
                    type="date"
                    className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                    value={endDate}
                    onChange={(event) => setEndDate(event.target.value)}
                  />
                </label>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={busy}
                  onClick={() => void record()}
                >
                  Record analytics as observation
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={busy}
                  onClick={() => void disconnect()}
                >
                  Disconnect YouTube
                </button>
              </div>
            </>
          )}
        </>
      )}
      {message && (
        <p role="status" aria-live="polite" className="mt-2 font-mono text-[0.62rem] text-amber">
          {message}
        </p>
      )}
    </div>
  );
}
