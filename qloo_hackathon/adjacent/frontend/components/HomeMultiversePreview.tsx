"use client";

import { useMemo, useState } from "react";
import {
  MULTIVERSE_BANNER,
  previewIndex,
  strategies,
  suggestStrategy,
  type Strategy,
} from "@/lib/nightfallMultiverseData";
import { photos, type Photo } from "@/lib/nightfallPhotos";
import PhotoFrame from "./NightfallPhotoFrame";
import { cn } from "@/components/u";
import type { StrategyId } from "@/lib/nightfallMultiverseData";

const photoFor: Record<StrategyId, Photo> = {
  anchor: photos.cinemaEmpty,
  bridge: photos.soho,
  frontier: photos.projectorLens,
};

const secondPhoto: Record<StrategyId, Photo> = {
  anchor: photos.editingTable,
  bridge: photos.urbanPuddle,
  frontier: photos.reelTape,
};

export default function HomeMultiversePreview() {
  const [id, setId] = useState<StrategyId>("anchor");
  const [openDossier, setOpenDossier] = useState(false);
  const [priorities, setPriorities] = useState({ evidence: 80, distinct: 55, range: 25 });
  const [appliedSuggestion, setAppliedSuggestion] = useState<StrategyId | null>(null);

  const strategy = strategies.find((s) => s.id === id)!;
  const index = useMemo(() => previewIndex(priorities), [priorities]);
  const suggestion = useMemo(() => suggestStrategy(priorities), [priorities]);

  return (
    <section className="relative bg-ink" id="multiverse">
      <div className="mx-auto max-w-[1440px] px-4 py-20 md:px-8 md:py-28">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <p className="type-kicker">Cultural Multiverse</p>
            <h2 className="font-display mt-4 text-4xl leading-[0.95] md:text-6xl">
              Three ways to stand
              <span className="italic text-amber"> a film</span> in culture.
            </h2>
          </div>
          <p className="max-w-sm text-sm leading-relaxed text-mute">
            A visual, illustrative preview of Anchor, Bridge and Frontier. The evidence-backed strategy arena is available in Creator Studio after a completed run.
          </p>
        </div>

        <div className="mt-8 border border-amber/40 bg-amber/10 px-4 py-3">
          <p className="font-mono text-[0.68rem] tracking-[0.14em] uppercase text-amber">
            {MULTIVERSE_BANNER}
          </p>
        </div>

        <div className="mt-10 grid gap-3 md:grid-cols-3">
          {strategies.map((s) => (
            <StrategyTab
              key={s.id}
              strategy={s}
              active={s.id === id}
              onSelect={() => {
                setId(s.id);
                setOpenDossier(false);
              }}
            />
          ))}
        </div>

        <div
          className={cn(
            "mt-6 overflow-hidden border border-line",
            id === "anchor" && "bg-ink-2",
            id === "bridge" && "bg-ink",
            id === "frontier" && "bg-ink-3"
          )}
        >
          {id === "anchor" && <AnchorStage strategy={strategy} />}
          {id === "bridge" && <BridgeStage strategy={strategy} />}
          {id === "frontier" && <FrontierStage strategy={strategy} />}
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <p className="type-kicker">Illustrative evidence map</p>
            <ul className="mt-5 divide-y divide-line border-y border-line">
              {strategy.evidence.map((row) => (
                <li key={row.label} className="grid gap-2 py-4 md:grid-cols-[220px_1fr]">
                  <div>
                    <p className="text-sm text-paper">{row.label}</p>
                    <p className="caption mt-1">{row.kind}</p>
                  </div>
                  <p className="text-sm leading-relaxed text-mute">{row.note}</p>
                </li>
              ))}
            </ul>
            <ul className="mt-6 space-y-2">
              {strategy.risks.map((r) => (
                <li key={r} className="text-sm text-paper-2 before:mr-3 before:text-amber before:content-['—']">
                  {r}
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-5 border border-line p-5 md:p-6">
            <p className="type-kicker">What-if lab</p>
            <p className="mt-3 text-sm text-mute">
              Moving a slider computes an illustrative index using the published weights below. It
              does not reorder the stage — the suggestion applies only when you choose “Apply to
              preview”. It never scores a film and never writes an experiment.
            </p>
            <div className="mt-6 space-y-5">
              {(
                [
                  ["evidence", "Evidence strictness"],
                  ["distinct", "Distinctiveness"],
                  ["range", "Exploratory range"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="block">
                  <span className="flex justify-between font-mono text-[0.62rem] tracking-[0.14em] uppercase text-amber">
                    {label}
                    <span>{priorities[key]}</span>
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={priorities[key]}
                    onChange={(e) =>
                      setPriorities((p) => ({ ...p, [key]: Number(e.target.value) }))
                    }
                    className="mt-2 w-full accent-amber"
                  />
                </label>
              ))}
            </div>
            <ul className="mt-5 space-y-1 border border-line bg-ink p-3">
              {strategies.map((s) => (
                <li key={s.id} className="flex items-baseline justify-between text-xs">
                  <span className={s.id === suggestion.id ? "text-amber" : "text-mute"}>
                    {s.name}
                  </span>
                  <span className="font-mono tabular-nums text-paper-2">{index[s.id]}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-sm leading-relaxed text-paper-2">
              Suggested <span className="text-amber">{suggestion.id}</span> · selected{" "}
              <span className="text-amber">{id}</span>
              {suggestion.id === id ? " (matching)" : " (distinct)"}. {suggestion.reason}
            </p>
            <p className="mt-2 font-mono text-[0.58rem] leading-relaxed text-dim">
              {suggestion.weights}
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                className="btn-amber"
                disabled={suggestion.id === id}
                onClick={() => {
                  setId(suggestion.id);
                  setAppliedSuggestion(suggestion.id);
                }}
              >
                Apply to preview
              </button>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setOpenDossier((v) => !v)}
                aria-expanded={openDossier}
              >
                {openDossier ? "Close dossier" : "Open decision dossier"}
              </button>
            </div>
            <p className="mt-4 caption">
              Demonstration rule with published weights — not a production ranking model.
              {appliedSuggestion !== null &&
                appliedSuggestion !== suggestion.id &&
                " Suggestion changed since it was applied."}
            </p>
          </div>
        </div>

        {openDossier && (
          <div className="drawer-enter mt-8 grid gap-0 border border-line md:grid-cols-2">
            <div className="p-6 md:p-10">
              <p className="type-kicker">{strategy.dossier.title}</p>
              <h3 className="font-display mt-4 text-3xl md:text-4xl">{strategy.dossier.stance}</h3>
              <p className="mt-6 text-sm leading-relaxed text-mute">{strategy.dossier.imageCrop}</p>
              <p className="mt-2 text-sm leading-relaxed text-mute">{strategy.dossier.typeTone}</p>
              <p className="mt-8 caption">
                This dossier belongs to the concept preview. Creator Studio uses a separate run-linked strategy payload and validated evidence.
              </p>
            </div>
            <PhotoFrame photo={photoFor[id]} className="min-h-[280px]" />
          </div>
        )}
      </div>
    </section>
  );
}

function StrategyTab({
  strategy,
  active,
  onSelect,
}: {
  strategy: Strategy;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={active}
      className={cn(
        "border px-4 py-5 text-left transition-colors",
        active ? "border-amber bg-amber/10" : "border-line hover:border-line-strong"
      )}
    >
      <p className="type-meta">{strategy.kicker}</p>
      <p className="font-display mt-2 text-3xl">{strategy.name}</p>
      <p className="mt-2 text-sm leading-relaxed text-mute">{strategy.lede}</p>
    </button>
  );
}

function AnchorStage({ strategy }: { strategy: Strategy }) {
  return (
    <div className="grid md:grid-cols-12">
      <div className="flex flex-col justify-end p-6 md:col-span-5 md:p-12">
        <p className="type-kicker">Anchor</p>
        <h3 className="font-display mt-4 text-4xl leading-[0.95] md:text-5xl">{strategy.headline}</h3>
        <p className="mt-6 max-w-md text-sm leading-relaxed text-paper-2">{strategy.body}</p>
        <p className="caption mt-8">{strategy.visual}</p>
      </div>
      <div className="md:col-span-7">
        <PhotoFrame photo={photos.cinemaEmpty} className="h-full min-h-[320px]" credit={false} />
      </div>
    </div>
  );
}

function BridgeStage({ strategy }: { strategy: Strategy }) {
  return (
    <div className="grid md:grid-cols-2">
      <div className="relative min-h-[280px]">
        <PhotoFrame photo={photos.editingTable} className="h-full" credit={false} />
        <span className="caption absolute bottom-3 left-3 z-10 bg-ink/70 px-2 py-1">
          {strategy.worlds.a}
        </span>
      </div>
      <div className="relative min-h-[280px]">
        <PhotoFrame photo={secondPhoto.bridge} className="h-full" credit={false} />
        <span className="caption absolute bottom-3 left-3 z-10 bg-ink/70 px-2 py-1">
          {strategy.worlds.b}
        </span>
      </div>
      <div className="border-t border-line p-6 md:col-span-2 md:p-10">
        <div className="grid gap-8 md:grid-cols-2">
          <h3 className="font-display text-4xl leading-[0.95]">{strategy.headline}</h3>
          <p className="text-sm leading-relaxed text-paper-2">{strategy.body}</p>
        </div>
      </div>
    </div>
  );
}

function FrontierStage({ strategy }: { strategy: Strategy }) {
  return (
    <div className="relative min-h-[420px] md:min-h-[520px]">
      <PhotoFrame
        photo={photos.projectorLens}
        className="absolute inset-0"
        imgClassName="object-[20%_center]"
        credit={false}
      />
      <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/70 to-transparent" />
      <div className="relative z-10 flex min-h-[420px] max-w-xl flex-col justify-end p-6 md:min-h-[520px] md:p-12">
        <p className="type-kicker">Frontier</p>
        <h3 className="font-display mt-4 text-4xl leading-[0.95] md:text-6xl">{strategy.headline}</h3>
        <p className="mt-6 text-sm leading-relaxed text-paper-2">{strategy.body}</p>
      </div>
    </div>
  );
}
