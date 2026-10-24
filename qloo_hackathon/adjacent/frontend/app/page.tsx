import Link from "next/link";
import HomeMultiversePreview from "@/components/HomeMultiversePreview";

const JOURNEY = [
  { number: "01", title: "Your film", body: "Title, logline, genre and comparable works. The intake becomes the subject of the investigation—not a source of assumed audience facts.", href: "/creator#intake" },
  { number: "02", title: "Investigation", body: "Resolve references, inspect the run status and follow the recorded provider trace. Unresolved inputs stay unresolved.", href: "/creator#analysis" },
  { number: "03", title: "Cultural Fingerprint", body: "Explore returned cohorts, member entities, exclusions and provenance from the completed analysis.", href: "/creator#fingerprint" },
  { number: "04", title: "Positioning Arena", body: "Compare Anchor, Bridge and Frontier when the evidence supports them; unsupported positions abstain.", href: "/creator#positioning" },
  { number: "05", title: "Decision Brief", body: "Review evidence-linked claims and limitations. Optional synthesis cannot replace missing evidence.", href: "/creator#brief" },
  { number: "06", title: "Test Card", body: "Edit a comparison, measure, decision rule and window. Export or save a plan; saving does not execute it.", href: "/creator#test-card" },
  { number: "07", title: "Archive", body: "Reopen planned experiments, append observations and preserve evaluations without rewriting history.", href: "/creator#experiments" },
];

const PRINCIPLES = [
  { number: "I", title: "Evidence or abstention", body: "Factual claims must be traceable to returned records. When the gate does not clear, the system says so." },
  { number: "II", title: "Affinity is not audience", body: "Qloo affinity is cultural similarity only. It is not audience size, viewing probability, attendance, conversion, revenue or causal lift." },
  { number: "III", title: "A loop, not an oracle", body: "Hypothesis → planned test → observation → evaluation. A plan is not an outcome, and missing data is not zero." },
];

export default function HomePage() {
  return (
    <main className="nightfall-home">
      <section className="nightfall-home-hero">
        <div className="nightfall-home-hero-image" aria-hidden="true" />
        <div className="nightfall-home-hero-shade" aria-hidden="true" />
        <div className="nightfall-film-grain" aria-hidden="true" />
        <div className="nightfall-home-hero-inner">
          <div className="nightfall-volume-line"><span>VOL. 01 · THE CULTURE ROOM</span><span>INDEPENDENT CINEMA / CULTURAL INTELLIGENCE</span></div>
          <div className="nightfall-home-title-block">
            <p className="nightfall-kicker">An evidence-led working room for film</p>
            <h1>Every film belongs<br />to more than <em>one world.</em></h1>
            <p className="nightfall-home-lede">Investigate cultural relationships, inspect their sources, and develop a positioning hypothesis worth testing. No invented audiences. No guaranteed outcomes.</p>
            <div className="nightfall-home-actions">
              <Link className="nightfall-button is-amber" href="/creator">Enter Creator Studio <span aria-hidden="true">↗</span></Link>
              <Link className="nightfall-button" href="/creator?demo=fixture">Explore labelled fixture</Link>
              <Link className="nightfall-text-link" href="/cinema">Cinema Mode <span aria-hidden="true">→</span></Link>
            </div>
          </div>
          <div className="nightfall-home-hero-footer"><span>Evidence before interpretation.</span><a href="https://www.pexels.com/photo/an-empty-cinema-7991486/" target="_blank" rel="noreferrer">Atmospheric image · Tima Miroshnichenko / Pexels</a></div>
        </div>
      </section>

      <section className="nightfall-journey-section" id="journey">
        <div className="nightfall-content-shell nightfall-journey-grid">
          <div className="nightfall-journey-intro">
            <p className="nightfall-kicker">The seven-stage Creator journey</p>
            <h2>From film brief<br />to <em>measured learning.</em></h2>
            <p>Each stage uses the current film and completed analysis context. Fixture demonstrations stay labelled; only persisted records appear in the archive.</p>
            <Link className="nightfall-text-link" href="/creator">Open Creator Studio <span aria-hidden="true">→</span></Link>
          </div>
          <ol className="nightfall-journey-list">
            {JOURNEY.map((step) => (
              <li key={step.number}>
                <span className="nightfall-step-number">{step.number}</span>
                <div><h3><Link href={step.href}>{step.title}</Link></h3><p>{step.body}</p></div>
                <span className="nightfall-step-arrow" aria-hidden="true">↗</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <HomeMultiversePreview />

      <section className="nightfall-principles-section">
        <div className="nightfall-content-shell">
          <p className="nightfall-kicker">The evidence boundary</p>
          <h2>Three rules the product<br /><em>cannot break.</em></h2>
          <div className="nightfall-principles-grid">
            {PRINCIPLES.map((principle) => (
              <article key={principle.number}>
                <span>{principle.number}</span><h3>{principle.title}</h3><p>{principle.body}</p>
              </article>
            ))}
          </div>
          <div className="nightfall-route-links">
            <Link href="/cinema"><span>01</span><strong>Cinema Mode</strong><small>Five chapters · programme, cultural field, opportunity, test</small><b aria-hidden="true">↗</b></Link>
            <Link href="/creator/sponsor"><span>02</span><strong>FilmSponsor</strong><small>Eight stages · source review and approval prerequisites</small><b aria-hidden="true">↗</b></Link>
          </div>
        </div>
      </section>
      <footer className="nightfall-home-footer"><span>ADJACENT · CULTURAL INTELLIGENCE FOR INDEPENDENT CINEMA</span><span>Concept preview is not live Qloo evidence.</span></footer>
    </main>
  );
}
