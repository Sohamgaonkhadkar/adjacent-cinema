/**
 * View model for the Comparables Audit (Creator Mode).
 *
 * The backend decides what Qloo returned for a pair; this module only decides
 * how to say it. Two rules are enforced here, not in the component:
 *
 *   1. A pair with no readable value is reported as unevaluated — never as
 *      "these films are unrelated". The absence of a Qloo field is not evidence.
 *   2. A provider failure and an unreadable response are different states with
 *      different words, because one is about the provider and the other is about
 *      this build's reader.
 *
 * Pure and dependency-free so it can be unit-tested under Node.
 */

import type { ComparablesAudit, ComparablesPair } from "@/types/adjacent";

export type ComparablesTone = "live" | "fixture" | "warn" | "fail" | "neutral";

export interface ComparablesRow {
  id: string;
  pair: string;
  status: ComparablesPair["status"];
  statusLabel: string;
  tone: ComparablesTone;
  detail: string;
  metric: string | null;
  callId: string | null;
  /** Key names only, never values — the provider body never reaches the UI. */
  observedKeys: string[];
  resolutionCallIds: string[];
}

export interface ComparablesView {
  available: boolean;
  tone: ComparablesTone;
  status: ComparablesAudit["status"] | "missing";
  headline: string;
  statement: string;
  rows: ComparablesRow[];
  unresolved: string[];
  notEvaluated: string[];
  summary: string;
  limits: string[];
  dataStatus: string;
}

const STATUS_LABELS: Record<string, { label: string; tone: ComparablesTone }> = {
  measured: { label: "Measured", tone: "live" },
  no_readable_field: { label: "Unevaluated · no readable field", tone: "neutral" },
  not_modelled_in_fixture: { label: "Not modelled in the fixture", tone: "fixture" },
  failed: { label: "Upstream failure", tone: "fail" },
  unavailable_budget: { label: "Not compared · call budget", tone: "warn" },
  not_attempted_after_failure: { label: "Not attempted after a failure", tone: "warn" },
};

function pairName(a: string, b: string): string {
  return `${a} · ${b}`;
}

function metricLine(pair: ComparablesPair): string | null {
  const metric = pair.metric;
  if (!metric || typeof metric.value !== "number") return null;
  const direction =
    metric.direction === "higher_is_closer"
      ? "higher = more overlap"
      : metric.direction === "lower_is_closer"
        ? "lower = more overlap"
        : "direction not interpreted by this build";
  return `${metric.key} ${metric.value.toFixed(3)} · ${direction}`;
}

export function comparablesRow(pair: ComparablesPair, index: number): ComparablesRow {
  const meta = STATUS_LABELS[pair.status] ?? { label: pair.status, tone: "neutral" as const };
  return {
    id: `${pair.a.entity_id ?? pair.a.title}:${pair.b.entity_id ?? pair.b.title}:${index}`,
    pair: pairName(pair.a.title, pair.b.title),
    status: pair.status,
    statusLabel: meta.label,
    tone: meta.tone,
    detail: pair.reason,
    metric: metricLine(pair),
    callId: pair.call_id ?? null,
    observedKeys: pair.observed_keys ?? [],
    resolutionCallIds: [pair.a.resolution_call_id, pair.b.resolution_call_id].filter(
      (value): value is string => Boolean(value),
    ),
  };
}

export function buildComparablesView(
  audit: ComparablesAudit | null | undefined,
): ComparablesView {
  if (!audit) {
    return {
      available: false,
      tone: "neutral",
      status: "missing",
      headline: "Not run",
      statement:
        "No comparables audit is attached to this run. Nothing is inferred in its place — re-run the analysis to request one.",
      rows: [],
      unresolved: [],
      notEvaluated: [],
      summary: "",
      limits: [],
      dataStatus: "unknown",
    };
  }

  const rows = (audit.pairs ?? []).map(comparablesRow);
  const unresolved = (audit.unresolved_references ?? []).map(
    (item) => `${item.title}${item.year ? ` (${item.year})` : ""}`,
  );
  const notEvaluated = (audit.not_evaluated ?? []).map(
    (item) => `${item.a} · ${item.b}`,
  );

  const measured = rows.filter((row) => row.status === "measured").length;
  const summary =
    rows.length === 0
      ? ""
      : `${rows.length} pair${rows.length === 1 ? "" : "s"} compared, ${measured} returned a readable value.`;

  if (audit.status === "insufficient_input") {
    return {
      available: false,
      tone: "warn",
      status: audit.status,
      headline: "Not enough resolved references",
      statement: audit.reason,
      rows,
      unresolved,
      notEvaluated,
      summary,
      limits: audit.limits ?? [],
      dataStatus: audit.data_status,
    };
  }

  const tone: ComparablesTone =
    measured > 0 ? "live" : audit.data_status === "fixture" ? "fixture" : "neutral";
  const headline =
    measured > 0
      ? "Reference pairs Qloo could compare"
      : "Compares made, no readable value returned";

  return {
    available: audit.available,
    tone,
    status: audit.status,
    headline,
    statement: audit.reason,
    rows,
    unresolved,
    notEvaluated,
    summary,
    limits: audit.limits ?? [],
    dataStatus: audit.data_status,
  };
}
