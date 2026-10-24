"use client";

import {
  DEFAULT_POSITIONING_POLICY,
  orderPositioningStrategies,
  type PositioningMultiverse,
  type PositioningOrdering,
  type PositioningPolicy,
  type PositioningStrategy,
  type PositioningDimensionName,
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
  const strategyById = new Map(multiverse.strategies.map((strategy) => [strategy.id, strategy]));
  const baselineOrdering = orderPositioningStrategies(multiverse, DEFAULT_POSITIONING_POLICY);
  const baselineRanks = new Map(baselineOrdering.entries.map((entry) => [entry.strategy_id, entry.rank]));
  const ordered = [
    ...ordering.entries.map((entry) => strategyById.get(entry.strategy_id)).filter((item): item is PositioningStrategy => Boolean(item)),
    ...multiverse.strategies.filter((strategy) => strategy.availability === "unavailable"),
  ];
  const selected = multiverse.strategies.find((strategy) => strategy.id === selectedId && strategy.availability === "available");

  return (
    <section aria-labelledby="positioning-arena-title" style={{ margin: "24px 0", padding: 20, border: "1px solid var(--rule)", borderRadius: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <h3 id="positioning-arena-title" style={{ margin: 0, fontSize: 21, fontWeight: 500 }}>Cultural Multiverse · Positioning Arena</h3>
        <span className="mono-note">{multiverse.data_status.toUpperCase()} · {multiverse.calculation_version}</span>
      </div>
      <p style={{ color: "#a7a39b", fontSize: 12, lineHeight: 1.7 }}>
        One completed Creator run, existing evidence only. What-if priorities reorder these candidates without another Qloo request; they do not change evidence, predict audience behaviour, or create a causal counterfactual.
      </p>

      <fieldset style={{ border: 0, padding: 0, margin: "16px 0" }}>
        <legend className="micro-label">WHAT-IF DECISION PRIORITIES · ORDINAL PREFERENCE FORMULA v1</legend>
        <div style={{ display: "grid", gap: 10, marginTop: 8 }}>
          {DIMENSIONS.map(({ key, label, hint }) => {
            const supported = multiverse.strategies.some((strategy) => strategy.availability === "available" && strategy.dimensions[key].available);
            return (
              <label key={key} style={{ display: "grid", gridTemplateColumns: "minmax(180px, 1fr) minmax(100px, 2fr) 42px", alignItems: "center", gap: 10, color: supported ? "#b3aea4" : "#77736d", fontSize: 12 }}>
                <span>{label}<small style={{ display: "block", color: "#77736d" }}>{supported ? hint : "Unavailable in this run's evidence"}</small></span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={1}
                  value={policy[key]}
                  aria-label={`${label} priority`}
                  disabled={!supported}
                  onChange={(event) => onPolicyChange({ ...policy, [key]: Number(event.target.value) })}
                />
                <span className="mono-note">{supported ? policy[key] : "—"}</span>
              </label>
            );
          })}
        </div>
      </fieldset>
      <p className="mono-note" style={{ lineHeight: 1.7 }}>
        {ordering.notes.join(" ")} Preference weights: fit {policy.fit}, exploration {policy.exploration}, breadth {policy.breadth}. Each available dimension is normalized over ordinal positions only; unsupported dimensions are omitted and disclosed.
      </p>
      <ol aria-label="Current strategy preference order" style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.7 }}>
        {ordering.entries.map((entry) => {
          const baselineRank = baselineRanks.get(entry.strategy_id);
          const movement = baselineRank === undefined || baselineRank === entry.rank
            ? "same rank as default priorities"
            : entry.rank < baselineRank
              ? `moved up from default rank ${baselineRank}`
              : `moved down from default rank ${baselineRank}`;
          return (
              <li key={entry.strategy_id}>
                {entry.rank}. {entry.strategy_id.toUpperCase()} · {movement}
                {entry.preference_index === null ? " · source-rank tie-break" : ` · preference index ${entry.preference_index.toFixed(3)} (not a prediction)`}
                {` · ${entry.explanation}`}
                {Object.keys(entry.unavailable_dimensions).length > 0 && ` · unavailable: ${Object.keys(entry.unavailable_dimensions).join(", ")}`}
              </li>
          );
        })}
      </ol>

      <div style={{ display: "grid", gap: 12 }}>
        {ordered.map((strategy) => (
          <article key={strategy.id} style={{ padding: 14, border: "1px solid var(--rule)", borderRadius: 6, opacity: strategy.availability === "available" ? 1 : 0.72 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
              <strong>{strategy.type} · {strategy.availability === "available" ? "EVIDENCE AVAILABLE" : "UNAVAILABLE"}</strong>
              {strategy.availability === "available" && (
                <button type="button" aria-pressed={selectedId === strategy.id} onClick={() => onSelect(strategy.id)}>
                  {selectedId === strategy.id ? "Selected for Test Card" : "Select this strategy"}
                </button>
              )}
            </div>
            <p style={{ color: "#d1cbc0", lineHeight: 1.65 }}>{strategy.thesis}</p>
            {strategy.availability === "unavailable" ? (
              <p role="status">{strategy.unavailable_reason}</p>
            ) : (
              <>
                <p style={{ color: "#a7a39b", lineHeight: 1.65 }}>{strategy.creative_direction}</p>
                <p className="mono-note">DATA: {strategy.data_status.toUpperCase()} · EVIDENCE: {strategy.evidence_strength ?? "not available"} · SOURCE COHORTS: {strategy.source_cohort_ids.join(", ")}</p>
                <ul style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.7 }}>
                  {strategy.entity_refs.map((entity) => (
                    <li key={`${entity.cohort_id}:${entity.entity_id}`}>
                      {entity.name} · {entity.domain.replace("urn:entity:", "")} · Qloo cultural similarity {entity.affinity.toFixed(3)} · {entity.call_id}
                    </li>
                  ))}
                </ul>
                <div style={{ display: "grid", gap: 4, color: "#9b968d", fontSize: 11 }}>
                  {(Object.keys(strategy.dimensions) as PositioningDimensionName[]).map((key) => (
                    <div key={key}><span className="mono-note">{key.toUpperCase()}: </span>{formatDimension(strategy, key)}</div>
                  ))}
                </div>
                <p style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.65 }}><strong>Why selected:</strong> {strategy.why_selected}</p>
                {strategy.evidence_refs.map((evidence, index) => (
                  <p key={`${evidence.kind}-${index}`} className="mono-note" style={{ lineHeight: 1.6 }}>
                    EVIDENCE · {evidence.description} · calls {evidence.call_ids.join(", ") || "unavailable"} · entities {evidence.entity_ids.join(", ")}
                  </p>
                ))}
                <details>
                  <summary className="micro-label" style={{ cursor: "pointer" }}>EVIDENCE CHALLENGE · ATTRIBUTION {strategy.evidence_challenge.attribution_status.toUpperCase()}</summary>
                  <p className="mono-note" style={{ lineHeight: 1.6 }}>{strategy.evidence_challenge.attribution_detail}</p>
                  <p className="mono-note">MEMBER ATTRIBUTION STATES: {strategy.evidence_challenge.attribution_statuses.join(", ") || "missing"}</p>
                  <p className="mono-note">SOURCE INPUTS: {strategy.evidence_challenge.source_inputs.map((input) => `${input.title} [${input.resolution_status}]`).join(" · ") || "none returned"}</p>
                  {strategy.evidence_challenge.unresolved_references.length > 0 && <p className="mono-note">UNRESOLVED: {strategy.evidence_challenge.unresolved_references.join(", ")}</p>}
                  <ul style={{ color: "#9b968d", fontSize: 11, lineHeight: 1.6 }}>
                    {strategy.evidence_challenge.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                  </ul>
                  <p className="mono-note">A SUPPORTIVE OBSERVATION: {strategy.evidence_challenge.observation_that_supports}</p>
                  <p className="mono-note">A CONTRADICTING OBSERVATION: {strategy.evidence_challenge.observation_that_contradicts}</p>
                </details>
              </>
            )}
          </article>
        ))}
      </div>

      {selected && (
        <div aria-live="polite" style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--rule)" }}>
          <strong>POSITIONING BRIEF · {selected.type}</strong>
          <p>{selected.thesis}</p>
          <p>{selected.creative_direction}</p>
          <p><strong>Falsifiable hypothesis:</strong> {selected.falsifiable_hypothesis}</p>
          <p className="mono-note">Suggested plan: {selected.suggested_test.comparison_protocol} {selected.suggested_test.primary_measure} {selected.suggested_test.decision_rule} {selected.suggested_test.observation_window}</p>
          <p className="mono-note">Interpretation limits: {selected.tradeoffs.join(" ")}</p>
        </div>
      )}
    </section>
  );
}
