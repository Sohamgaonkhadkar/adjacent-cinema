"use client";

import { useMemo, useState } from "react";
import { ArrowRight, Lock, Snowflake } from "lucide-react";
import type {
  PositioningDimensionName,
  PositioningMultiverse,
  PositioningOrdering,
  PositioningPolicy,
  PositioningStrategy,
} from "@/lib/positioningArena";
import { photos, type Photo } from "@/lib/photos";
import { PhotoFrame } from "./PhotoFrame";
import { ClaimChip, SourceStatusChip } from "./Chips";
import { cn } from "@/lib/cn";

/**
 * Cultural Multiverse / Positioning Arena.
 *
 * Visual composition, three-stage presentation and the "freeze decision"
 * affordance are ported from the source ZIP
 * (src/components/PositioningArena.tsx). Unlike the ZIP's concept preview, this
 * implementation is driven entirely by a completed run: strategies, their
 * availability, evidence references, limitations and the what-if ordering all
 * come from `lib/positioningArena` (no illustrative scores, no invented copy).
 */

const stagePhoto: Record<PositioningStrategy["id"], Photo> = {
  anchor: photos.cinemaEmpty,
  bridge: photos.editingTable,
  frontier: photos.projectorLens,
};

const stageSecond: Record<PositioningStrategy["id"], Photo> = {
  anchor: photos.reelTape,
  bridge: photos.nightAlley,
  frontier: photos.filmstrips,
};

/**
 * Editorial treatment per strategy. This is a documented product convention
 * (how the strategy is presented), explicitly not evidence about the film.
 */
const TREATMENT: Record<PositioningStrategy["id"], string> = {
  anchor: "One still frame, level horizon, one claim per line. Restraint is the point.",
  bridge: "Diptych. Two photographic fields and a join you can see. Two captions, one decision.",
  frontier: "Off-centre crop, more air, the question in the copy. Never a verdict.",
};

const DIMENSIONS: Array<{ key: PositioningDimensionName; label: string; hint: string }> = [
  { key: "fit", label: "Evidence strictness", hint: "Rank of this world within its scoring context" },
  { key: "exploration", label: "Exploratory range", hint: "Novelty proxy from returned popularity" },
  { key: "breadth", label: "Context breadth", hint: "Distinct returned provider domains" },
];

function strategyName(strategy: PositioningStrategy): string {
  return strategy.type === "ANCHOR" ? "Anchor" : strategy.type === "BRIDGE" ? "Bridge" : "Frontier";
}

function kindLabel(kind: string): string {
  if (kind === "candidate_affinity") return "CANDIDATE AFFINITY";
  if (kind === "shared_qloo_tag") return "SHARED PROVIDER TAG";
  if (kind === "shared_seed_attribution") return "SHARED SEED ATTRIBUTION";
  return kind.toUpperCase();
}

function formatDimension(strategy: PositioningStrategy, key: PositioningDimensionName): string {
  const dimension = strategy.dimensions[key];
  if (!dimension.available || dimension.value === null) return dimension.explanation;
  if (key === "fit") {
    return `Rank ${dimension.value} · ${dimension.comparison_group ?? "within its scoring context"}`;
  }
  if (key === "exploration") {
    return `${dimension.value.toFixed(3)} exploration proxy · ${dimension.comparison_group ?? "within its context"}`;
  }
  return `${dimension.value} ${dimension.unit} · ${dimension.comparison_group ?? "returned domains"}`;
}

