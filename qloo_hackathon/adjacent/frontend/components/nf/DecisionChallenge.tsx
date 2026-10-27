"use client";

import { ArrowRight, Download, ShieldAlert, ShieldCheck } from "lucide-react";
import type { DecisionChallengeData } from "@/types/adjacent";
import { buildChallengeView, type ChallengeRow, type Tone } from "@/lib/challengeView";
import { DataChip } from "./Chips";
import { cn } from "@/lib/cn";

/**
 * Decision Challenge.
 *
 * Three answers in the order a sceptical reader asks them:
 *   1. would this recommendation survive without Qloo's affinity numbers,
 *   2. does it survive losing one of its own evidence items,
 *   3. what would actually close the gap that remains.
 *
 * Nothing here is generated prose about the film. Every number is printed by the
 * backend from this run's own cached evidence, and every claim can be checked
 * against the call ids that travel with it.
 */

const TONE_TEXT: Record<Tone, string> = {
  live: "text-amber",
  fixture: "text-paper-2",
  warn: "text-warn",
  fail: "text-blood",
  neutral: "text-paper-2",
};

function Row({ row }: { row: ChallengeRow }) {
  return (
    <li className="border-t border-line py-4 first:border-t-0 first:pt-0">
      <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-dim">{row.label}</p>
      <p className={cn("mt-2 max-w-2xl text-sm leading-relaxed", TONE_TEXT[row.tone])}>{row.detail}</p>
    </li>
  );
}

export type DecisionChallengeProps = {
  challenge: DecisionChallengeData | null | undefined;
  onExportReceipt: () => void;
  onGoToTest?: () => void;
};

