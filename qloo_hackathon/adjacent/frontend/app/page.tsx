"use client";

import Link from "next/link";

// ─── Creator-first landing (M13.15) ────────────────────────────────────────
// Cinematic editorial language adapted from the approved prototype
// (correct_frontend_source/Qloo) into the existing Next.js app. No invented
// statistics, no fake confidence: every claim on this page describes what the
// product actually does, and the demo/fixture labelling rule is stated up
// front. Cinema Mode is preserved at /cinema.

const HERO_IMAGE = {
  src: "https://images.pexels.com/photos/7991486/pexels-photo-7991486.jpeg?auto=compress&cs=tinysrgb&fit=crop&w=1800&h=1100",
  photographer: "Tima Miroshnichenko",
  source: "Pexels",
  creditUrl: "https://www.pexels.com/photo/an-empty-cinema-7991486/",
};

const JOURNEY = [
  {
    no: "01",
    title: "Your film",
    body: "A title, logline, genre, the references that shaped it, and what you want the release to do. Nothing else is assumed.",
  },
  {
    no: "02",
    title: "Cultural fingerprint",
    body: "A deterministic agent runs real Qloo operations: your references resolve to entities, a taste profile emerges, adjacent cultural worlds expand and rank — every step recorded with a call id.",
  },
  {
    no: "03",
    title: "Evidence-grounded brief",
    body: "Findings are typed FACT, INTERPRETATION, HYPOTHESIS or UNKNOWN. Facts cite the call that produced them. An optional model-written brief must pass claim-level validation or fall back — labelled — to the deterministic account.",
  },
  {
    no: "04",
    title: "Your experiment",
    body: "A positioning proposal you edit and explicitly confirm before it is saved. What the model proposed and what you changed stay separately on the record.",
  },
  {
    no: "05",
    title: "Observation",
    body: "Record what actually happened — including zero, partial or missing. A missing measurement is never presented as a negative result.",
  },
  {
    no: "06",
    title: "Honest evaluation",
    body: "Supported, contradicted or inconclusive against the criteria you pre-registered. Correlation is never dressed up as causation.",
  },
];

const PRINCIPLES = [
  {
    label: "Evidence or abstention",
    body: "Every factual claim cites the Qloo call that produced it. When evidence is insufficient, the system says so and refuses to force a recommendation — a missing answer is a legitimate result.",
  },
  {
    label: "Affinity is not audience",
    body: "Cultural affinity measures similarity between expressed interests. It is not proof anyone will watch, enjoy or share your film — the product never predicts views, revenue or virality.",
  },
  {
    label: "A loop, not an oracle",
    body: "Hypothesis → experiment → observation → evaluation, with append-only history. You can always trace what was decided, on what evidence, and what the outcome actually showed.",
  },
];

const CLAIM_TYPES = [
  { type: "FACT", note: "Returned by a recorded Qloo call — cites its call id." },
  { type: "INTERPRETATION", note: "Reasoning over facts — labelled, never sold as source data." },
  { type: "HYPOTHESIS", note: "A positioning decision to test, not an established truth." },
  { type: "UNKNOWN", note: "Openly unresolved — never filled with plausible-sounding content." },
];

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-topbar">
        <Link href="/" className="landing-wordmark">
          ADJACENT<span className="landing-wordmark-sub">cultural intelligence</span>
        </Link>
        <nav className="landing-nav" aria-label="Primary">
          <Link href="/creator" className="landing-nav-link is-primary">Creator Studio</Link>
          <Link href="/cinema" className="landing-nav-link">Cinema Mode</Link>
        </nav>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-media" aria-hidden>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={HERO_IMAGE.src} alt="" />
          <a
            className="landing-photo-credit"
            href={HERO_IMAGE.creditUrl}
            target="_blank"
            rel="noreferrer"
          >
            {HERO_IMAGE.photographer} / {HERO_IMAGE.source}
          </a>
        </div>
        <div className="landing-hero-copy">
          <p className="landing-kicker">Qloo-powered cultural intelligence · for independent filmmakers</p>
          <h1 className="landing-title">
            Know which cultural world<br />
            <em>your film speaks to</em> —<br />
            before you position it.
          </h1>
          <p className="landing-lede">
            Adjacent investigates your film&rsquo;s real cultural connections through the Qloo
            API, turns the evidence into a positioning hypothesis you can test, and records
            what actually happened. No invented audiences. No guaranteed virality. Evidence,
            or an honest &ldquo;not enough evidence yet.&rdquo;
          </p>
          <div className="landing-cta-row">
            <Link href="/creator" className="landing-cta">Start a film investigation</Link>
            <Link href="/cinema" className="landing-cta is-ghost">Enter Cinema Mode</Link>
          </div>
          <p className="landing-hero-note">
            Runs without live Qloo credentials use clearly labelled fixture demonstrations —
            never presented as live results.
          </p>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-shell">
          <p className="landing-kicker">The journey</p>
          <h2 className="landing-h2">From film brief to <em>measured learning.</em></h2>
          <div className="landing-journey">
            {JOURNEY.map((step) => (
              <article key={step.no} className="landing-step">
                <span className="landing-step-no">{step.no}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section is-dark">
        <div className="landing-shell">
          <p className="landing-kicker">Why this is not another analytics dashboard</p>
          <h2 className="landing-h2">Three rules the product <em>cannot break.</em></h2>
          <div className="landing-principles">
            {PRINCIPLES.map((p) => (
              <article key={p.label} className="landing-principle">
                <h3>{p.label}</h3>
                <p>{p.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-shell">
          <p className="landing-kicker">Reading the evidence</p>
          <h2 className="landing-h2">Every claim tells you <em>what it is.</em></h2>
          <div className="landing-claims">
            {CLAIM_TYPES.map((c) => (
              <div key={c.type} className="landing-claim">
                <span className="micro-label">{c.type}</span>
                <p>{c.note}</p>
              </div>
            ))}
          </div>
          <div className="landing-closing">
            <p>
              The agent decides with a fixed, auditable plan — resolve, analyse, expand, rank —
              and stops when the evidence runs out. The model may propose. The evidence
              constrains it. You decide. The experiment records what happened.
            </p>
            <Link href="/creator" className="landing-cta">Investigate your film</Link>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <span>Adjacent — cultural-intelligence decision support for independent film.</span>
        <span className="landing-footer-links">
          <Link href="/creator">Creator Studio</Link>
          <Link href="/cinema">Cinema Mode</Link>
        </span>
      </footer>
    </div>
  );
}
