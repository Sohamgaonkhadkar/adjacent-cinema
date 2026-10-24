"use client";

import { useMemo, useState } from "react";
import type { FingerprintNode } from "@/types/nf";
import { ClaimChip, DataChip } from "./Chips";

/**
 * Cultural Fingerprint ported from the source ZIP
 * (src/components/CulturalFingerprint.tsx).
 *
 * The layout, inspector and keyboard model are the source design. The nodes are
 * no longer fixture data: they are derived from a completed backend run by
 * `buildFingerprintNodes`, and an empty field renders as an honest empty state.
 */

type Pos = { x: number; y: number };

function polar(i: number, n: number, r: number, rot = -Math.PI / 2): Pos {
  const a = rot + (i / Math.max(n, 1)) * Math.PI * 2;
  return { x: 50 + r * Math.cos(a), y: 50 + r * Math.sin(a) };
}

export function CulturalFingerprint({
  nodes,
  filmTitle,
  dataStatus,
  emptyBody,
}: {
  nodes: FingerprintNode[];
  filmTitle: string;
  dataStatus: string | null | undefined;
  emptyBody?: string;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [focusIndex, setFocusIndex] = useState(0);

  const cohorts = nodes.filter((node) => node.kind === "cohort" && !node.rejected);
  const rejected = nodes.filter((node) => node.rejected);
  const entities = nodes.filter((node) => node.kind === "entity" || node.kind === "tag");
  const selected = nodes.find((node) => node.id === selectedId) ?? null;

  const layout = useMemo(() => {
    const map: Record<string, Pos> = { film: { x: 50, y: 50 } };
    cohorts.forEach((cohort, index) => {
      map[cohort.id] = polar(index, cohorts.length, 28);
    });
    entities.forEach((entity, index) => {
      map[entity.id] = polar(index, entities.length, 42, -Math.PI / 3);
    });
    return map;
  }, [cohorts, entities]);

  const selectable = [...cohorts, ...entities];

  // Every rendered node is individually focusable and activatable with the
  // keyboard, so the graph is not a mouse-only surface.
  const nodeKeyDown = (nodeId: string, index: number) => (event: React.KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setSelectedId(nodeId);
      setFocusIndex(index);
    }
  };
  const related = new Set(selected?.related ?? []);
  if (selected) related.add(selected.id);

  const onKey = (event: React.KeyboardEvent) => {
    if (!selectable.length) return;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      const next = (focusIndex + 1) % selectable.length;
      setFocusIndex(next);
      setSelectedId(selectable[next].id);
    }
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      const next = (focusIndex - 1 + selectable.length) % selectable.length;
      setFocusIndex(next);
      setSelectedId(selectable[next].id);
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setSelectedId(selectable[focusIndex]?.id ?? null);
    }
    if (event.key === "Escape") setSelectedId(null);
  };

  if (!nodes.length) {
    return (
      <div className="border border-line px-6 py-16 text-center">
        <p className="type-kicker">Cultural Fingerprint</p>
        <p className="font-display mx-auto mt-4 max-w-md text-3xl">No cultural field yet.</p>
        <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-mute">
          {emptyBody ??
            "A completed investigation places this film at the centre and arranges the cohorts it actually returned. Empty is not a fake graph."}
        </p>
      </div>
    );
  }

  return (
    <div className="border border-line bg-ink-2">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <p className="type-kicker">Cultural Fingerprint</p>
          <h3 className="font-display mt-1 text-2xl md:text-3xl">Atlas of returned worlds</h3>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <DataChip status={dataStatus} />
          <span className="caption">Arrow keys inspect · Enter selects</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_320px]">
        <div
          className="relative min-h-[420px] p-3 md:min-h-[540px] md:p-6"
          tabIndex={0}
          role="application"
          aria-label="Cultural fingerprint graph"
          onKeyDown={onKey}
        >
          <svg viewBox="0 0 100 100" className="h-full w-full" role="img" aria-label="Cultural field">
            <circle cx="50" cy="50" r="28" fill="none" stroke="rgba(233,228,218,0.08)" strokeWidth="0.15" />
            <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(233,228,218,0.06)" strokeWidth="0.15" />
            <circle cx="50" cy="50" r="8" fill="none" stroke="rgba(194,154,110,0.35)" strokeWidth="0.2" />

            {cohorts.flatMap((cohort) =>
              (cohort.related ?? [])
                .filter((id) => layout[id] && layout[cohort.id])
                .map((id) => {
                  const a = layout[cohort.id];
                  const b = layout[id];
                  const active = !selected || (related.has(cohort.id) && related.has(id));
                  return (
                    <line
                      key={`${cohort.id}-${id}`}
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke={active ? "rgba(194,154,110,0.45)" : "rgba(233,228,218,0.08)"}
                      strokeWidth={active ? 0.22 : 0.1}
                    />
                  );
                }),
            )}

            <g>
              <text
                x="50"
                y="49.2"
                textAnchor="middle"
                fill="#e9e4da"
                fontSize="3.2"
                fontFamily="Instrument Serif, serif"
              >
                {filmTitle.length > 18 ? `${filmTitle.slice(0, 16)}…` : filmTitle}
              </text>
              <text
                x="50"
                y="53.2"
                textAnchor="middle"
                fill="#c29a6e"
                fontSize="1.6"
                fontFamily="IBM Plex Mono, monospace"
                letterSpacing="0.12"
              >
                SUBJECT
              </text>
            </g>

            {cohorts.map((cohort, index) => {
              const p = layout[cohort.id];
              const isSelected = selectedId === cohort.id;
              const dim = selected && !related.has(cohort.id);
              return (
                <g
                  key={cohort.id}
                  className="graph-node"
                  role="button"
                  tabIndex={0}
                  aria-label={`${cohort.label}, cohort · ${cohort.domain ?? "domain unavailable"}${
                    typeof cohort.affinity === "number"
                      ? `, affinity ${cohort.affinity.toFixed(2)}`
                      : ", no affinity score"
                  }`}
                  opacity={dim ? 0.28 : 1}
                  onClick={() => {
                    setSelectedId(cohort.id);
                    setFocusIndex(index);
                  }}
                  onKeyDown={nodeKeyDown(cohort.id, index)}
                >
                  <title>{cohort.label}</title>
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={isSelected ? 2.1 : 1.35}
                    fill={isSelected ? "#c29a6e" : "#090909"}
                    stroke="#c29a6e"
                    strokeWidth="0.28"
                  />
                  <text
                    x={p.x}
                    y={p.y - 3.1}
                    textAnchor="middle"
                    fill={isSelected ? "#e0c49a" : "#e9e4da"}
                    fontSize="2.05"
                    fontFamily="DM Sans, sans-serif"
                  >
                    {cohort.label.length > 26 ? `${cohort.label.slice(0, 24)}…` : cohort.label}
                  </text>
                  {cohort.domain && (
                    <text
                      x={p.x}
                      y={p.y + 3.6}
                      textAnchor="middle"
                      fill="#8a8478"
                      fontSize="1.4"
                      fontFamily="IBM Plex Mono, monospace"
                    >
                      {cohort.domain}
                      {typeof cohort.affinity === "number" ? ` · ${cohort.affinity.toFixed(2)}` : " · no score"}
                    </text>
                  )}
                </g>
              );
            })}

            {entities.map((entity, index) => {
              const p = layout[entity.id];
              const isSelected = selectedId === entity.id;
              const dim = selected && !related.has(entity.id);
              return (
                <g
                  key={entity.id}
                  className="graph-node"
                  role="button"
                  tabIndex={0}
                  aria-label={`${entity.label}, ${entity.kind === "tag" ? "tag" : "member"}${
                    entity.domain ? ` of ${entity.domain}` : ""
                  }`}
                  opacity={dim ? 0.22 : 0.9}
                  onClick={() => {
                    setSelectedId(entity.id);
                    setFocusIndex(cohorts.length + index);
                  }}
                  onKeyDown={nodeKeyDown(entity.id, cohorts.length + index)}
                >
                  <title>{entity.label}</title>
                  <rect
                    x={p.x - 0.7}
                    y={p.y - 0.7}
                    width="1.4"
                    height="1.4"
                    fill={isSelected ? "#c29a6e" : "#e9e4da"}
                  />
                  <text
                    x={p.x}
                    y={p.y + 2.6}
                    textAnchor="middle"
                    fill="#d4cec2"
                    fontSize="1.55"
                    fontFamily="DM Sans, sans-serif"
                  >
                    {entity.label.length > 18 ? `${entity.label.slice(0, 16)}…` : entity.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        <aside className="border-t border-line lg:border-l lg:border-t-0">
          {selected ? (
            <div className="drawer-enter flex h-full flex-col p-5">
              <p className="type-meta">{selected.kind}</p>
              <h4 className="font-display mt-2 text-2xl leading-tight">{selected.label}</h4>
              <div className="mt-3 flex flex-wrap gap-2">
                <ClaimChip kind={selected.claim} />
                {selected.domain && <span className="chip chip-unk">{selected.domain}</span>}
              </div>
              <p className="mt-4 text-sm leading-relaxed text-paper-2">{selected.note}</p>
              {typeof selected.affinity === "number" && (
                <p className="mt-4 text-xs text-mute">
                  Affinity {selected.affinity.toFixed(2)} — cultural similarity, not audience size.
                </p>
              )}
              {selected.sourceCallId && (
                <p className="mt-2 font-mono text-[0.65rem] text-dim">
                  Source call · {selected.sourceCallId}
                </p>
              )}
              {selected.members && selected.members.length > 0 && (
                <ul className="mt-4 space-y-1 border-t border-line pt-4">
                  {selected.members.map((member, index) => (
                    <li key={`${member}-${index}`} className="font-mono text-xs tracking-wide text-paper-2">
                      {member}
                    </li>
                  ))}
                </ul>
              )}
              <button
                type="button"
                className="btn-ghost mt-auto self-start"
                onClick={() => setSelectedId(null)}
              >
                Clear selection
              </button>
            </div>
          ) : (
            <div className="flex h-full flex-col justify-between p-5 text-sm text-mute">
              <div>
                <p className="type-kicker">Inspector</p>
                <p className="mt-3 leading-relaxed">
                  Select a cohort, tag or entity to read its claim type, source call, and limits.
                  Proximity is layout, not a hidden score.
                </p>
              </div>
              <p className="caption">Edges exist only where the analysis recorded a relation.</p>
            </div>
          )}
        </aside>
      </div>

      <div className="border-t border-line px-5 py-5">
        <p className="type-meta">Reading key</p>
        <dl className="mt-3 grid gap-3 text-xs leading-relaxed text-mute sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-paper-2">Programme anchor</dt>
            <dd>The film or programme at the centre — not a score.</dd>
          </div>
          <div>
            <dt className="text-paper-2">Cultural connection</dt>
            <dd>A ranked cohort the analysis returned, with its domain and affinity.</dd>
          </div>
          <div>
            <dt className="text-paper-2">Member / tag</dt>
            <dd>A provider entity or a matched theme tag, never a generated label.</dd>
          </div>
          <div>
            <dt className="text-paper-2">Rejected</dt>
            <dd>Considered and not admitted, kept visible with its reason.</dd>
          </div>
        </dl>
        <p className="caption mt-4">
          Position is layout, not a hidden score. The parent cohorts of a selected node are listed
          in the inspector, and an empty field is reported as empty.
        </p>
      </div>

      {rejected.length > 0 && (
        <div className="border-t border-line px-5 py-4">
          <p className="type-meta">Rejected or insufficient</p>
          <ul className="mt-3 space-y-2">
            {rejected.map((node) => (
              <li key={node.id} className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-sm text-paper-2">{node.label}</span>
                <span className="caption">{node.rejectReason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Small illustrative layout used only by the home page's fingerprint teaser. */
export function MiniFingerprint({ filmTitle, labels }: { filmTitle: string; labels: string[] }) {
  return (
    <svg viewBox="0 0 100 64" className="h-full w-full" aria-hidden="true">
      <circle cx="50" cy="32" r="18" fill="none" stroke="rgba(233,228,218,0.12)" strokeWidth="0.3" />
      <circle cx="50" cy="32" r="6" fill="none" stroke="rgba(194,154,110,0.5)" strokeWidth="0.3" />
      <text x="50" y="31.5" textAnchor="middle" fill="#e9e4da" fontSize="3.4" fontFamily="Instrument Serif, serif">
        {filmTitle}
      </text>
      {labels.slice(0, 5).map((label, index) => {
        const angle = -Math.PI / 2 + (index / 5) * Math.PI * 2;
        const x = 50 + 26 * Math.cos(angle);
        const y = 32 + 22 * Math.sin(angle);
        return (
          <g key={label}>
            <circle cx={x} cy={y} r="1.1" fill="none" stroke="#c29a6e" strokeWidth="0.3" />
            <text
              x={x}
              y={y + 3.4}
              textAnchor="middle"
              fill="#d4cec2"
              fontSize="2.1"
              fontFamily="DM Sans, sans-serif"
            >
              {label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
