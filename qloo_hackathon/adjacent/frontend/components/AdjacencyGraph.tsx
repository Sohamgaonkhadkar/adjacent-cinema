"use client";

import { useMemo, useState } from "react";
import type { CulturalField, ProgrammeBetData, TraceRow } from "@/types/adjacent";
import { traceAnchorId } from "@/components/EvidenceTrace";

// ─── Cultural adjacency graph (M13.15) ─────────────────────────────────────
// Renders ONLY what the run actually established: ranked adjacent worlds from
// the Qloo pipeline, the positioning bet's primary/runner-up, and rejected
// worlds kept visible with their reason codes. No synthetic nodes, no invented
// affinities — an empty field renders as an honest empty state.

const W = 1120;
const H = 700;
const CX = W / 2;
const CY = H / 2;

interface NodeDatum {
  key: string;
  label: string;
  domain: string;
  kindLabel: string;
  constructionReason: string | null;
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

function comparableName(value: string | null | undefined): string {
  return value?.trim().toLowerCase() ?? "";
}

function cohortKindLabel(kind: string | undefined, subtype: string | undefined, domain: string): string {
  if (kind === "subtype_group" && subtype) return `Qloo subtype · ${subtype}`;
  if (kind === "tag_cluster") return "Shared Qloo tag group";
  if (kind === "domain_group") return "Domain-only group";
  if (kind === "singleton_group") return "Single candidate";
  return domainLabel(domain);
}

export default function AdjacencyGraph({
  filmTitle,
  cohorts,
  bet,
  dataStatus,
  traceRows,
}: {
  filmTitle: string;
  cohorts: CulturalField;
  bet: ProgrammeBetData | null;
  dataStatus: string;
  traceRows: TraceRow[];
}) {
  const [selected, setSelected] = useState<string | null>(null);

  const nodes: NodeDatum[] = useMemo(() => {
    return cohorts.ranked.map((c, i) => {
      const memberLabel = c.members?.find((m) => m.name)?.name ?? domainLabel(c.domain);
      // Distinguish same-domain cohorts without changing their underlying rank.
      const groupingHint = c.construction_evidence?.subtype
        ?? c.construction_reason
        ?? (c.kind && c.kind !== "domain_group" ? c.kind.replace(/_/g, " ") : null);
      const label = groupingHint && !memberLabel.toLowerCase().includes(groupingHint.toLowerCase())
        ? `${memberLabel} · ${groupingHint}`
        : memberLabel;
      const isPrimary = bet?.primary
        ? bet.primary.cohort_id
          ? bet.primary.cohort_id === c.cohort_id
          : bet.primary.domain === c.domain && comparableName(bet.primary.cohort_name) === comparableName(label)
        : false;
      const isRunnerUp = bet?.runner_up
        ? bet.runner_up.domain === c.domain && comparableName(bet.runner_up.cohort_name) === comparableName(label)
        : false;
      const role: NodeDatum["role"] = isPrimary ? "primary" : isRunnerUp ? "runner-up" : "ranked";
      const contextCallId = traceRows.find((row) => row.tool === `score_context:${c.domain}`)?.call_id ?? null;
      const callId =
        (role === "primary" ? bet?.primary?.call_id : role === "runner-up" ? bet?.runner_up?.call_id : null) ??
        contextCallId;
      return {
        key: c.cohort_id || `${c.domain}-${i}`,
        label,
        domain: c.domain,
        kindLabel: cohortKindLabel(c.kind, c.construction_evidence?.subtype, c.domain),
        constructionReason: c.construction_reason ?? null,
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
  }, [cohorts, bet, traceRows]);

  const maxMembers = Math.max(1, ...nodes.map((n) => n.memberCount));
  const placed = nodes.map((n, i) => {
    const angle = (i / Math.max(1, nodes.length)) * Math.PI * 2 - Math.PI / 2;
    const ring = 168 + (n.rank > 3 ? 18 : 0);
    return {
      node: n,
      angle,
      x: CX + Math.cos(angle) * ring,
      y: CY + Math.sin(angle) * ring * 0.76,
      r: 6 + (n.memberCount / maxMembers) * 3,
    };
  });

  // Outer nodes are real members returned in each ranked cohort — never synthetic recommendations.
  const memberNodes = placed.flatMap((parent) =>
    parent.node.members.slice(0, 2).map((member, index) => {
      const angle = parent.angle + (parent.node.members.length > 1 ? (index === 0 ? -0.085 : 0.085) : 0);
      return {
        key: "member-" + parent.node.key + "-" + member.name + "-" + index,
        parentKey: parent.node.key,
        name: member.name,
        affinity: member.affinity,
        angle,
        x: CX + Math.cos(angle) * 296,
        y: CY + Math.sin(angle) * 216,
      };
    })
  );

  const rejected = cohorts.rejected ?? [];
  const active = placed.find((p) => p.node.key === selected) ?? null;
  const activeTrace = active?.node.callId
    ? traceRows.find((row) => row.call_id === active.node.callId) ?? null
    : null;

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
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="group"
          aria-label={`Interactive cultural fingerprint for ${filmTitle}. Use Tab to select a ranked cultural world.`}
        >
          <title>Adjacent cultural worlds around {filmTitle}</title>
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

          {/* Second orbit: links to actual entities nested inside the ranked cohorts. */}
          {memberNodes.map((member) => {
            const parent = placed.find((item) => item.node.key === member.parentKey);
            if (!parent) return null;
            return (
              <path
                key={"member-edge-" + member.key}
                d={"M " + parent.x + " " + parent.y + " Q " + ((parent.x + member.x) / 2 + (Math.cos(member.angle) > 0 ? 7 : -7)) + " " + ((parent.y + member.y) / 2) + " " + member.x + " " + member.y}
                className="agraph-member-edge"
                style={{ opacity: member.affinity == null ? 0.32 : 0.24 + Math.min(0.42, Math.max(0, member.affinity)) }}
              />
            );
          })}

          {/* center: the film */}
          <g className="agraph-center">
            <circle cx={CX} cy={CY} r={38} />
            <text x={CX} y={CY - 3} textAnchor="middle" className="agraph-center-title">
              {filmTitle.length > 22 ? `${filmTitle.slice(0, 21)}…` : filmTitle}
            </text>
            <text x={CX} y={CY + 13} textAnchor="middle" className="agraph-center-sub">
              YOUR FILM
            </text>
          </g>

          {/* Ranked cultural domains: small marks, editorial labels and clear hierarchy. */}
          {placed.map((p) => {
            const cosine = Math.cos(p.angle);
            const sine = Math.sin(p.angle);
            const anchor = cosine > 0.2 ? "start" : cosine < -0.2 ? "end" : "middle";
            const labelX = p.x + (anchor === "start" ? 13 : anchor === "end" ? -13 : 0);
            const labelY = Math.abs(cosine) <= 0.2 ? p.y + (sine > 0 ? 22 : -14) : p.y + 4;
            const isSelected = selected === p.node.key;
            return (
              <g
                key={p.node.key}
                className={"agraph-node agraph-domain-node" + (isSelected ? " is-selected" : "") + (p.node.role === "primary" ? " is-primary" : p.node.role === "runner-up" ? " is-runner" : "")}
                role="button"
                tabIndex={0}
                onClick={() => setSelected(isSelected ? null : p.node.key)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelected(isSelected ? null : p.node.key);
                  }
                }}
                aria-pressed={isSelected}
                aria-label={p.node.label + ", " + p.node.kindLabel + ", rank " + p.node.rank}
              >
                <circle className="agraph-node-halo" cx={p.x} cy={p.y} r="13" />
                <circle cx={p.x} cy={p.y} r={p.node.role === "primary" ? 7.5 : 5.8} />
                <text x={labelX} y={labelY} textAnchor={anchor} className="agraph-node-label">
                  {p.node.label.length > 21 ? p.node.label.slice(0, 20) + "…" : p.node.label}
                </text>
                <text x={labelX} y={labelY + 13} textAnchor={anchor} className="agraph-node-meta">
                  {String(p.node.rank).padStart(2, "0") + " · " + p.node.memberCount + " MEMBERS"}
                </text>
              </g>
            );
          })}

          {/* The outer orbit names real cohort members and selects their parent world. */}
          {memberNodes.map((member) => {
            const cosine = Math.cos(member.angle);
            const sine = Math.sin(member.angle);
            const anchor = cosine > 0.18 ? "start" : cosine < -0.18 ? "end" : "middle";
            const labelX = member.x + (anchor === "start" ? 9 : anchor === "end" ? -9 : 0);
            const labelY = Math.abs(cosine) <= 0.18 ? member.y + (sine > 0 ? 15 : -9) : member.y + 3;
            const isSelected = selected === member.parentKey;
            return (
              <g
                key={member.key}
                className={"agraph-node agraph-entity-node" + (isSelected ? " is-selected" : "")}
                role="button"
                tabIndex={0}
                onClick={() => setSelected(isSelected ? null : member.parentKey)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelected(isSelected ? null : member.parentKey);
                  }
                }}
                aria-pressed={isSelected}
                aria-label={member.name + ", member of " + (placed.find((p) => p.node.key === member.parentKey)?.node.label ?? "a cultural world")}
              >
                <circle cx={member.x} cy={member.y} r={member.affinity == null ? 4.6 : 4.1 + Math.max(0, Math.min(1, member.affinity)) * 2.2} />
                <text x={labelX} y={labelY} textAnchor={anchor} className="agraph-node-label">
                  {member.name.length > 25 ? member.name.slice(0, 24) + "…" : member.name}
                </text>
                <text x={labelX} y={labelY + 12} textAnchor={anchor} className="agraph-node-meta">
                  {placed.find((p) => p.node.key === member.parentKey)?.node.label ?? "CULTURAL CONNECTION"}
                </text>
              </g>
            );
          })}
        </svg>
        {dataStatus === "fixture" && (
          <span className="agraph-stamp">FIXTURE DEMONSTRATION — NOT LIVE QLOO DATA</span>
        )}
        {dataStatus !== "measured" && dataStatus !== "fixture" && (
          <span className="agraph-stamp is-unknown">DATA STATUS UNKNOWN</span>
        )}
      </div>

      <aside className="agraph-inspector" aria-live="polite">
        {!active && (
          <p className="agraph-inspector-hint">
          Select a world to inspect its cohort and recorded call reference. Node size reflects
          member count; edge weight reflects the run&apos;s mean affinity. Rejected worlds remain
          visible with their reason codes — exclusions are annotations, not deletions.
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
              <div><dt>Grouping</dt><dd>{active.node.kindLabel}</dd></div>
              {active.node.constructionReason && (
                <div><dt>Why grouped</dt><dd>{active.node.constructionReason}</dd></div>
              )}
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
                <div>
                  <dt>Evidence call</dt>
                  <dd className="mono-tiny">
                    {activeTrace ? (
                      <a href={`#${traceAnchorId(active.node.callId)}`}>
                        {active.node.callId} · inspect trace
                      </a>
                    ) : (
                      <span>{active.node.callId} · no matching trace entry</span>
                    )}
                  </dd>
                </div>
              )}
              {!active.node.callId && (
                <div><dt>Evidence call</dt><dd>Not linked in this response</dd></div>
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
              Affinity is cultural similarity — not evidence this audience will watch the film. A fixture is not a live Qloo result.
            </p>
          </>
        )}
      </aside>
    </div>
  );
}
