/* ─── Adjacent Shell — adapted from original SUTRA Shell ──────────────────── */

import { useEffect, useState } from "react";
import {
  Activity,
  ClipboardCheck,
  Crosshair,
  Footprints,
  MapPinned,
  ScrollText,
  type LucideIcon,
} from "lucide-react";
import { cn, Dot, type Tone } from "./u";

export type ViewId = "overview" | "resolver" | "places" | "evidence" | "queue" | "method";

const NAV: { id: ViewId; no: string; label: string; icon: LucideIcon; sub: string }[] = [
  { id: "overview", no: "01", label: "Overview", icon: Activity, sub: "pipeline & bet" },
  { id: "resolver", no: "02", label: "Resolver", icon: Crosshair, sub: "films & cohorts" },
  { id: "places", no: "03", label: "Places", icon: MapPinned, sub: "cultural geography" },
  { id: "evidence", no: "04", label: "Evidence", icon: Footprints, sub: "Qloo trace" },
  { id: "queue", no: "05", label: "Predictions", icon: ClipboardCheck, sub: "lifecycle" },
  { id: "method", no: "06", label: "Method", icon: ScrollText, sub: "how it decides" },
];

function LiveClock() {
  const [t, setT] = useState("");
  useEffect(() => {
    const f = () => {
      const d = new Date();
      const p = (n: number) => String(n).padStart(2, "0");
      setT(`${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`);
    };
    f();
    const id = setInterval(f, 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="mono text-[11px] text-ink tnum">{t}</span>;
}

export default function Shell({
  view,
  setView,
  queueCount,
  dataMode,
  children,
}: {
  view: ViewId;
  setView: (v: ViewId) => void;
  queueCount: number;
  dataMode: "LIVE" | "DEMO" | "OFFLINE" | "MODE_UNVERIFIED";
  children: React.ReactNode;
}) {
  const current = NAV.find((n) => n.id === view)!;
  const modeTone: Tone = dataMode === "LIVE" ? "ok" : dataMode === "DEMO" ? "warn" : "crit";

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── rail ── */}
      <aside className="w-[228px] shrink-0 border-r hairline bg-panel flex flex-col">
        <div className="px-4 pt-4 pb-3 border-b hairline">
          <div className="flex items-center gap-2">
            <span className="grid place-items-center size-[26px] border border-line2 bg-raised">
              <Crosshair size={15} strokeWidth={1.7} className="text-accent-deep" />
            </span>
            <div>
              <div className="text-[15px] font-bold tracking-[0.22em] leading-none">ADJACENT</div>
              <div className="mono text-[8px] tracking-[0.18em] text-mute mt-1 uppercase">
                cultural intelligence
              </div>
            </div>
          </div>
          <div className="mt-3 border hairline bg-raised px-2 py-1.5 mono text-[8.5px] text-mute leading-relaxed uppercase tracking-[0.08em]">
            Prince Charles Cinema · London<br />
            independent repertory cinema
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map((n) => {
            const active = n.id === view;
            const badge = n.id === "queue" ? queueCount : undefined;
            const Icon = n.icon;
            return (
              <button
                key={n.id}
                onClick={() => setView(n.id)}
                className={cn(
                  "group w-full flex items-center gap-2.5 px-4 py-[7px] text-left border-l-2 -ml-px transition-colors",
                  active
                    ? "border-accent bg-accent-faint/70"
                    : "border-transparent hover:bg-raised"
                )}
              >
                <span className={cn("mono text-[9px]", active ? "text-accent-deep" : "text-faint")}>
                  {n.no}
                </span>
                <Icon
                  size={14}
                  strokeWidth={1.7}
                  className={cn(active ? "text-accent-deep" : "text-mute group-hover:text-ink2")}
                />
                <span className="flex-1 min-w-0">
                  <span
                    className={cn(
                      "block text-[12px] leading-tight",
                      active ? "font-semibold text-ink" : "text-ink2"
                    )}
                  >
                    {n.label}
                  </span>
                  <span className="block mono text-[8px] uppercase tracking-[0.1em] text-faint leading-tight">
                    {n.sub}
                  </span>
                </span>
                {badge !== undefined && (
                  <span
                    className={cn(
                      "mono text-[9px] px-1 border",
                      active
                        ? "border-accent/50 text-accent-deep bg-raised"
                        : "hairline text-mute bg-raised"
                    )}
                  >
                    {badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="border-t hairline px-4 py-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="mono text-[9px] uppercase tracking-[0.1em] text-mute">Data mode</span>
            <span className="flex items-center gap-1.5 mono text-[9px]">
              <Dot tone={modeTone} blink={dataMode !== "LIVE"} /> {dataMode}
            </span>
          </div>
          <div className="text-[10.5px] leading-snug">
            <div className="font-semibold">Prince Charles Cinema</div>
            <div className="mono text-[8.5px] uppercase tracking-[0.1em] text-mute">
              London · independent repertory
            </div>
          </div>
          <div className="mono text-[8px] text-faint uppercase tracking-[0.1em]">
            adjacent v1 · Qloo cultural intelligence
          </div>
        </div>
      </aside>

      {/* ── main ── */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-11 shrink-0 border-b hairline bg-panel flex items-center justify-between gap-4 px-5">
          <div className="flex items-baseline gap-2.5 min-w-0">
            <span className="mono text-[9.5px] tracking-[0.16em] text-faint uppercase">ADJACENT /</span>
            <span className="mono text-[10.5px] tracking-[0.16em] text-ink uppercase font-semibold">
              {current.label}
            </span>
            <span className="mono text-[9px] tracking-[0.1em] text-mute uppercase hidden md:inline">
              — {current.sub}
            </span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="mono text-[9px] uppercase tracking-[0.1em] text-mute hidden lg:inline">
              Qloo cultural intelligence · London
            </span>
            <span className="border hairline bg-raised px-2 py-1 flex items-center gap-2">
              <span className="mono text-[8.5px] uppercase tracking-[0.12em] text-faint">BST</span>
              <LiveClock />
            </span>
            <Tag2 tone={modeTone}>{dataMode === "LIVE" ? "live qloo" : dataMode === "DEMO" ? "demo data" : dataMode === "MODE_UNVERIFIED" ? "mode unverified" : "offline"}</Tag2>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto bg-paper">
          <div className="p-5 min-h-full">{children}</div>
        </main>
      </div>
    </div>
  );
}

/* inline Tag2 to avoid circular import */
function Tag2({ tone = "ink", children }: { tone?: Tone; children: React.ReactNode }) {
  const chip: Record<Tone, string> = {
    ink: "bg-sunk text-ink2 border-line2",
    accent: "bg-accent-faint text-accent-deep border-accent/40",
    ok: "bg-ok-soft text-ok border-ok/30",
    warn: "bg-warn-soft text-warn border-warn/30",
    crit: "bg-crit-soft text-crit border-crit/30",
    cool: "bg-cool-soft text-cool border-cool/30",
    plum: "bg-plum-soft text-plum border-plum/30",
    mute: "bg-sunk text-mute border-line",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 border px-1.5 py-px mono text-[9.5px] uppercase tracking-[0.08em] leading-[1.5] ${chip[tone]}`}
    >
      {children}
    </span>
  );
}