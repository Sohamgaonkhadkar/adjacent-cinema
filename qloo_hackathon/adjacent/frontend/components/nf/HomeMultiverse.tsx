"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  MULTIVERSE_BANNER,
  previewIndex,
  previewStrategies,
  suggestPreviewStrategy,
  type PreviewStrategy,
  type PreviewStrategyId,
} from "@/lib/nfPreview";
import { photos, type Photo } from "@/lib/photos";
import { PhotoFrame } from "./PhotoFrame";
import { cn } from "@/lib/cn";

/**
 * Home-page Cultural Multiverse, ported from the source ZIP
 * (src/components/Multiverse.tsx) with its three stages intact.
 *
 * This section is a *design preview*: it is deliberately isolated from the
 * Creator run, and it never claims to analyse a film. The evidence-backed
 * arena lives at /creator#arena and is computed from a completed investigation.
 */

const photoFor: Record<PreviewStrategyId, Photo> = {
  anchor: photos.cinemaEmpty,
  bridge: photos.soho,
  frontier: photos.projectorLens,
};

const secondPhoto: Record<PreviewStrategyId, Photo> = {
  anchor: photos.editingTable,
  bridge: photos.urbanPuddle,
  frontier: photos.reelTape,
};

export function HomeMultiverse() {
  const [id, setId] = useState<PreviewStrategyId>("anchor");
  const [openDossier, setOpenDossier] = useState(false);
  const [priorities, setPriorities] = useState({ evidence: 80, distinct: 55, range: 25 });
  const [appliedSuggestion, setAppliedSuggestion] = useState<PreviewStrategyId | null>(null);

  const strategy = previewStrategies.find((item) => item.id === id)!;
  const index = useMemo(() => previewIndex(priorities), [priorities]);
  const suggestion = useMemo(() => suggestPreviewStrategy(priorities), [priorities]);

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
            Anchor, Bridge and Frontier as visual strategies. This section demonstrates the
            interaction design only — the evidence-backed arena runs inside Creator Studio against a
            completed investigation.
          </p>
        </div>

        <div className="mt-8 border border-amber/40 bg-amber/10 px-4 py-3">
          <p className="font-mono text-[0.68rem] uppercase tracking-[0.14em] text-amber">
            {MULTIVERSE_BANNER}
          </p>
        </div>

        <div className="mt-10 grid gap-3 md:grid-cols-3">
          {previewStrategies.map((item) => (
            <StrategyTab
              key={item.id}
              strategy={item}
              active={item.id === id}
              onSelect={() => {
                setId(item.id);
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
            id === "frontier" && "bg-ink-3",
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
              {strategy.risks.map((risk) => (
                <li
                  key={risk}
                  className="text-sm text-paper-2 before:mr-3 before:text-amber before:content-['—']"
                >
                  {risk}
                </li>
              ))}
            </ul>
          </div>

          <div className="border border-line p-5 lg:col-span-5 md:p-6">
            <p className="type-kicker">What-if lab · design preview</p>
            <p className="mt-3 text-sm text-mute">
              Moving a slider computes an illustrative index with the published weights below. It
              does not score a film, does not call a provider and does not write an experiment. The
              real lab reorders existing candidates from a completed run.
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
                  <span className="flex justify-between font-mono text-[0.62rem] uppercase tracking-[0.14em] text-amber">
                    {label}
                    <span>{priorities[key]}</span>
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={priorities[key]}
                    aria-label={`${label} demonstration priority`}
                    onChange={(event) =>
                      setPriorities((previous) => ({ ...previous, [key]: Number(event.target.value) }))
                    }
                    className="mt-2 w-full accent-amber"
                  />
                </label>
              ))}
            </div>
            <ul className="mt-5 space-y-1 border border-line bg-ink p-3">
              {previewStrategies.map((item) => (
                <li key={item.id} className="flex items-baseline justify-between text-xs">
                  <span className={item.id === suggestion.id ? "text-amber" : "text-mute"}>
                    {item.name}
                  </span>
                  <span className="font-mono tabular-nums text-paper-2">{index[item.id]}</span>
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
                onClick={() => setOpenDossier((value) => !value)}
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
            <Link
              href="/creator#arena"
              className="mt-4 inline-flex items-center gap-2 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-amber hover:text-paper"
            >
              Open the evidence-backed arena ↗
            </Link>
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
                Illustrative design copy. The real dossier is assembled from returned evidence and
                your saved plan.
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
  strategy: PreviewStrategy;
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
        active ? "border-amber bg-amber/10" : "border-line hover:border-line-strong",
      )}
    >
      <p className="type-meta">{strategy.kicker}</p>
      <p className="font-display mt-2 text-3xl">{strategy.name}</p>
      <p className="mt-2 text-sm leading-relaxed text-mute">{strategy.lede}</p>
    </button>
  );
}

function AnchorStage({ strategy }: { strategy: PreviewStrategy }) {
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

function BridgeStage({ strategy }: { strategy: PreviewStrategy }) {
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

function FrontierStage({ strategy }: { strategy: PreviewStrategy }) {
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
