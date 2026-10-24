"use client";

import { useState } from "react";

const LENSES = [
  {
    id: "anchor",
    number: "01",
    name: "Anchor",
    phrase: "Stay with the world the evidence can hold.",
    description: "A restrained direction built from a completed run's strongest eligible cohort. If the evidence gate does not clear, the application abstains.",
    motif: "One frame · one supported direction",
  },
  {
    id: "bridge",
    number: "02",
    name: "Bridge",
    phrase: "Connect two worlds only when the source connects them.",
    description: "A cultural link needs a returned relationship or validated source attribution. Similar wording alone is never enough.",
    motif: "Two fields · a visible join",
  },
  {
    id: "frontier",
    number: "03",
    name: "Frontier",
    phrase: "Explore the edge that still has a source.",
    description: "A more exploratory alternative is shown only when it clears the evidence gate in the same scoring context; novelty is not effectiveness.",
    motif: "Open crop · evidence limits in view",
  },
] as const;

type LensId = (typeof LENSES)[number]["id"];

export default function HomeMultiversePreview() {
  const [active, setActive] = useState<LensId>("anchor");
  const lens = LENSES.find((item) => item.id === active)!;

  return (
    <section className="nightfall-multiverse" id="multiverse-preview" aria-labelledby="nightfall-multiverse-title">
      <div className="nightfall-content-shell">
        <div className="nightfall-section-heading">
          <div>
            <p className="nightfall-kicker">Cultural Multiverse · design preview</p>
            <h2 id="nightfall-multiverse-title">Three ways to stand<br /><em>a film</em> in culture.</h2>
          </div>
          <p className="nightfall-section-deck">The Positioning Arena compares defensible directions after a completed Creator investigation. This homepage panel is a design preview—not an analysis of your film.</p>
        </div>

        <div className="nightfall-concept-banner" role="note">
          <span className="nightfall-live-dot" aria-hidden="true" />
          CONCEPT PREVIEW · ILLUSTRATIVE INTERACTION · NOT A LIVE QLOO ANALYSIS
        </div>

        <div className="nightfall-lens-tabs" role="tablist" aria-label="Illustrative positioning lenses">
          {LENSES.map((item) => (
            <button
              key={item.id}
              id={`home-lens-tab-${item.id}`}
              type="button"
              role="tab"
              aria-selected={active === item.id}
              aria-controls="home-lens-panel"
              className={active === item.id ? "is-active" : ""}
              onClick={() => setActive(item.id)}
            >
              <span>{item.number} · {item.motif}</span>
              <strong>{item.name}</strong>
              <small>{item.phrase}</small>
            </button>
          ))}
        </div>

        <div className={`nightfall-lens-panel is-${active}`} id="home-lens-panel" role="tabpanel" aria-labelledby={`home-lens-tab-${active}`}>
          <div className="nightfall-lens-art" aria-label="Schematic illustration, not source evidence" role="img">
            <div className="nightfall-lens-art-image" />
            <div className="nightfall-lens-art-shade" />
            <svg viewBox="0 0 600 380" aria-hidden="true">
              <path d={active === "bridge" ? "M90 178 C210 70 390 310 510 165" : active === "frontier" ? "M300 190 C350 100 460 100 520 52" : "M300 190 C245 130 175 115 92 88"} />
              <circle cx="300" cy="190" r="35" className="subject" />
              <circle cx="300" cy="190" r="54" className="orbit" />
              <circle cx="92" cy={active === "bridge" ? "178" : "88"} r="10" />
              {active === "bridge" && <circle cx="510" cy="165" r="10" />}
              {active === "frontier" && <circle cx="520" cy="52" r="10" />}
              {active === "anchor" && <circle cx="92" cy="88" r="10" />}
              <text x="300" y="186" textAnchor="middle">FILM</text>
              <text x="300" y="203" textAnchor="middle" className="diagram-sub">SCHEMATIC ONLY</text>
            </svg>
            <span className="nightfall-art-caption">Cultural field · illustrative diagram</span>
          </div>
          <div className="nightfall-lens-copy">
            <p className="nightfall-kicker">{lens.number} / {lens.name} · positioning lens</p>
            <h3>{lens.phrase}</h3>
            <p>{lens.description}</p>
            <dl className="nightfall-limits-list">
              <div><dt>Input</dt><dd>One completed Creator run</dd></div>
              <div><dt>Evidence</dt><dd>Returned sources and trace only</dd></div>
              <div><dt>When unsupported</dt><dd>Show why it abstains</dd></div>
            </dl>
            <p className="nightfall-lens-limit">Cultural affinity is similarity evidence—not audience size, viewing probability, attendance, conversion, revenue, or causal lift.</p>
          </div>
        </div>
        <p className="nightfall-source-note">This preview is intentionally kept separate from entered film details, measured Qloo evidence, and saved experiments.</p>
      </div>
    </section>
  );
}
