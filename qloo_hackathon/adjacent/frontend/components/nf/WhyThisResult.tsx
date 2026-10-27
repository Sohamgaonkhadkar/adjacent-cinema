"use client";

import type { BoundedAttribution, CohortMember, ProgrammeFilm } from "@/types/adjacent";
import { whyThisResult } from "@/lib/attribution";

/**
 * "Why this result?" — a restrained disclosure under a ranked cohort.
 *
 * Show: the provider's own contribution weights, the reference film each seed id
 * belongs to, the call that returned them, and an explicit unavailable state
 * when the provider returned nothing. Nothing here is generated prose about the
 * film, and no weight is described as audience size or causality.
 */
export function WhyThisResult({
  members,
  programme,
  bounded,
}: {
  members: CohortMember[] | null | undefined;
  programme: { items: ProgrammeFilm[] } | null | undefined;
  bounded?: BoundedAttribution | null;
}) {
  const view = whyThisResult(members, programme, bounded);

  return (
    <details className="mt-4 border border-line bg-ink-2/60 p-4" open={!view.available ? false : undefined}>
      <summary className="cursor-pointer font-mono text-[0.6rem] uppercase tracking-[0.14em] text-amber">
        Why this result? · provider attribution
      </summary>

      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-paper-2">{view.statement}</p>

      {view.available && (
        <ul className="mt-3 space-y-3">
          {view.contributors.map((contributor) => (
            <li key={contributor.entityName} className="border-t border-line pt-3 first:border-t-0 first:pt-0">
              <p className="text-sm text-paper">{contributor.entityName}</p>
              <ul className="mt-1 space-y-1">
                {contributor.seeds.map((seed, index) => (
                  <li
                    key={`${contributor.entityName}:${seed.label}:${index}`}
                    className="font-mono text-[0.58rem] uppercase tracking-[0.1em] text-mute"
                  >
                    {seed.label} · weight {seed.weight.toFixed(3)}
                  </li>
                ))}
              </ul>
              {contributor.callId && (
                <p className="mt-1 font-mono text-[0.56rem] uppercase tracking-[0.1em] text-dim">
                  {contributor.origin === "bounded" ? "bounded attribution call" : "scoring call"} ·{" "}
                  {contributor.callId}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      {view.note && <p className="caption mt-3">{view.note}</p>}

      <ul className="mt-2 space-y-1">
        {view.limits.map((limit) => (
          <li key={limit} className="text-[0.68rem] leading-relaxed text-dim">
            — {limit}
          </li>
        ))}
      </ul>
    </details>
  );
}