export function DecisionChallenge({ challenge, onExportReceipt, onGoToTest }: DecisionChallengeProps) {
  const view = buildChallengeView(challenge);

  if (!view.available) {
    return (
      <div className="border border-dashed border-line-strong p-8">
        <span className="chip chip-unk">Not calculated</span>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">{view.unavailableReason}</p>
        <p className="caption mt-4">
          A challenge is only produced when there is a recommendation to challenge. It is never
          substituted with a placeholder analysis.
        </p>
      </div>
    );
  }

  const FragileIcon = view.stabilityVerdict === "fragile" ? ShieldAlert : ShieldCheck;

  return (
    <div className="grid gap-10 md:grid-cols-12">
      <div className="md:col-span-7">
        <div className="flex flex-wrap items-center gap-3">
          <DataChip status={view.dataStatus} />
          <span className="chip chip-interp">Diagnostic · not a forecast</span>
        </div>

        <h2 className="font-display mt-5 text-3xl leading-tight md:text-5xl">
          Would this decision survive being wrong?
        </h2>

        {view.statement && (
          <p className="mt-5 max-w-2xl text-sm leading-relaxed text-paper-2">{view.statement}</p>
        )}

        <h3 className="type-kicker mt-10">Necessity · what the taste signal did</h3>
        <ul className="mt-4">
          {view.necessityRows.map((row) => (
            <Row key={row.id} row={row} />
          ))}
        </ul>

        <h3 className="type-kicker mt-10">Stability · what happens if one item is wrong</h3>
        <div
          className={cn(
            "mt-4 flex items-start gap-3 border p-4",
            view.stabilityVerdict === "fragile" && "border-blood/40 bg-blood/10",
            view.stabilityVerdict === "stable" && "border-amber/40 bg-amber/5",
            view.stabilityVerdict === "undetermined" && "border-line bg-ink-2",
          )}
        >
          <FragileIcon className="mt-0.5 h-4 w-4 shrink-0 text-warn" aria-hidden />
          <div>
            <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-dim">
              {view.headline}
            </p>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-paper-2">{view.stabilityReason}</p>
            {view.stabilityRule && <p className="caption mt-2">{view.stabilityRule}</p>}
          </div>
        </div>

        {view.stabilityRows.length > 0 && (
          <ul className="mt-6">
            {view.stabilityRows.map((row) => (
              <Row key={row.id} row={row} />
            ))}
          </ul>
        )}

        {view.pairwise && (
          <>
            <h3 className="type-kicker mt-10">Comparison · how close are the two groups</h3>
            <div className="mt-4 border border-line bg-ink-2 p-4">
              <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-dim">
                {view.pairwise.label}
              </p>
              <p className={cn("mt-2 max-w-2xl text-sm leading-relaxed", TONE_TEXT[view.pairwise.tone])}>
                {view.pairwise.detail}
              </p>
              <p className="caption mt-2">
                {view.pairwise.callId
                  ? `Qloo call ${view.pairwise.callId} · /v2/analysis/compare`
                  : "No call was made for this comparison"}
              </p>
            </div>
          </>
        )}

        {view.skipped.length > 0 && (
          <details className="mt-6 border border-line bg-ink-2 p-4">
            <summary className="cursor-pointer font-mono text-[0.62rem] uppercase tracking-[0.16em] text-dim">
              {view.skipped.length} item{view.skipped.length === 1 ? "" : "s"} could not be tested
            </summary>
            <ul className="mt-3 space-y-2">
              {view.skipped.map((skip) => (
                <li key={skip.id} className="text-sm text-mute">
                  — {skip.text}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>

      <div className="md:col-span-5">
        <h3 className="type-kicker">What to investigate next</h3>
        <ul className="mt-4 space-y-4">
          {view.checks.length === 0 && (
            <li className="border border-line bg-ink-2 p-4 text-sm text-mute">
              No gap was identified from this run&rsquo;s own numbers. That is not a claim that the
              recommendation is correct — only that this run does not show where it is thin.
            </li>
          )}
          {view.checks.map((check) => (
            <li key={check.id} className="border border-line bg-ink-2 p-4">
              <p className="text-sm font-medium text-paper">{check.title}</p>
              <p className="mt-2 text-sm leading-relaxed text-mute">{check.detail}</p>
              <p className="mt-3 text-sm leading-relaxed text-paper-2">
                <span className="text-amber">Next · </span>
                {check.proposed_check.action}
              </p>
              <p className="caption mt-2">
                Addresses: {check.uncertainty_addressed}
                {check.proposed_check.operation
                  ? ` · ${check.proposed_check.operation}`
                  : ""}
                {check.proposed_check.estimated_qloo_calls
                  ? ` · ~${check.proposed_check.estimated_qloo_calls} Qloo ${check.proposed_check.estimated_qloo_calls === 1 ? "call" : "calls"}`
                  : " · no new Qloo call"}
              </p>
              {!check.proposed_check.available_now && check.proposed_check.unavailable_reason && (
                <p className="caption mt-1 text-warn">
                  Cannot be run from this build: {check.proposed_check.unavailable_reason}
                </p>
              )}
            </li>
          ))}
        </ul>

        <div className="mt-6 grid grid-cols-2 gap-px border border-line bg-line">
          {view.counts.map((count) => (
            <div key={count.label} className="bg-ink p-3">
              <p className="font-display text-2xl">{count.value}</p>
              <p className="caption mt-1">{count.label}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" className="test-card-export" onClick={onExportReceipt}>
            <span>Export decision receipt</span>
            <small>PLAIN TEXT · .TXT</small>
          </button>
          {onGoToTest && (
            <button
              type="button"
              onClick={onGoToTest}
              className="inline-flex items-center gap-2 border border-line-strong px-4 py-2 font-mono text-[0.62rem] uppercase tracking-[0.16em] text-paper-2 transition-colors hover:text-paper"
            >
              Turn this into a test
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </button>
          )}
        </div>

        {view.limits.length > 0 && (
          <details className="mt-6">
            <summary className="cursor-pointer font-mono text-[0.62rem] uppercase tracking-[0.16em] text-dim">
              Limits of this challenge
            </summary>
            <ul className="mt-3 space-y-2">
              {view.limits.map((limit) => (
                <li key={limit} className="text-sm leading-relaxed text-mute">
                  — {limit}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}

/** Inline badge for the Test chapter: the receipt's verdict travels with the test. */
export function ChallengeSummary({ challenge }: { challenge: DecisionChallengeData | null | undefined }) {
  const view = buildChallengeView(challenge);
  if (!view.available) return null;
  return (
    <div className="mt-4 border border-line bg-ink-2 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <span
          className={cn(
            "chip",
            view.stabilityVerdict === "fragile"
              ? "chip-warn"
              : view.stabilityVerdict === "stable"
                ? "chip-live"
                : "chip-unk",
          )}
        >
          Stability · {view.stabilityVerdict}
        </span>
        <span className="caption">
          {view.receipt?.stability.evaluated ?? 0} single-item removals tested ·{" "}
          {view.receipt?.stability.flips ?? 0} changed the recommendation
        </span>
      </div>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-mute">
        Recorded with this test so the experiment is judged against a decision whose fragility was
        known before screening, not after.
      </p>
      {view.checks.length > 0 && (
        <p className="mt-2 text-sm leading-relaxed text-paper-2">
          <span className="text-amber">Investigate first · </span>
          {view.checks[0].title}
        </p>
      )}
    </div>
  );
}

export function DownloadIcon() {
  return <Download className="h-3 w-3" aria-hidden />;
}
