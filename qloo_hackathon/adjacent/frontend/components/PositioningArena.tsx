"use client";

import { useEffect, useMemo, useState } from "react";
import {
  DEFAULT_POSITIONING_POLICY,
  orderPositioningStrategies,
  type PositioningDimensionName,
  type PositioningMultiverse,
  type PositioningOrdering,
  type PositioningPolicy,
  type PositioningStrategy,
} from "@/lib/positioningArena";

const DIMENSIONS: Array<{ key: PositioningDimensionName; label: string; hint: string }> = [
  { key: "fit", label: "Strongest supported fit", hint: "Within-context affinity rank only" },
  { key: "exploration", label: "Exploration / novelty", hint: "Existing 1 − median-popularity proxy" },
  { key: "breadth", label: "Evidence breadth", hint: "Distinct returned Qloo domains" },
];

function formatDimension(strategy: PositioningStrategy, key: PositioningDimensionName): string {
  const dimension = strategy.dimensions[key];
  if (!dimension.available || dimension.value === null) return `Unavailable — ${dimension.explanation}`;
  if (key === "fit") return `Rank ${dimension.value} · ${dimension.comparison_group ?? "within context"}`;
  if (key === "exploration") return `${dimension.value.toFixed(3)} · ${dimension.comparison_group ?? "within context"}`;
  return `${dimension.value} ${dimension.unit}`;
}

