"use client";

import { Download, Lock, Pencil } from "lucide-react";
import type { TestCardData } from "@/types/adjacent";
import type { TestDesign, TestDesignField } from "@/lib/testCardDesign";
import { DataChip } from "./Chips";
import { Field, TextArea } from "./Field";

/**
 * Test Card ported from the source ZIP (src/components/TestCard.tsx).
 *
 * The paper-sheet composition, sprocket rules and read/edit modes are the
 * source design. The content is the backend's returned Test Card plus the
 * creator's own experiment design; the export writes exactly what is shown.
 */

/** Source field → design field mapping kept in one place for export parity. */
const DESIGN_FIELDS: Array<{ field: TestDesignField; label: string; hint: string }> = [
  {
    field: "comparison_protocol",
    label: "Comparison protocol",
    hint: "How two frames will be compared. Randomised only if the platform actually supports it.",
  },
  {
    field: "primary_measure",
    label: "Primary measure",
    hint: "One observable. Zero is zero. Missing stays missing.",
  },
  {
    field: "decision_rule",
    label: "Decision rule",
    hint: "Set by you before launch. The product does not invent a success threshold.",
  },
  {
    field: "observation_window",
    label: "Observation window",
    hint: "When the comparison is allowed to close.",
  },
];

export type TestCardProps = {
  card: TestCardData;
  design: TestDesign;
  editing: boolean;
  hypothesis: string;
  hypothesisNote?: string;
  onChange: (field: TestDesignField, value: string) => void;
  onToggleEdit: () => void;
  onExport: () => void;
};

export function TestCard({
  card,
  design,
  editing,
  hypothesis,
  hypothesisNote,
  onChange,
  onToggleEdit,
  onExport,
}: TestCardProps) {
  return (
    <article className="paper-card relative overflow-hidden">
      <div className="pointer-events-none absolute inset-y-0 left-0 w-3 bg-[repeating-linear-gradient(to_bottom,transparent_0_10px,#c29a6e_10px_12px,transparent_12px_22px)] opacity-40" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-3 bg-[repeating-linear-gradient(to_bottom,transparent_0_10px,#c29a6e_10px_12px,transparent_12px_22px)] opacity-40" />

      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-ink/10 px-6 py-5 md:px-10">
        <div>
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-amber-2">
            Test Card · planned experiment
          </p>
          <h3 className="font-display mt-2 text-3xl leading-none md:text-4xl">
            {card.title || "Untitled investigation"}
          </h3>
          <p className="mt-2 max-w-xl text-sm text-ink/60">
            A production notebook, not a result. Saving records a plan — it does not run the
            experiment.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <DataChip status={card.data_status} />
          <span className="chip" style={{ color: "#5c574e" }}>
            {editing ? "Editing" : "Read"}
          </span>
        </div>
      </header>

      <div className="space-y-7 px-6 py-7 md:px-10">
        <div>
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-amber-2">
            Hypothesis
          </p>
          <p className="mt-2 text-[0.95rem] leading-relaxed text-ink/85">
            {hypothesis || "— not yet written —"}
          </p>
          {hypothesisNote && (
            <p className="mt-2 font-mono text-[0.58rem] uppercase tracking-[0.12em] text-ink/45">
              {hypothesisNote}
            </p>
          )}
        </div>

        <SheetSection label="Programme context" value={card.programme_context} />
        <SheetSection label="Cultural bridge" value={card.cultural_bridge} />
        <SheetSection label="Geographic signal" value={card.geographic_signal} />
        <SheetSection label="Programming direction" value={card.programming_direction} />
        <SheetSection label="Primary evidence" value={card.primary_evidence} />
        <SheetSection label="Runner-up direction" value={card.runner_up} />
        <SheetSection label="Observable success criteria" value={card.success_criteria} />

        <div className="border-t border-ink/10 pt-6">
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-amber-2">
            Pre-registered experiment design
          </p>
          <p className="mt-1 text-xs leading-relaxed text-ink/50">
            Edit these before you export or save. They are the design you are committing to, not a
            result.
          </p>
          <div className="mt-4 space-y-5">
            {DESIGN_FIELDS.map(({ field, label, hint }) => (
              <div key={field}>
                {editing ? (
                  <Field label={label} hint={hint}>
                    <TextArea
                      className="border-ink/20 text-ink placeholder:text-ink/30"
                      value={design[field]}
                      onChange={(event) => onChange(field, event.target.value)}
                    />
                  </Field>
                ) : (
                  <>
                    <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-amber-2">
                      {label}
                    </p>
                    <p className="mt-2 text-[0.95rem] leading-relaxed text-ink/85">
                      {design[field] || "— not yet written —"}
                    </p>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-amber-2">
            Falsification
          </p>
          <p className="mt-2 text-[0.95rem] leading-relaxed text-ink/85">
            {card.falsification_condition || "— not yet written —"}
          </p>
          <p className="mt-2 font-mono text-[0.55rem] uppercase tracking-[0.12em] text-ink/40">
            Written by the analysis, before any results arrive
          </p>
        </div>
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-ink/10 px-6 py-4 md:px-10">
        <p className="font-mono text-[0.58rem] uppercase tracking-[0.12em] text-ink/45">
          PLAIN TEXT · .TXT · Affinity ≠ audience · plan ≠ outcome
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-ghost !border-ink/20 !text-ink" onClick={onToggleEdit}>
            {editing ? <Lock size={14} /> : <Pencil size={14} />}
            {editing ? "Lock card" : "Edit card"}
          </button>
          <button type="button" className="btn-primary" onClick={onExport}>
            <Download size={14} />
            Export .txt
          </button>
        </div>
      </footer>
    </article>
  );
}

function SheetSection({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div>
      <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-amber-2">{label}</p>
      <p className="mt-2 text-[0.95rem] leading-relaxed text-ink/85">{value}</p>
    </div>
  );
}
