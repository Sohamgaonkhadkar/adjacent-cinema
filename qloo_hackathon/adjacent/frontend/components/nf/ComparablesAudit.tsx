"use client";

import type { ComparablesAudit } from "@/types/adjacent";
import { buildComparablesView, type ComparablesTone } from "@/lib/comparables";
import { cn } from "@/lib/cn";

/**
 * Comparables Audit — challenge your assumptions.
 *
 * Sits inside Creator Studio's cultural-fingerprint chapter, beside the
 * provider attribution panel, because both answer the same kind of question:
 * *what did Qloo actually return about this programme?*
 *
 * Every row is one real `/v2/analysis/compare` call. A row with no numeric value
 * says so and says why; none of them ever reads as "these references are
 * unrelated". The section is quiet by design: one bordered block, no charts.
 */

const TONE_TEXT: Record<ComparablesTone, string> = {
  live: "text-amber",
  fixture: "text-paper-2",
  warn: "text-warn",
  fail: "text-blood",
  neutral: "text-paper-2",
};

export function ComparablesAuditPanel({
  audit,
}: {
  audit: ComparablesAudit | null | undefined;
}) {
  const view = buildComparablesView(audit);

  return (
    <div className="mt-10 border border-line p-5 md:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="type-kicker">Comparables audit · challenge your assumptions</p>
          <p className="mt-2 max-w-2xl text-xs leading-relaxed text-mute">
            Each row compares two of your reference films with Qloo. A row without a value is
            unevaluated — not a judgement that the two references are unrelated.
          </p>
        </div>
        {view.status !== "missing" && (
          <span className="font-mono text-[0.58rem] uppercase tracking-[0.12em] text-dim">
            {view.summary}
          </span>
        )}
      </div>

      {view.rows.length > 0 ? (
        <ul className="mt-5">
          {view.rows.map((row) => (
            <li key={row.id} className="border-t border-line py-4 first:border-t-0 first:pt-0">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-sm text-paper">{row.pair}</p>
                <span className="font-mono text-[0.58rem] uppercase tracking-[0.12em] text-dim">
                  {row.statusLabel}
                </span>
              </div>
              <p className={cn("mt-2 max-w-2xl text-sm leading-relaxed", TONE_TEXT[row.tone])}>
                {row.detail}
              </p>
              {row.metric && (
                <p className="mt-2 font-mono text-[0.62rem] uppercase tracking-[0.12em] text-amber">
                  {row.metric}
                </p>
              )}
              {(row.callId || row.resolutionCallIds.length > 0 || row.observedKeys.length > 0) && (
                <details className="mt-2">
                  <summary className="cursor-pointer font-mono text-[0.56rem] uppercase tracking-[0.12em] text-dim">
                    Trace
                  </summary>
                  <dl className="mt-2 space-y-1 font-mono text-[0.56rem] text-mute">
                    {row.callId && (
                      <div>
                        <dt className="inline text-dim">compare call · </dt>
                        <dd className="inline">{row.callId}</dd>
                      </div>
                    )}
                    {row.resolutionCallIds.length > 0 && (
                      <div>
                        <dt className="inline text-dim">resolution calls · </dt>
                        <dd className="inline">{row.resolutionCallIds.join(", ")}</dd>
                      </div>
                    )}
                    {row.observedKeys.length > 0 && (
                      <div>
                        <dt className="inline text-dim">fields returned · </dt>
                        <dd className="inline">{row.observedKeys.join(", ")}</dd>
                      </div>
                    )}
                  </dl>
                </details>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-5 max-w-2xl text-sm leading-relaxed text-mute">{view.statement}</p>
      )}

      {view.unresolved.length > 0 && (
        <p className="mt-4 text-xs leading-relaxed text-mute">
          Not compared because they did not resolve to a verified Qloo entity:{" "}
          {view.unresolved.join(", ")}.
        </p>
      )}

      {view.notEvaluated.length > 0 && (
        <p className="mt-2 text-xs leading-relaxed text-dim">
          Left out to keep the audit bounded ({audit?.not_evaluated_count ?? view.notEvaluated.length}{" "}
          pair{view.notEvaluated.length === 1 ? "" : "s"}): {view.notEvaluated.join("; ")}.
        </p>
      )}

      {view.limits.length > 0 && (
        <details className="mt-4">
          <summary className="cursor-pointer font-mono text-[0.58rem] uppercase tracking-[0.12em] text-dim">
            Limits of this audit
          </summary>
          <ul className="mt-2 space-y-1 text-xs leading-relaxed text-mute">
            {view.limits.map((limit) => (
              <li key={limit}>— {limit}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
