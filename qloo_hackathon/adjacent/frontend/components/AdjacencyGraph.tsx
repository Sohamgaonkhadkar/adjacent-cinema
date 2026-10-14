"use client";

import { useMemo, useState } from "react";
import type { CulturalField, ProgrammeBetData } from "@/types/adjacent";

// ─── Cultural adjacency graph (M13.15) ─────────────────────────────────────
// Renders ONLY what the run actually established: ranked adjacent worlds from
// the Qloo pipeline, the positioning bet's primary/runner-up, and rejected
// worlds kept visible with their reason codes. No synthetic nodes, no invented
// affinities — an empty field renders as an honest empty state.

const W = 920;
const H = 540;
const CX = W / 2;
const CY = H / 2 + 8;

interface NodeDatum {
  key: string;
  label: string;
  domain: string;
  rank: number;
  memberCount: number;
  qualifyingCount: number | null;
  meanAffinity: number | null;
  members: { name: string; affinity: number | null }[];
  excludedCount: number;
  callId: string | null;
  role: "primary" | "runner-up" | "ranked";
}

function domainLabel(domain: string): string {
  return domain.replace("urn:entity:", "").replace(/_/g, " ");
}

export default function AdjacencyGraph({
  filmTitle,
  cohorts,
  bet,
  dataStatus,
}: {
  filmTitle: string;
  cohorts: CulturalField;
  bet: ProgrammeBetData | null;
  dataStatus: string;
}) {
  const [selected, setSelected] = useState<string | null>(null);

  const nodes: NodeDatum[] = useMemo(() => {
    return cohorts.ranked.map((c, i) => {
      const role: NodeDatum["role"] =
        bet?.primary && c.domain === bet.primary.domain
          ? "primary"
          : bet?.runner_up && c.domain === bet.runner_up.domain
            ? "runner-up"
            : "ranked";
      const callId =
        role === "primary"
          ? bet?.primary.call_id ?? null
          : role === "runner-up"
            ? bet?.runner_up?.call_id ?? null
            : null;
      return {
        key: c.cohort_id || `${c.domain}-${i}`,
        label: c.members?.find((m) => m.name)?.name ?? domainLabel(c.domain),
        domain: c.domain,
        rank: c.rank,
        memberCount: c.member_count,
        qualifyingCount: c.qualifying_count ?? null,
        meanAffinity: c.score?.mean_affinity ?? null,
        members: (c.members ?? []).slice(0, 6).map((m) => ({ name: m.name, affinity: m.affinity })),
        excludedCount: (c.excluded_members ?? []).length,
        callId,
        role,
      };
    });
  }, [cohorts, bet]);

  const maxMembers = Math.max(1, ...nodes.map((n) => n.memberCount));
  const placed = nodes.map((n, i) => {
    const angle = (i / Math.max(1, nodes.length)) * Math.PI * 2 - Math.PI / 2;
    const ring = 168 + (n.rank > 3 ? 46 : 0);
    return {
      node: n,
      x: CX + Math.cos(angle) * ring,
      y: CY + Math.sin(angle) * ring * 0.72,
      r: 16 + (n.memberCount / maxMembers) * 26,
    };
  });

  const rejected = cohorts.rejected ?? [];
  const active = placed.find((p) => p.node.key === selected) ?? null;

  if (nodes.length === 0) {
    return (
      <div className="agraph-empty">
        <span className="micro-label">Cultural fingerprint</span>
        <p>
          No adjacent cultural world passed the evidence gate in this run. Nothing is drawn
          because nothing was established — the investigation records why, and what would be
          needed to answer.
        </p>
      </div>
    );
  }

  return (
    <div className="agraph">
      <div className="agraph-canvas-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Adjacent cultural worlds around your film">
          {/* rejected worlds — visible on the outer edge, with reason codes */}
          {rejected.map((r, i) => {
            const angle = (i / Math.max(1, rejected.length)) * Math.PI * 2 + 0.4;
            const x = CX + Math.cos(angle) * 250;
            const y = CY + Math.sin(angle) * 190;
            return (
              <g key={r.cohort_id || `rej-${i}`} className="agraph-rejected">
                <circle cx={x} cy={y} r={7} />
                <text x={x} y={y - 12} textAnchor="middle">
                  {domainLabel(r.domain)} · {r.rejection_reason ?? "rejected"}
                </text>
              </g>
            );
          })}

          {/* edges */}
          {placed.map((p) => (
            <line
              key={`edge-${p.node.key}`}
              x1={CX}
              y1={CY}
              x2={p.x}
              y2={p.y}
              className={
                p.node.role === "primary"
                  ? "agraph-edge is-primary"
                  : p.node.role === "runner-up"
                    ? "agraph-edge is-runner"
                    : "agraph-edge"
              }
              style={{
                opacity: p.node.meanAffinity != null ? 0.25 + Math.min(0.6, p.node.meanAffinity) : 0.25,
              }}
            />
          ))}

          {/* center: the film */}
          <g className="agraph-center">
            <circle cx={CX} cy={CY} r={44} />
            <text x={CX} y={CY - 4} textAnchor="middle" className="agraph-center-title">
              {filmTitle.length > 18 ? `${filmTitle.slice(0, 17)}…` : filmTitle}
            </text>
            <text x={CX} y={CY + 14} textAnchor="middle" className="agraph-center-sub">
              YOUR FILM
            </text>
          </g>

          {/* ranked worlds */}
          {placed.map((p) => (
            <g
              key={p.node.key}
              className={`agraph-node${selected === p.node.key ? " is-selected" : ""}${
                p.node.role === "primary" ? " is-primary" : p.node.role === "runner-up" ? " is-runner" : ""
              }`}
              role="button"
              tabIndex={0}
              onClick={() => setSelected(selected === p.node.key ? null : p.node.key)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") setSelected(selected === p.node.key ? null : p.node.key);
              }}
              aria-label={`${p.node.label}, rank ${p.node.rank}`}
            >
              <circle cx={p.x} cy={p.y} r={p.r} />
              <text x={p.x} y={p.y - p.r - 10} textAnchor="middle" className="agraph-node-label">
                {p.node.label.length > 22 ? `${p.node.label.slice(0, 21)}…` : p.node.label}
              </text>
              <text x={p.x} y={p.y - p.r + 2} textAnchor="middle" className="agraph-node-meta">
                #{p.node.rank} · {domainLabel(p.node.domain)}
              </text>
              {p.node.meanAffinity != null && (
                <text x={p.x} y={p.y + 14} textAnchor="middle" className="agraph-node-meta">
                  affinity {p.node.meanAffinity.toFixed(2)}
                </text>
              )}
            </g>
          ))}
        </svg>
        {dataStatus !== "measured" && (
          <span className="agraph-stamp">FIXTURE DEMONSTRATION — NOT LIVE QLOO DATA</span>
        )}
      </div>

      <aside className="agraph-inspector" aria-live="polite">
        {!active && (
          <p className="agraph-inspector-hint">
            Select a world to inspect its evidence. Node size reflects member count; edge
            weight reflects measured mean affinity. Rejected worlds remain visible with their
            reason codes — exclusions are annotations, not deletions.
          </p>
        )}
        {active && (
          <>
            <span className="micro-label">
              {active.node.role === "primary"
                ? "Primary positioning target"
                : active.node.role === "runner-up"
                  ? "Runner-up world"
                  : `Ranked world #${active.node.rank}`}
            </span>
            <h4>{active.node.label}</h4>
            <dl className="agraph-facts">
              <div><dt>Domain</dt><dd>{domainLabel(active.node.domain)}</dd></div>
              <div><dt>Members</dt><dd>{active.node.memberCount}</dd></div>
              {active.node.qualifyingCount != null && (
                <div><dt>Qualifying</dt><dd>{active.node.qualifyingCount}</dd></div>
              )}
              {active.node.meanAffinity != null && (
                <div><dt>Mean affinity</dt><dd>{active.node.meanAffinity.toFixed(3)}</dd></div>
              )}
              {active.node.excludedCount > 0 && (
                <div><dt>Excluded (visible)</dt><dd>{active.node.excludedCount}</dd></div>
              )}
              {active.node.callId && (
                <div><dt>Evidence call</dt><dd className="mono-tiny">{active.node.callId}</dd></div>
              )}
            </dl>
            {active.node.members.length > 0 && (
              <>
                <span className="micro-label">Strongest members</span>
                <ul className="agraph-members">
                  {active.node.members.map((m) => (
                    <li key={m.name}>
                      {m.name}
                      {m.affinity != null && <span className="mono-tiny"> · {m.affinity.toFixed(2)}</span>}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p className="agraph-guard">
              Affinity is cultural similarity — not evidence this audience will watch the film.
            </p>
          </>
        )}
      </aside>
    </div>
  );
}