export function PositioningArena({
  multiverse,
  policy,
  ordering,
  selectedId,
  onPolicyChange,
  onSelect,
  experimentDesign,
  freeze,
  sourceLabel,
}: {
  multiverse: PositioningMultiverse;
  policy: PositioningPolicy;
  ordering: PositioningOrdering;
  selectedId: PositioningStrategy["id"] | null;
  onPolicyChange: (policy: PositioningPolicy) => void;
  onSelect: (id: PositioningStrategy["id"]) => void;
  experimentDesign: {
    comparison_protocol: string;
    primary_measure: string;
    decision_rule: string;
    observation_window: string;
  } | null;
  freeze: {
    busy: boolean;
    disabledReason: string | null;
    message: string | null;
    savedStrategyId: string | null;
    onSave: () => void;
  };
  sourceLabel: string;
}) {
  const [freezeOpen, setFreezeOpen] = useState(false);
  const [applied, setApplied] = useState<PositioningStrategy["id"] | null>(null);

  const byId = useMemo(
    () => new Map(multiverse.strategies.map((strategy) => [strategy.id, strategy])),
    [multiverse.strategies],
  );
  const suggestedId = ordering.entries[0]?.strategy_id ?? null;
  const active =
    multiverse.strategies.find(
      (strategy) => strategy.id === selectedId && strategy.availability === "available",
    ) ?? null;
  const preview = active ?? multiverse.strategies[0] ?? null;
  const ordered = [
    ...ordering.entries
      .map((entry) => byId.get(entry.strategy_id))
      .filter((strategy): strategy is PositioningStrategy => Boolean(strategy)),
    ...multiverse.strategies.filter((strategy) => strategy.availability === "unavailable"),
  ];
  const dirty = applied !== null && applied !== suggestedId;

  return (
    <div className="border border-line bg-ink-2">
      <header className="border-b border-line px-5 py-5 md:px-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="type-kicker">Cultural Multiverse · Positioning Arena</p>
            <h3 className="font-display mt-2 text-3xl md:text-4xl">
              Three defensible ways to stand in culture.
            </h3>
          </div>
          <SourceStatusChip status={multiverse.data_status} />
        </div>

        <div className="mt-6 grid gap-px bg-line md:grid-cols-3">
          <SourceCell
            label="Source investigation"
            value={multiverse.film_title || sourceLabel}
            detail={`Run ${multiverse.source_run_id ?? "—"} · ${multiverse.calculation_version}`}
          />
          <SourceCell
            label="Strategy engine"
            value={`${multiverse.strategies.filter((item) => item.availability === "available").length} of 3 available`}
            detail="Built from this run's ranked cohorts, members and trace. Unsupported positions abstain with a reason."
          />
          <SourceCell
            label="Data status"
            value={multiverse.data_status === "measured" ? "Measured Qloo run" : "Labelled fixture run"}
            detail="No cross-query affinity comparison. No audience forecast. No invented strategy."
          />
        </div>

        <p className="mt-4 text-xs leading-relaxed text-mute">
          {ordering.notes.join(" ")} A strategy that cannot clear the evidence gate is shown as
          unavailable instead of being written as if it existed.
        </p>
      </header>

      <div className="grid lg:grid-cols-12">
        {/* ── tabs + what-if ─────────────────────────────────────────── */}
        <div className="border-b border-line lg:col-span-3 lg:border-b-0 lg:border-r">
          <ul>
            {ordered.map((strategy, index) => {
              const isActive = active?.id === strategy.id;
              const unavailable = strategy.availability === "unavailable";
              return (
                <li key={strategy.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(strategy.id)}
                    aria-pressed={isActive}
                    className={cn(
                      "w-full border-b border-line px-5 py-5 text-left transition-colors",
                      isActive ? "bg-amber/10" : "hover:bg-ink-3",
                      unavailable && "opacity-70",
                    )}
                  >
                    <span className="flex items-baseline justify-between gap-2">
                      <span className="type-meta">
                        0{index + 1} · {unavailable ? "unavailable" : strategy.evidence_strength ?? "available"}
                      </span>
                      {freeze.savedStrategyId === strategy.id && (
                        <span className="caption text-sage">in saved plan</span>
                      )}
                      {strategy.id === suggestedId && applied !== suggestedId && (
                        <span className="caption text-warn">suggested</span>
                      )}
                    </span>
                    <span
                      className={cn(
                        "font-display mt-1 block text-3xl",
                        isActive ? "text-amber" : "text-paper",
                      )}
                    >
                      {strategyName(strategy)}
                    </span>
                    <span className="mt-1 block text-sm leading-relaxed text-mute">
                      {unavailable ? strategy.unavailable_reason : strategy.thesis}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="px-5 py-5">
            <p className="type-kicker">What-if lab</p>
            <p className="mt-2 text-xs leading-relaxed text-mute">
              Drag the priorities to reorder the candidates that already exist. Nothing is rescored
              and nothing moves until you apply it.
            </p>
            <div className="mt-5 space-y-5">
              {DIMENSIONS.map(({ key, label, hint }) => {
                const supported = multiverse.strategies.some(
                  (strategy) =>
                    strategy.availability === "available" && strategy.dimensions[key].available,
                );
                return (
                  <label key={key} className="block">
                    <span className="flex justify-between font-mono text-[0.6rem] uppercase tracking-[0.14em] text-amber">
                      {label}
                      <span className="text-paper-2">{supported ? policy[key] : "—"}</span>
                    </span>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={policy[key]}
                      disabled={!supported}
                      aria-label={`${label} priority`}
                      onChange={(event) =>
                        onPolicyChange({ ...policy, [key]: Number(event.target.value) })
                      }
                      className="mt-2 w-full accent-amber"
                    />
                    <span className="mt-1 block text-[0.62rem] leading-relaxed text-dim">
                      {supported ? hint : "Unavailable in this run's evidence — omitted, not scored."}
                    </span>
                  </label>
                );
              })}
            </div>

            <div className="mt-5 border border-line bg-ink p-3">
              <p className="type-meta">Preference order · existing candidates</p>
              {ordering.entries.length === 0 ? (
                <p className="mt-2 text-xs leading-relaxed text-mute">
                  No strategy is eligible in this run, so the lab cannot promote one.
                </p>
              ) : (
                <ol className="mt-2 space-y-1">
                  {ordering.entries.map((entry) => (
                    <li key={entry.strategy_id} className="flex items-baseline justify-between text-xs">
                      <span className={entry.strategy_id === suggestedId ? "text-amber" : "text-mute"}>
                        {String(entry.rank).padStart(2, "0")} · {entry.strategy_id}
                      </span>
                      <span className="font-mono tabular-nums text-paper-2">
                        {entry.preference_index === null
                          ? "tie-break"
                          : entry.preference_index.toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </div>

            <p className="mt-4 text-xs leading-relaxed text-paper-2">
              Suggested: <span className="text-amber">{suggestedId ?? "none"}</span>.
              {suggestedId === null
                ? " No candidate cleared the evidence gate for this run."
                : ` ${ordering.entries[0]?.explanation ?? ""}`}
            </p>
            <p className="mt-2 font-mono text-[0.58rem] leading-relaxed text-dim">
              {ordering.formula_version} · fit {policy.fit} / exploration {policy.exploration} /
              breadth {policy.breadth}. Preference is ordinal, not a prediction.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-amber"
                disabled={!suggestedId || suggestedId === active?.id}
                onClick={() => {
                  if (!suggestedId) return;
                  onSelect(suggestedId);
                  setApplied(suggestedId);
                }}
              >
                Apply to preview
              </button>
              {applied && applied !== suggestedId && (
                <button type="button" className="btn-ghost" onClick={() => setApplied(null)}>
                  Clear applied
                </button>
              )}
            </div>
            {dirty && (
              <p className="mt-2 caption text-warn">
                Priorities changed after your last apply — selected and suggested stay distinct.
              </p>
            )}
          </div>
        </div>

        {/* ── stage + brief ─────────────────────────────────────────── */}
        <div className="min-h-0 flex flex-col lg:col-span-6">
          {!active ? (
            <div className="flex min-h-[300px] flex-col justify-center gap-4 border-b border-line p-6 md:min-h-[380px] md:p-10">
              <span className="chip chip-warn">No supported strategy selected</span>
              <h4 className="font-display text-3xl leading-[0.95] md:text-4xl">
                {preview?.availability === "unavailable"
                  ? `${strategyName(preview)} is unavailable for this run.`
                  : "Select an available strategy."}
              </h4>
              <p className="max-w-md text-sm leading-relaxed text-mute">
                {preview?.unavailable_reason ??
                  "An unavailable strategy is not replaced with illustrative copy. Its reason stays visible in the list."}
              </p>
            </div>
          ) : (
            <>
              <div className="relative min-h-[300px] md:min-h-[380px]">
                <PhotoFrame
                  photo={stagePhoto[active.id]}
                  fill
                  credit={false}
                  priority
                  imgClassName={cn("h-full w-full object-cover", active.id === "frontier" && "object-[20%_center]")}
                />
                <div
                  className={cn(
                    "absolute inset-0",
                    active.id === "anchor" && "bg-gradient-to-t from-ink via-ink/55 to-transparent",
                    active.id === "bridge" && "bg-gradient-to-r from-ink/85 via-ink/40 to-ink/85",
                    active.id === "frontier" && "bg-gradient-to-r from-ink via-ink/75 to-transparent",
                  )}
                />
                <div
                  className={cn(
                    "relative z-10 flex min-h-[300px] flex-col justify-end p-6 md:min-h-[380px] md:p-8",
                    active.id === "bridge" && "items-center text-center",
                    active.id === "frontier" && "max-w-md",
                  )}
                >
                  <p className="type-kicker">{strategyName(active)}</p>
                  <h4
                    className={cn(
                      "font-display mt-3 leading-[0.95] text-paper",
                      active.id === "frontier" ? "text-4xl md:text-5xl" : "text-3xl md:text-5xl",
                      active.id === "anchor" && "text-center",
                    )}
                  >
                    {active.thesis}
                  </h4>
                  <p className="mt-4 max-w-md text-sm leading-relaxed text-paper-2">
                    {active.why_selected}
                  </p>
                </div>
              </div>

              <div className="border-t border-line p-5 md:p-6">
                <p className="type-kicker">Positioning brief</p>
                <p className="mt-3 text-sm leading-relaxed text-paper-2">
                  {active.creative_direction}
                </p>
                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <div className="border border-line p-3">
                    <p className="type-meta">Worlds held</p>
                    {active.entity_refs.length === 0 && (
                      <p className="mt-2 text-sm text-mute">No returned entity supports this row.</p>
                    )}
                    {active.entity_refs.slice(0, 3).map((entity) => (
                      <p key={`${entity.cohort_id}-${entity.entity_id}`} className="mt-2 text-sm text-paper">
                        {entity.name}
                        <span className="caption"> · {entity.domain} · {entity.affinity.toFixed(2)}</span>
                      </p>
                    ))}
                  </div>
                  <div className="border border-line p-3">
                    <p className="type-meta">Suggested treatment</p>
                    <p className="mt-2 text-sm text-paper-2">{TREATMENT[active.id]}</p>
                    <p className="mt-2 text-[0.6rem] leading-relaxed text-dim">
                      Editorial convention for presenting this strategy — not evidence about the film.
                    </p>
                  </div>
                </div>
                <div className="mt-5 flex gap-2 overflow-hidden border border-line">
                  {[stagePhoto[active.id], stageSecond[active.id], photos.soho].map((photo, index) => (
                    <div key={`${photo.src}-${index}`} className="h-16 flex-1">
                      <PhotoFrame photo={photo} className="h-full" credit={false} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Fill the shared grid row intentionally. The evidence inspector can be
                  much taller than the brief; without this visual field its column was
                  a large, empty black rectangle beneath the contact sheet. These are
                  atmospheric photographs, not additional evidence for the selected strategy. */}
              <div
                data-testid="multiverse-visual-field"
                className="relative mt-auto min-h-[280px] flex-1 overflow-hidden border-t border-line bg-ink-3"
              >
                <div className="absolute inset-0 grid grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)] gap-px bg-line">
                  <div className="relative min-h-0 overflow-hidden bg-ink-3">
                    <PhotoFrame
                      photo={stageSecond[active.id]}
                      fill
                      credit={false}
                      imgClassName="h-full w-full object-cover"
                    />
                  </div>
                  <div className="relative min-h-0 overflow-hidden bg-ink-3">
                    <PhotoFrame
                      photo={photos.lanternStreet}
                      fill
                      credit={false}
                      imgClassName="h-full w-full object-cover"
                    />
                  </div>
                </div>
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink via-ink/20 to-transparent" />
                <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 p-5 md:p-6">
                  <p className="type-kicker">Additional visual field · {strategyName(active)}</p>
                  <p className="caption mt-2 max-w-sm">
                    Atmospheric imagery only · the positioning decision remains bounded by the cited evidence above.
                  </p>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ── evidence challenge + freeze ───────────────────────────── */}
        <div className="border-t border-line lg:col-span-3 lg:border-l lg:border-t-0">
          <div className="border-b border-line p-5">
            <p className="type-kicker">Evidence challenge</p>
            {!active ? (
              <p className="mt-4 text-xs leading-relaxed text-mute">
                Select an available strategy to inspect what supports it and what would contradict it.
              </p>
            ) : (
              <>
                <ul className="mt-4 space-y-3">
                  {active.evidence_refs.length === 0 && (
                    <li className="border border-line p-3 text-xs text-mute">
                      This run returned no distinct evidence reference for the strategy.
                    </li>
                  )}
                  {active.evidence_refs.map((row) => (
                    <li key={`${row.kind}-${row.description}`} className="border border-line p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-paper-2">
                          {row.description}
                        </span>
                        <span className="chip chip-unk">{kindLabel(row.kind)}</span>
                      </div>
                      <p className="mt-2 font-mono text-[0.58rem] leading-relaxed text-dim">
                        {row.call_ids.length > 0 ? `Calls · ${row.call_ids.join(", ")}` : "No call id returned"}
                        {row.qloo_tag_id ? ` · tag ${row.qloo_tag_id}` : ""}
                        {row.source_seed_id ? ` · seed ${row.source_seed_id}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>

                <div className="mt-4 space-y-2">
                  <p className="caption">Source inputs</p>
                  <ul className="space-y-1">
                    {active.evidence_challenge.source_inputs.map((input) => (
                      <li key={`${input.title}-${input.entity_id ?? "unresolved"}`} className="text-xs leading-relaxed text-paper-2">
                        — {input.title}
                        <span className="text-dim">
                          {" "}· {input.resolution_status}
                          {input.call_ids.length ? ` · ${input.call_ids.join(", ")}` : ""}
                        </span>
                      </li>
                    ))}
                    {active.evidence_challenge.source_inputs.length === 0 && (
                      <li className="text-xs text-mute">No source input was recorded for this run.</li>
                    )}
                  </ul>
                </div>

                <div className="mt-4 space-y-2">
                  <p className="caption">Attribution</p>
                  <p className="text-xs leading-relaxed text-paper-2">
                    {active.evidence_challenge.attribution_detail}
                  </p>
                </div>

                {active.evidence_challenge.unresolved_references.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="caption">Unresolved references · not stored as proof</p>
                    <p className="text-xs leading-relaxed text-paper-2">
                      {active.evidence_challenge.unresolved_references.join(", ")}
                    </p>
                  </div>
                )}

                <div className="mt-4 space-y-2">
                  <p className="caption">Limitations</p>
                  <ul className="space-y-2">
                    {[...active.evidence_challenge.limitations, ...active.tradeoffs].map((limitation, index) => (
                      <li key={`${limitation}-${index}`} className="text-xs leading-relaxed text-paper-2">
                        — {limitation}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-4 border-t border-line pt-4">
                  <div className="flex flex-wrap gap-2">
                    <ClaimChip kind="HYPOTHESIS" />
                    <span className="chip chip-warn">Falsifiable</span>
                  </div>
                  <p className="mt-3 text-xs leading-relaxed text-paper-2">
                    {active.falsifiable_hypothesis}
                  </p>
                  <dl className="mt-3 space-y-1 text-[0.65rem] leading-relaxed text-mute">
                    <div>
                      <dt className="text-dim">Would support</dt>
                      <dd>{active.evidence_challenge.observation_that_supports}</dd>
                    </div>
                    <div className="mt-2">
                      <dt className="text-dim">Would contradict</dt>
                      <dd>{active.evidence_challenge.observation_that_contradicts}</dd>
                    </div>
                  </dl>
                </div>
              </>
            )}
          </div>

          <div className="p-5">
            <p className="type-kicker">Freeze decision</p>
            <p className="mt-3 text-xs leading-relaxed text-mute">
              Saving records the selected strategy, the policy and the experiment design in a
              decision snapshot attached to a planned experiment. It does not run anything.
            </p>
            <button
              type="button"
              className="btn-ghost mt-4 w-full justify-center"
              disabled={Boolean(freeze.disabledReason) || freeze.busy}
              aria-disabled={Boolean(freeze.disabledReason) || freeze.busy}
              title={freeze.disabledReason ?? "Save the plan with this strategy"}
              onClick={freeze.onSave}
            >
              <Snowflake size={14} />
              {freeze.busy ? "Saving…" : "Freeze decision"}
            </button>
            {freeze.disabledReason && (
              <p className="mt-2 text-[0.65rem] leading-relaxed text-dim">{freeze.disabledReason}</p>
            )}
            {freeze.message && (
              <p className="mt-2 text-xs leading-relaxed text-amber" role="status" aria-live="polite">
                {freeze.message}
              </p>
            )}
            <button
              type="button"
              className="btn-amber mt-3 w-full justify-center"
              onClick={() => setFreezeOpen((value) => !value)}
              aria-expanded={freezeOpen}
            >
              <Lock size={13} />
              {freezeOpen ? "Hide snapshot preview" : "Preview snapshot record"}
            </button>
            {freezeOpen && (
              <div className="drawer-enter mt-4 border border-line bg-ink p-3">
                <p className="type-meta">Record preview</p>
                <dl className="mt-3 space-y-2 text-xs">
                  <Line k="strategy" v={active ? strategyName(active).toUpperCase() : "— none selected —"} />
                  <Line k="source_run" v={multiverse.source_run_id ?? "— none attached —"} />
                  <Line
                    k="status"
                    v={
                      active && freeze.savedStrategyId === active.id
                        ? "SAVED IN PLAN"
                        : "NOT SAVED"
                    }
                  />
                  <Line k="priorities" v={`F${policy.fit} E${policy.exploration} B${policy.breadth}`} />
                  <Line
                    k="comparison"
                    v={experimentDesign?.comparison_protocol ? "recorded" : "— not written —"}
                  />
                  <Line
                    k="decision_rule"
                    v={experimentDesign?.decision_rule ? "set by creator" : "— not set —"}
                  />
                </dl>
                <p className="mt-3 flex items-center gap-1 text-[0.65rem] text-dim">
                  {freeze.savedStrategyId === active?.id ? "Stored by the backend." : "Nothing has been written yet."}
                  <ArrowRight size={11} />
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {applied !== null && (
        <p className="border-t border-line px-5 py-3 caption">
          Suggestion applied to preview: {applied}. Selected and suggested stay visually distinct
          until you apply again.
        </p>
      )}
    </div>
  );
}

function SourceCell({
  label,
  value,
  detail,
  chip,
}: {
  label: string;
  value: string;
  detail: string;
  chip?: React.ReactNode;
}) {
  return (
    <div className="bg-ink-2 p-4">
      <p className="type-meta">{label}</p>
      <p className="font-display mt-2 text-xl">{value}</p>
      {chip && <div className="mt-2">{chip}</div>}
      <p className="mt-2 text-xs leading-relaxed text-mute">{detail}</p>
    </div>
  );
}

function Line({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-dim">{k}</dt>
      <dd className="text-right text-paper-2">{v}</dd>
    </div>
  );
}
