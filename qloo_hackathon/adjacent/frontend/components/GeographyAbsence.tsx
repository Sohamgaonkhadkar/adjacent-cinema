import type { GeographyView } from "@/lib/geographyView";

type AbsenceView = Extract<GeographyView, { mode: "unmapped" | "absent" }>;

/**
 * The geography panel when there is nothing to draw.
 *
 * The failure this replaces was a large dashed rectangle holding a single
 * caption: visually broken, and — worse — it said "no usable coordinates
 * returned" even when the run had returned cells that simply carried no
 * affinity score. This panel instead states what came back, in the same
 * editorial register as the rest of the chapter, so an absent map reads as a
 * measured result rather than a rendering failure.
 *
 * It never draws a coordinate that was not returned.
 */
export function GeographyAbsence({
  view,
  city,
  callId,
  note,
}: {
  view: AbsenceView;
  city: string;
  callId: string | null;
  note: string;
}) {
  const facts = [
    { label: "City context", value: city || "Recorded per run" },
    { label: "Cells returned", value: String(view.returned) },
    { label: "With affinity", value: "0" },
    { label: "Map / pins", value: "Not drawn" },
  ];

  return (
    <div
      data-geography-absence={view.mode}
      className="flex min-h-[280px] flex-col justify-between border border-line bg-ink-3 p-5 md:p-6"
    >
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="caption text-dim">Geographic layer · not drawn</p>
          <span className="chip chip-warn">No pins</span>
        </div>
        <p className="font-display mt-4 text-2xl leading-tight text-paper">{view.headline}</p>
        <p className="mt-3 max-w-md text-sm leading-relaxed text-paper-2">{view.body}</p>
      </div>

      <div>
        <dl className="mt-6 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line pt-4">
          {facts.map((fact) => (
            <div key={fact.label}>
              <dt className="caption">{fact.label}</dt>
              <dd className="mt-1 font-mono text-[0.72rem] uppercase tracking-[0.08em] text-paper-2">
                {fact.value}
              </dd>
            </div>
          ))}
        </dl>
        {note && <p className="caption mt-4 text-dim">Provider note · {note}</p>}
        {callId && <p className="mt-2 font-mono text-[0.6rem] text-dim">CALL {callId}</p>}
      </div>
    </div>
  );
}
