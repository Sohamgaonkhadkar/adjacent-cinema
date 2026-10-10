"use client";

interface TwoSidedSignals {
  programme_adjacency: number | null;
  adjacency_band: string | null;
  adjacency_call_id: string | null;
  cohort_breadth: number | null;
  breadth_band: string | null;
  breadth_call_id: string | null;
  methodology_note: string;
}

interface RejectedCandidate {
  cohort_id: string;
  domain: string;
  reason: string;
  detail: string;
}

interface BetData {
  primary: {
    domain: string;
    cohort_name: string;
    member_count: number;
    mean_affinity: number;
    call_id: string;
  };
  runner_up: {
    domain: string;
    cohort_name: string;
    mean_affinity: number;
    call_id: string;
  } | null;
  two_sided_signals: TwoSidedSignals;
  why: string;
  cultural_bridge: string;
  geographic_signal: string;
  programming_direction: string;
  falsification_condition: string;
  rejected_candidates: RejectedCandidate[];
  geography_call_id: string | null;
  data_status: string;
}

interface Props {
  bet: BetData;
}

function BandBadge({ band }: { band: string | null }) {
  if (!band) return null;
  const colors = {
    High: "bg-emerald-900/50 text-emerald-300",
    Medium: "bg-amber-900/50 text-amber-300",
    Low: "bg-red-900/50 text-red-300",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${colors[band as keyof typeof colors] || "bg-gray-700 text-gray-300"}`}>
      {band}
    </span>
  );
}

export default function ProgrammeBet({ bet }: Props) {
  const primary = bet.primary;
  const signals = bet.two_sided_signals;
  const hasSignals = Boolean(
    signals && (signals.programme_adjacency != null || signals.cohort_breadth != null)
  );

  return (
    <div className="rounded-xl border border-emerald-700/50 bg-emerald-900/10 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-emerald-400 uppercase tracking-wide">
          🎯 Programme Bet
        </h3>
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${
            bet.data_status === "measured"
              ? "bg-emerald-900/50 text-emerald-300"
              : "bg-amber-900/50 text-amber-300"
          }`}
        >
          {bet.data_status === "measured" ? "Measured Qloo" : bet.data_status === "fixture" ? "Fixture demo (not live)" : bet.data_status}
        </span>
      </div>

      {/* Primary bet */}
      <div className="mb-4">
        <div className="text-lg font-semibold text-emerald-200">
          {primary.cohort_name}
        </div>
        <div className="text-sm text-gray-400 mt-1">
          {primary.domain} · {primary.member_count} entities · mean
          affinity {primary.mean_affinity.toFixed(2)}
        </div>
      </div>

      {/* Two-sided signals (M11.3: scientifically accurate labels) */}
      {hasSignals && (
        <div className="mb-4 p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
            Evidence Dimensions
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-gray-400">Programme Adjacency</div>
              <div className="text-[10px] text-gray-500 mb-1">Cultural proximity to your programme</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm font-medium text-gray-200">
                  {signals.programme_adjacency?.toFixed(2) ?? "—"}
                </span>
                <BandBadge band={signals.adjacency_band} />
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Cohort Breadth</div>
              <div className="text-[10px] text-gray-500 mb-1">Fraction above quality threshold</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm font-medium text-gray-200">
                  {signals.cohort_breadth?.toFixed(2) ?? "—"}
                </span>
                <BandBadge band={signals.breadth_band} />
              </div>
            </div>
          </div>
          {signals.methodology_note && (
            <div className="mt-2 text-[10px] text-gray-500 italic">
              {signals.methodology_note}
            </div>
          )}
        </div>
      )}

      {/* Why */}
      <div className="mb-4">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
          Why
        </div>
        <p className="text-sm text-gray-300 leading-relaxed">{bet.why}</p>
      </div>

      {/* Cultural bridge */}
      <div className="mb-4">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
          Cultural Bridge
        </div>
        <p className="text-sm text-gray-300 leading-relaxed">
          {bet.cultural_bridge}
        </p>
      </div>

      {/* Geographic signal */}
      <div className="mb-4">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
          Geographic Signal
        </div>
        <p className="text-sm text-gray-300 leading-relaxed">
          {bet.geographic_signal}
        </p>
      </div>

      {/* Programming direction */}
      <div className="mb-4">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
          Programming Direction
        </div>
        <p className="text-sm text-gray-300 leading-relaxed">
          {bet.programming_direction}
        </p>
      </div>

      {/* Runner-up */}
      {bet.runner_up && (
        <div className="mb-4 pt-3 border-t border-gray-700/50">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            Runner-Up
          </div>
          <p className="text-sm text-gray-300">
            {bet.runner_up.cohort_name} ({bet.runner_up.domain}) —{" "}
            affinity {bet.runner_up.mean_affinity.toFixed(2)}
          </p>
        </div>
      )}

      {/* Rejected candidates */}
      {bet.rejected_candidates?.length > 0 && (
        <div className="mb-4 pt-3 border-t border-gray-700/50">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            Rejected Candidates
          </div>
          <div className="space-y-1">
            {bet.rejected_candidates.map((r, i) => (
              <div key={i} className="text-xs text-gray-400">
                {r.domain} — {r.reason}
                {r.detail && `: ${r.detail}`}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Falsification */}
      <div className="mt-4 pt-3 border-t border-red-800/50">
        <div className="text-xs text-red-400 uppercase tracking-wide mb-1">
          ⚠️ Falsification Condition
        </div>
        <p className="text-sm text-red-300/80 leading-relaxed">
          {bet.falsification_condition}
        </p>
      </div>
    </div>
  );
}