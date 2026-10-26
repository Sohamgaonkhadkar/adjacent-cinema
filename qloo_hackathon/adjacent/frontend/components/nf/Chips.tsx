"use client";

import type { ClaimKind } from "@/types/nf";
import { cn } from "@/lib/cn";

/**
 * Claim / data / run chips ported from the source ZIP
 * (src/components/ClaimChip.tsx), extended with the real backend's
 * status vocabulary ("measured", "insufficient", "cancelled", …).
 * A chip never invents a status: unknown values render as UNKNOWN.
 */

export function ClaimChip({ kind }: { kind: ClaimKind }) {
  const map: Record<ClaimKind, string> = {
    FACT: "chip chip-fact",
    INTERPRETATION: "chip chip-interp",
    HYPOTHESIS: "chip chip-hyp",
    UNKNOWN: "chip chip-unk",
  };
  return <span className={map[kind]}>{kind}</span>;
}

export function DataChip({ status }: { status: string | null | undefined }) {
  if (status === "measured" || status === "live") {
    return <span className="chip chip-live">Measured Qloo data</span>;
  }
  if (status === "fixture" || status === "demo") {
    return <span className="chip chip-fixture">Fixture · not live</span>;
  }
  if (status === "unavailable") return <span className="chip chip-warn">Unavailable</span>;
  if (status === "insufficient") return <span className="chip chip-warn">Insufficient evidence</span>;
  if (status === "failed") return <span className="chip chip-fail">Failed</span>;
  return <span className="chip chip-unk">Unknown status</span>;
}

const RUN_LABEL: Record<string, string> = {
  idle: "Idle",
  pending: "Queued",
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  insufficient: "Insufficient evidence",
  failed: "Failed",
  cancelled: "Cancelled",
  unavailable: "Unavailable",
};

export function RunChip({ status }: { status: string | null | undefined }) {
  if (!status) return <span className="chip chip-unk">No run</span>;
  return (
    <span
      className={cn(
        "chip",
        status === "completed" && "chip-live",
        (status === "running" || status === "pending" || status === "queued") && "chip-fact",
        (status === "failed" || status === "cancelled") && "chip-fail",
        (status === "insufficient" || status === "unavailable") && "chip-warn",
        status === "idle" && "chip-unk",
      )}
    >
      {RUN_LABEL[status] ?? status.toUpperCase()}
    </span>
  );
}

export function VerdictChip({ verdict }: { verdict: string }) {
  const cls =
    verdict === "SUPPORTED" ? "chip-live" : verdict === "CONTRADICTED" ? "chip-fail" : "chip-warn";
  return <span className={cn("chip", cls)}>{verdict}</span>;
}

export function ObservationChip({ kind }: { kind: string }) {
  return <span className="chip chip-interp">{kind}</span>;
}

export function SourceStatusChip({ status }: { status: string }) {
  const cls =
    status === "measured"
      ? "chip-live"
      : status === "fixture"
        ? "chip-fixture"
        : "chip-warn";
  return (
    <span className={cn("chip", cls)}>
      {status === "measured" ? "Measured run" : status === "fixture" ? "Fixture run" : "Status unknown"}
    </span>
  );
}