export default function PositioningArena({
  multiverse,
  policy,
  ordering,
  selectedId,
  onPolicyChange,
  onSelect,
}: {
  multiverse: PositioningMultiverse;
  policy: PositioningPolicy;
  ordering: PositioningOrdering;
  selectedId: PositioningStrategy["id"] | null;
  onPolicyChange: (policy: PositioningPolicy) => void;
  onSelect: (strategyId: PositioningStrategy["id"]) => void;
}) {
  const [appliedPreviewId, setAppliedPreviewId] = useState<PositioningStrategy["id"] | null>(null);
  const strategyById = new Map(multiverse.strategies.map((strategy) => [strategy.id, strategy]));
  const baselineOrdering = useMemo(
    () => orderPositioningStrategies(multiverse, DEFAULT_POSITIONING_POLICY),
    [multiverse],
  );
  const baselineRanks = new Map(baselineOrdering.entries.map((entry) => [entry.strategy_id, entry.rank]));
  const suggestedId = ordering.entries[0]?.strategy_id ?? null;
  const suggested = suggestedId ? strategyById.get(suggestedId) ?? null : null;
  const selected = multiverse.strategies.find((strategy) => strategy.id === selectedId && strategy.availability === "available") ?? null;
  const previewId = appliedPreviewId ?? selectedId;
  const preview = multiverse.strategies.find((strategy) => strategy.id === previewId && strategy.availability === "available") ?? null;
  const ordered = [
    ...ordering.entries.map((entry) => strategyById.get(entry.strategy_id)).filter((item): item is PositioningStrategy => Boolean(item)),
    ...multiverse.strategies.filter((strategy) => strategy.availability === "unavailable"),
  ];

  useEffect(() => setAppliedPreviewId(null), [multiverse.source_run_id]);

  return (
    <section className="positioning-arena" aria-labelledby="positioning-arena-title">
      <header className="positioning-arena-header">
        <div>
          <p className="nightfall-kicker">Cultural Multiverse · Positioning Arena</p>
          <h3 id="positioning-arena-title">Three defensible ways<br />to stand in culture.</h3>
        </div>
        <div className="positioning-arena-source">
          <span className={`positioning-status-chip is-${multiverse.data_status}`}>{multiverse.data_status.toUpperCase()}</span>
          <span>{multiverse.calculation_version}</span>
          {multiverse.source_run_id && <span>RUN {multiverse.source_run_id}</span>}
        </div>
      </header>
      <p className="positioning-arena-intro">
        Derived only from this completed Creator run and its trace. What-If priorities reorder existing evidence-backed candidates; they do not change evidence, predict audience behaviour, or create a causal counterfactual.
      </p>

      <section className="positioning-whatif" aria-labelledby="positioning-whatif-title">
        <div className="positioning-subhead">
          <div><p className="nightfall-kicker">What-If Lab · preview only</p><h4 id="positioning-whatif-title">Change the decision priorities.</h4></div>
          <span className="positioning-formula-tag">ORDINAL PREFERENCE FORMULA v1</span>
        </div>
        <fieldset className="positioning-priority-fields">
          <legend className="visually-hidden">What-if strategy priority weights</legend>
          {DIMENSIONS.map(({ key, label, hint }) => {
            const supported = multiverse.strategies.some((strategy) => strategy.availability === "available" && strategy.dimensions[key].available);
            return (
              <label key={key} className={`positioning-priority-row${supported ? "" : " is-unavailable"}`}>
                <span className="positioning-priority-label">{label}<small>{supported ? hint : "Unavailable in this run's evidence"}</small></span>
                <input
                  type="range" min={0} max={100} step={1} value={policy[key]}
                  aria-label={`${label} priority`} disabled={!supported}
                  onChange={(event) => onPolicyChange({ ...policy, [key]: Number(event.target.value) })}
                />
                <output className="positioning-priority-value">{supported ? policy[key] : "—"}</output>
              </label>
            );
          })}
        </fieldset>
        <p className="positioning-order-notes">{ordering.notes.join(" ")} Weights: fit {policy.fit}, exploration {policy.exploration}, breadth {policy.breadth}. Unsupported dimensions are omitted and disclosed.</p>

        <div className="positioning-suggestion-panel">
          <div className="positioning-order-list">
            <p className="micro-label">SUGGESTED ORDER · EXISTING CANDIDATES</p>
            {ordering.entries.length === 0 ? (
              <p className="positioning-empty">No strategy is eligible in this run. The What-If Lab cannot promote unsupported evidence.</p>
            ) : (
              <ol aria-label="Current strategy preference order">
                {ordering.entries.map((entry) => {
                  const baselineRank = baselineRanks.get(entry.strategy_id);
                  const movement = baselineRank === undefined || baselineRank === entry.rank
                    ? "same rank as default"
                    : entry.rank < baselineRank ? `up from default ${baselineRank}` : `down from default ${baselineRank}`;
                  return (
                    <li key={entry.strategy_id} className={entry.strategy_id === suggestedId ? "is-suggested" : ""}>
                      <span className="positioning-order-rank">{String(entry.rank).padStart(2, "0")}</span>
                      <span className="positioning-order-name">{entry.strategy_id.toUpperCase()}{entry.strategy_id === suggestedId && <small>Suggested</small>}</span>
                      <span className="positioning-order-delta">{movement}</span>
                      <p>{entry.preference_index === null ? "Source-rank tie-break." : `Preference index ${entry.preference_index.toFixed(3)} · ${entry.explanation}`}</p>
                      {Object.keys(entry.unavailable_dimensions).length > 0 && <p className="positioning-order-unavailable">Unavailable: {Object.keys(entry.unavailable_dimensions).join(", ")}</p>}
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
          <div className="positioning-apply-panel">
            <span className="micro-label">SCENARIO PREVIEW</span>
            <p>{suggested ? <>Current weights suggest <strong>{suggested.type}</strong>. Your selected Test Card strategy is <strong>{selected?.type ?? "not selected"}</strong>.</> : "There is no evidence-supported suggestion for this run."}</p>
            <div className="positioning-preview-actions">
              <button type="button" className="positioning-action-primary" disabled={!suggested || appliedPreviewId === suggested.id} onClick={() => setAppliedPreviewId(suggested?.id ?? null)}>
                {appliedPreviewId === suggested?.id ? "Suggestion in preview" : "Apply to preview"}
              </button>
              {appliedPreviewId !== null && <button type="button" className="positioning-action-secondary" onClick={() => setAppliedPreviewId(null)}>Reset to selected</button>}
            </div>
            <small>Preview changes only the comparison shown below. It does not change your Test Card selection, saved snapshot, evidence, experiments, or provider calls.</small>
          </div>
        </div>

        {selected && suggested && (
          <div className="positioning-compare-grid" aria-label="Selected and suggested strategy comparison">
            <article className={selected.id === suggested.id ? "is-match" : ""}>
              <p className="micro-label">SELECTED · TEST CARD</p><h5>{selected.type}</h5><p>{selected.thesis}</p>
              <small>Source cohorts: {selected.source_cohort_ids.join(", ") || "none"}</small>
            </article>
            <article className={selected.id === suggested.id ? "is-match" : "is-suggested"}>
              <p className="micro-label">SUGGESTED · CURRENT WHAT-IF</p><h5>{suggested.type}</h5><p>{suggested.thesis}</p>
              <small>Source cohorts: {suggested.source_cohort_ids.join(", ") || "none"}</small>
            </article>
          </div>
        )}
        {preview && (
          <div className="positioning-applied-preview" aria-live="polite">
            <p className="micro-label">{appliedPreviewId ? "APPLIED TO PREVIEW · LOCAL ONLY" : "CURRENT PREVIEW · SELECTED DIRECTION"}</p>
            <h5>{preview.type} · {preview.creative_direction}</h5>
            <p>{preview.tradeoffs.join(" ")}</p>
          </div>
        )}
      </section>

      <div className="positioning-strategy-grid">
        {ordered.map((strategy) => (
          <article key={strategy.id} className={`positioning-strategy-card${strategy.availability === "unavailable" ? " is-unavailable" : ""}${selectedId === strategy.id ? " is-selected" : ""}${suggestedId === strategy.id ? " is-suggested" : ""}`}>
            <div className="positioning-strategy-topline">
              <div><p className="nightfall-kicker">{strategy.type}</p><h4>{strategy.availability === "available" ? "Evidence available" : "Unavailable"}</h4></div>
              <div className="positioning-card-badges">
                {suggestedId === strategy.id && <span className="positioning-badge is-suggested">Suggested</span>}
                {selectedId === strategy.id && <span className="positioning-badge is-selected">Selected</span>}
                {appliedPreviewId === strategy.id && <span className="positioning-badge is-preview">Preview</span>}
              </div>
            </div>
            {strategy.availability === "unavailable" ? (
              <p className="positioning-unavailable-reason" role="status">{strategy.unavailable_reason}</p>
            ) : (
              <>
                <h5>{strategy.thesis}</h5>
                <p className="positioning-creative-direction">{strategy.creative_direction}</p>
                <p className="positioning-provenance">DATA {strategy.data_status.toUpperCase()} · EVIDENCE {strategy.evidence_strength ?? "not available"} · COHORTS {strategy.source_cohort_ids.join(", ") || "—"}</p>
                <ul className="positioning-entity-list">
                  {strategy.entity_refs.map((entity) => (
                    <li key={`${entity.cohort_id}:${entity.entity_id}`}>
                      <strong>{entity.name}</strong><span>{entity.domain.replace("urn:entity:", "")} · Qloo cultural similarity {entity.affinity.toFixed(3)}</span>
                      <code>{entity.call_id}</code>
                    </li>
                  ))}
                </ul>
                <div className="positioning-dimensions">
                  {(Object.keys(strategy.dimensions) as PositioningDimensionName[]).map((key) => (
                    <div key={key}><span>{key.toUpperCase()}</span>{formatDimension(strategy, key)}</div>
                  ))}
                </div>
                <p className="positioning-rationale"><strong>Why this direction:</strong> {strategy.why_selected}</p>
                <details className="positioning-evidence-challenge">
                  <summary>Evidence Challenge · attribution {strategy.evidence_challenge.attribution_status}</summary>
                  <p>{strategy.evidence_challenge.attribution_detail}</p>
                  <p><strong>Member attribution states:</strong> {strategy.evidence_challenge.attribution_statuses.join(", ") || "missing"}</p>
                  <p><strong>Source inputs:</strong> {strategy.evidence_challenge.source_inputs.map((input) => `${input.title} [${input.resolution_status}]`).join(" · ") || "none returned"}</p>
                  {strategy.evidence_challenge.unresolved_references.length > 0 && <p><strong>Unresolved:</strong> {strategy.evidence_challenge.unresolved_references.join(", ")}</p>}
                  <ul>{strategy.evidence_challenge.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
                  <p><strong>Could support:</strong> {strategy.evidence_challenge.observation_that_supports}</p>
                  <p><strong>Could contradict:</strong> {strategy.evidence_challenge.observation_that_contradicts}</p>
                </details>
                <div className="positioning-evidence-refs">
                  {strategy.evidence_refs.map((evidence, index) => (
                    <p key={`${evidence.kind}-${index}`}><span>{evidence.kind.replaceAll("_", " ")}</span>{evidence.description}<small>Calls {evidence.call_ids.join(", ") || "unavailable"} · entities {evidence.entity_ids.join(", ") || "none"}</small></p>
                  ))}
                </div>
                <button type="button" className="positioning-action-secondary" aria-pressed={selectedId === strategy.id} onClick={() => onSelect(strategy.id)}>
                  {selectedId === strategy.id ? "Selected for Test Card" : "Select for Test Card"}
                </button>
              </>
            )}
          </article>
        ))}
      </div>

      {selected && (
        <section className="positioning-brief" aria-label="Grounded positioning brief">
          <div><p className="nightfall-kicker">Decision brief · {selected.type}</p><h4>{selected.thesis}</h4></div>
          <div><p>{selected.creative_direction}</p><p><strong>Falsifiable hypothesis:</strong> {selected.falsifiable_hypothesis}</p></div>
          <div><p><strong>Suggested test:</strong> {selected.suggested_test.comparison_protocol} {selected.suggested_test.primary_measure} {selected.suggested_test.decision_rule} {selected.suggested_test.observation_window}</p><p><strong>Limits:</strong> {selected.tradeoffs.join(" ")}</p></div>
          <p className="positioning-brief-note">The selected direction is the one used by the existing Test Card save/export workflow. The applied preview above never changes this selection.</p>
        </section>
      )}
    </section>
  );
}
