import Link from "next/link";
import { ArrowDown, ArrowRight } from "lucide-react";
import { photos, filmStrip } from "@/lib/photos";
import { PhotoFrame } from "@/components/nf/PhotoFrame";
import { HomeMultiverse } from "@/components/nf/HomeMultiverse";
import { MiniFingerprint } from "@/components/nf/CulturalFingerprint";
import { FrameCounter } from "@/components/nf/FrameCounter";
import { ClaimChip } from "@/components/nf/Chips";

/**
 * Home page ported from the source ZIP (src/pages/Home.tsx).
 * Composition, imagery, type hierarchy and section order follow the source.
 * Copy that described a not-yet-built arena now points at the real,
 * evidence-backed arena in Creator Studio.
 */
export default function HomePage() {
  return (
    <div>
      <Hero />
      <Journey />
      <Rules />
      <Taxonomy />
      <FingerprintTeaser />
      <HomeMultiverse />
      <Portals />
    </div>
  );
}

function Hero() {
  return (
    <section className="relative min-h-[100svh] overflow-hidden bg-ink">
      <div className="grain vignette absolute inset-0">
        <PhotoFrame
          photo={photos.cinemaEmpty}
          className="enter-aperture h-full w-full"
          credit={false}
          gate
          priority
        />
        <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/70 to-ink/20" />
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-transparent to-ink/40" />
        <div className="beam" aria-hidden="true" />
      </div>

      <div className="relative z-10 mx-auto flex min-h-[100svh] max-w-[1440px] flex-col px-4 md:px-8">
        <div className="flex items-center justify-between pt-6">
          <p className="type-meta text-paper/70">Vol. 01 · Issue 04 · The Culture Room</p>
          <div className="flex items-center gap-4">
            <span className="caption hidden sm:inline">Frame</span>
            <FrameCounter />
          </div>
        </div>

        <div className="flex flex-1 flex-col justify-end pb-8 pt-24 md:pb-12">
          <p className="type-kicker enter delay-1">Cultural intelligence for independent cinema</p>
          <h1 className="enter delay-2 mt-5 max-w-[18ch] font-display text-[2.8rem] leading-[0.92] text-paper sm:text-6xl md:text-7xl lg:text-[5.6rem]">
            Every film belongs to more than one world.
          </h1>
          <p className="enter delay-3 mt-6 max-w-lg text-base leading-relaxed text-paper-2 md:text-lg">
            Investigate a film’s cultural relationships, examine the evidence, and develop a
            positioning hypothesis worth testing.
          </p>

          <div className="enter delay-4 mt-8 flex flex-wrap items-center gap-3">
            <Link className="btn-primary" href="/creator">
              Enter Creator Studio
              <ArrowRight size={16} />
            </Link>
            <Link className="btn-ghost" href="/cinema">
              Cinema Mode
            </Link>
            <Link className="btn-ghost" href="/creator?demo=fixture">
              Labelled fixture
            </Link>
          </div>
        </div>

        <div className="enter delay-5 border-t border-line-strong py-4">
          <div className="flex items-end justify-between gap-4">
            <div className="hidden min-w-0 flex-1 gap-2 md:flex">
              {filmStrip.map((photo, index) => (
                <div key={photo.src} className="relative h-14 flex-1 overflow-hidden bg-ink-3">
                  <PhotoFrame photo={photo} className="h-full" credit={false} />
                  <span className="caption absolute bottom-1 left-1 z-10 bg-ink/60 px-1">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
              ))}
            </div>
            <a
              href={photos.cinemaEmpty.source}
              className="caption shrink-0 hover:text-amber"
              target="_blank"
              rel="noreferrer"
            >
              Photo · {photos.cinemaEmpty.credit} / Pexels
            </a>
            <a href="#journey" className="caption hidden items-center gap-2 sm:inline-flex">
              Scroll
              <ArrowDown size={12} />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function Journey() {
  const steps = [
    {
      n: "01",
      t: "Your film",
      d: "A title, logline, genre, the references that shaped it, and what you want the release to do. Nothing else is assumed.",
    },
    {
      n: "02",
      t: "Cultural fingerprint",
      d: "Resolved references, a taste profile, adjacent worlds ranked — every step recorded with a provider call id.",
    },
    {
      n: "03",
      t: "Evidence-grounded brief",
      d: "Findings are typed FACT, INTERPRETATION, HYPOTHESIS or UNKNOWN. Facts cite the call that produced them.",
    },
    {
      n: "04",
      t: "Your experiment",
      d: "A positioning proposal you edit and confirm. What was proposed and what you changed stay separately on the record.",
    },
    {
      n: "05",
      t: "Observation",
      d: "Record what actually happened — including zero, partial or missing. A missing measurement is never a negative result.",
    },
    {
      n: "06",
      t: "Honest evaluation",
      d: "Supported, contradicted or inconclusive against the criteria you pre-registered. Correlation is never causation.",
    },
  ];

  return (
    <section id="journey" className="border-t border-line bg-ink">
      <div className="mx-auto grid max-w-[1440px] gap-12 px-4 py-20 md:grid-cols-12 md:px-8 md:py-28">
        <div className="md:col-span-5">
          <p className="type-kicker">The journey</p>
          <h2 className="font-display mt-4 text-4xl leading-[0.95] md:text-6xl">
            From film brief to <span className="italic text-amber">measured learning.</span>
          </h2>
          <div className="mt-10">
            <PhotoFrame photo={photos.editingTable} gate className="aspect-[4/5]" />
          </div>
        </div>
        <ol className="md:col-span-7 md:pt-16">
          {steps.map((step) => (
            <li
              key={step.n}
              className="grid grid-cols-[4.5rem_1fr] gap-4 border-t border-line py-6 first:border-t-0 md:grid-cols-[6rem_1fr] md:py-7"
            >
              <span className="font-mono text-sm tracking-[0.14em] text-amber">{step.n}</span>
              <div>
                <h3 className="font-display text-2xl md:text-3xl">{step.t}</h3>
                <p className="mt-2 max-w-xl text-sm leading-relaxed text-mute">{step.d}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Rules() {
  const rules = [
    {
      n: "I",
      t: "Evidence or abstention",
      d: "Every factual claim cites the Qloo call that produced it. When evidence is insufficient, the system says so and refuses to force a recommendation.",
    },
    {
      n: "II",
      t: "Affinity is not audience",
      d: "Cultural affinity measures similarity between expressed interests. It is not proof anyone will watch, enjoy or share your film.",
    },
    {
      n: "III",
      t: "A loop, not an oracle",
      d: "Hypothesis → experiment → observation → evaluation, with append-only history. You can always trace what was decided, on what evidence, and what the outcome showed.",
    },
  ];

  return (
    <section className="relative overflow-hidden border-t border-line">
      <div className="absolute inset-0">
        <PhotoFrame photo={photos.dramaticTheater} className="h-full" credit={false} />
        <div className="absolute inset-0 bg-ink/78" />
      </div>
      <div className="relative mx-auto max-w-[1440px] px-4 py-20 md:px-8 md:py-28">
        <p className="type-kicker">Why this is not another analytics dashboard</p>
        <h2 className="font-display mt-4 max-w-3xl text-4xl leading-[0.95] md:text-6xl">
          Three rules the product <span className="italic">cannot break.</span>
        </h2>
        <div className="mt-14 grid gap-10 md:grid-cols-3">
          {rules.map((rule) => (
            <article key={rule.n} className="border-t border-amber/40 pt-6">
              <p className="font-mono text-xs tracking-[0.2em] text-amber">{rule.n}</p>
              <h3 className="font-display mt-4 text-3xl">{rule.t}</h3>
              <p className="mt-4 text-sm leading-relaxed text-paper-2">{rule.d}</p>
            </article>
          ))}
        </div>
        <p className="caption mt-10">
          Photo · {photos.dramaticTheater.credit} / Pexels · atmospheric reference, not a film still
        </p>
      </div>
    </section>
  );
}

function Taxonomy() {
  const items = [
    { kind: "FACT" as const, d: "Returned by a recorded Qloo call — cites its call id." },
    { kind: "INTERPRETATION" as const, d: "Reasoning over facts — labelled, never sold as source data." },
    { kind: "HYPOTHESIS" as const, d: "A positioning decision to test, not an established truth." },
    { kind: "UNKNOWN" as const, d: "Openly unresolved — never filled with plausible-sounding content." },
  ];

  return (
    <section className="border-t border-line bg-ink-2">
      <div className="mx-auto grid max-w-[1440px] items-start gap-12 px-4 py-20 md:grid-cols-12 md:px-8 md:py-28">
        <div className="md:col-span-4">
          <p className="type-kicker">Reading the evidence</p>
          <h2 className="font-display mt-4 text-4xl leading-[0.95] md:text-5xl">
            Every claim tells you <span className="italic text-amber">what it is.</span>
          </h2>
          <p className="mt-6 text-sm leading-relaxed text-mute">
            The agent decides with a fixed, auditable plan — resolve, analyse, expand, rank — and
            stops when the evidence runs out. The model may propose. The evidence constrains it. You
            decide.
          </p>
        </div>
        <div className="grid gap-px bg-line md:col-span-8 md:grid-cols-2">
          {items.map((item) => (
            <article key={item.kind} className="bg-ink-2 p-6 md:p-8">
              <ClaimChip kind={item.kind} />
              <p className="mt-5 text-sm leading-relaxed text-paper-2">{item.d}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function FingerprintTeaser() {
  return (
    <section className="border-t border-line bg-ink">
      <div className="mx-auto grid max-w-[1440px] gap-10 px-4 py-20 md:grid-cols-12 md:px-8 md:py-28">
        <div className="md:col-span-5">
          <p className="type-kicker">Product signature</p>
          <h2 className="font-display mt-4 text-4xl leading-[0.95] md:text-6xl">
            The Cultural Fingerprint is an atlas, not a glow.
          </h2>
          <p className="mt-6 text-sm leading-relaxed text-mute">
            At the centre: the film, as type. Around it: the cohorts the analysis actually returned.
            Select a node to inspect claim type, source, and limits. Empty is empty. Fixture is
            labelled fixture.
          </p>
          <Link className="btn-primary mt-8" href="/creator?demo=fixture">
            Inspect a labelled fixture
            <ArrowRight size={16} />
          </Link>
        </div>
        <div className="border border-line bg-ink-2 md:col-span-7">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <span className="caption">Illustrative layout · not analysis output</span>
            <span className="chip chip-fixture">Not live Qloo</span>
          </div>
          <div className="aspect-[16/10] p-4">
            <MiniFingerprint
              filmTitle="Your film"
              labels={["Inheritance", "Coastal", "Analog", "Room tone", "Seaside"]}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function Portals() {
  return (
    <section className="border-t border-line">
      <div className="mx-auto max-w-[1440px] px-4 py-20 md:px-8 md:py-28">
        <p className="type-kicker">Enter a room</p>
        <h2 className="font-display mt-4 text-4xl md:text-5xl">Two desks. One standard of evidence.</h2>
        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          <Link href="/creator" className="group text-left">
            <PhotoFrame photo={photos.screenplay} className="aspect-[16/10]" />
            <p className="type-kicker mt-5">01 · Creator Studio</p>
            <h3 className="font-display mt-2 text-3xl group-hover:text-amber">
              A filmmaker’s investigation
            </h3>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-mute">
              Brief, fingerprint, Cultural Multiverse, Test Card, archive. For one film and the
              worlds around it.
            </p>
          </Link>
          <Link href="/cinema" className="group text-left">
            <PhotoFrame photo={photos.cinemaCurtain} className="aspect-[16/10]" />
            <p className="type-kicker mt-5">02 · Cinema Mode</p>
            <h3 className="font-display mt-2 text-3xl group-hover:text-amber">
              A programmer’s atlas
            </h3>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-mute">
              Venue, city, programme. Curatorial notes, not a streaming wall. Geography only when
              the data exists.
            </p>
          </Link>
        </div>
        <div className="mt-10 grid gap-6 border-t border-line pt-10 md:grid-cols-2">
          <div>
            <p className="type-kicker">03 · FilmSponsor</p>
            <h3 className="font-display mt-2 text-2xl">A campaign dossier</h3>
            <p className="mt-3 text-sm leading-relaxed text-mute">
              Live brand discovery when configured. No substitute brands. Approval after source
              review. Outreach is observed, not predicted.
            </p>
            <Link className="btn-ghost mt-5" href="/creator/sponsor">
              Open FilmSponsor
              <ArrowRight size={14} />
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <PhotoFrame photo={photos.redPortrait} className="aspect-[3/4]" />
            <PhotoFrame photo={photos.columns} className="aspect-[3/4]" />
          </div>
        </div>
      </div>
    </section>
  );
}
