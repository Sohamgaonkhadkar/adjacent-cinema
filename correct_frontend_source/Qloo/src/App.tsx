import { useEffect, useState, type FormEvent } from "react";
import { cinema } from "./data/cinema";
import { culturalConnections } from "./data/culturalConnections";
import { culturalEntities } from "./data/culturalEntities";
import { films } from "./data/films";
import { images } from "./data/images";
import { programmeBet } from "./data/programmeBet";
import { testCard as initialTestCard } from "./data/testCard";
import type { TestCard, Venue } from "./data/types";
import { venues } from "./data/venues";

const navItems = [
  { id: "cinema", label: "Cinema" },
  { id: "programme", label: "Programme" },
  { id: "field", label: "Cultural field" },
  { id: "opportunity", label: "Opportunity" },
  { id: "test-card", label: "Test" },
];

const graphCenter = { id: "cinema", x: 500, y: 310 };
const graphEntities = new Map(culturalEntities.map((entity) => [entity.id, entity]));
const mapBounds = { minLongitude: -0.21, maxLongitude: -0.065, minLatitude: 51.495, maxLatitude: 51.55 };
const mapRoads = [
  "M 28 119 C 176 96 238 143 360 126 S 569 95 704 130 S 868 157 1006 118",
  "M 19 185 C 161 212 280 177 400 203 S 580 236 738 197 S 897 183 1010 213",
  "M 24 280 C 178 253 275 293 397 271 S 572 246 715 288 S 868 329 1008 292",
  "M 13 345 C 164 324 286 353 393 334 S 591 314 720 351 S 893 384 1004 348",
  "M 20 392 C 149 370 287 409 383 389 S 589 368 707 397 S 888 428 1007 393",
  "M 59 58 C 135 154 126 219 176 283 S 232 402 204 574",
  "M 173 30 C 244 130 229 207 290 275 S 342 416 324 588",
  "M 397 22 C 348 114 371 204 414 273 S 449 431 429 602",
  "M 561 19 C 533 118 559 191 583 276 S 597 429 571 605",
  "M 741 26 C 684 124 712 205 759 275 S 794 440 752 596",
  "M 887 38 C 842 145 862 226 900 305 S 919 448 892 588",
  "M 88 515 C 224 478 324 504 423 496 S 628 510 733 484 S 885 483 991 513",
];

type VenueFilter = "ALL" | Venue["category"];

function mapPoint(venue: Venue) {
  const x = 60 + ((venue.longitude - mapBounds.minLongitude) / (mapBounds.maxLongitude - mapBounds.minLongitude)) * 880;
  const y = 30 + ((mapBounds.maxLatitude - venue.latitude) / (mapBounds.maxLatitude - mapBounds.minLatitude)) * 550;
  return { x, y };
}

function categoryClass(category: Venue["category"]) {
  return category.toLowerCase().replace(/ /g, "-");
}

function PhotoCredit({ imageKey }: { imageKey: string }) {
  const image = images[imageKey];
  return (
    <a
      className="photo-credit"
      href={image.attributionUrl}
      target="_blank"
      rel="noreferrer"
      aria-label={`Photo by ${image.photographer}, sourced from ${image.source}`}
      title={`${image.photographer} / ${image.source} / ${image.license}`}
    >
      <span aria-hidden="true">PHOTO</span>
      <span>{image.photographer}</span>
      <span className="credit-arrow" aria-hidden="true">↗</span>
    </a>
  );
}

function ImageFigure({ imageKey, className = "" }: { imageKey: string; className?: string }) {
  const image = images[imageKey];
  return (
    <figure className={`editorial-image ${className}`}>
      <img src={image.src} alt={image.alt} loading="lazy" />
      <PhotoCredit imageKey={imageKey} />
    </figure>
  );
}

function GraphField({ selectedId, onSelect }: { selectedId: string; onSelect: (id: string) => void }) {
  const getPoint = (id: string) => (id === "cinema" ? graphCenter : graphEntities.get(id));

  return (
    <svg className="field-svg" viewBox="0 0 1000 620" role="img" aria-label="Interactive cultural adjacency field around Prince Charles Cinema">
      <title>Cultural connections around Prince Charles Cinema</title>
      <defs>
        <radialGradient id="field-wash" cx="50%" cy="50%" r="55%">
          <stop offset="0%" stopColor="#b88a5c" stopOpacity="0.11" />
          <stop offset="100%" stopColor="#b88a5c" stopOpacity="0" />
        </radialGradient>
      </defs>
      <ellipse className="field-wash" cx="500" cy="310" rx="230" ry="180" fill="url(#field-wash)" />
      <ellipse className="field-orbit" cx="500" cy="310" rx="246" ry="185" />
      <ellipse className="field-orbit field-orbit--outer" cx="500" cy="310" rx="407" ry="272" />
      {culturalConnections.map((connection) => {
        const from = getPoint(connection.from);
        const to = getPoint(connection.to);
        if (!from || !to) return null;
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const curve = connection.signal === "REPEATED" ? -0.12 : 0.1;
        const cx = (from.x + to.x) / 2 + dy * curve;
        const cy = (from.y + to.y) / 2 - dx * curve;
        const active = connection.from === selectedId || connection.to === selectedId;
        return (
          <path
            key={connection.id}
            className={`field-link field-link--${connection.signal.toLowerCase()}${active ? " is-related" : ""}`}
            d={`M ${from.x} ${from.y} Q ${cx} ${cy} ${to.x} ${to.y}`}
          />
        );
      })}
      {culturalEntities.map((entity) => {
        const selected = selectedId === entity.id;
        const isCinema = entity.id === "cinema";
        const alignRight = entity.x > 790;
        const labelX = alignRight ? -15 : 15;
        const labelAnchor = alignRight ? "end" : "start";
        return (
          <g
            key={entity.id}
            className={`field-node field-node--${entity.kind.toLowerCase()}${selected ? " is-selected" : ""}${isCinema ? " is-origin" : ""}`}
            transform={`translate(${entity.x} ${entity.y})`}
            role="button"
            aria-label={`${entity.name}. ${entity.domain}. ${entity.relationship}`}
            aria-pressed={selected}
            tabIndex={0}
            onClick={() => onSelect(entity.id)}
            onMouseEnter={() => onSelect(entity.id)}
            onFocus={() => onSelect(entity.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(entity.id);
              }
            }}
          >
            {isCinema && <circle className="node-halo" r="36" />}
            <circle className="node-ring" r={isCinema ? 22 : entity.kind === "DOMAIN" ? 10 : 7} />
            <circle className="node-dot" r={isCinema ? 3 : 2} />
            {isCinema ? (
              <>
                <text className="field-label field-label--origin" x="0" y="-43" textAnchor="middle">PRINCE CHARLES</text>
                <text className="field-micro field-micro--origin" x="0" y="48" textAnchor="middle">CINEMA · LONDON</text>
              </>
            ) : (
              <>
                <text className="field-label" x={labelX} y="-2" textAnchor={labelAnchor}>{entity.name}</text>
                <text className="field-micro" x={labelX} y="13" textAnchor={labelAnchor}>{entity.kind === "DOMAIN" ? entity.domain : entity.kind}</text>
              </>
            )}
          </g>
        );
      })}
    </svg>
  );
}

function App() {
  const [activeChapter, setActiveChapter] = useState("cinema");
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedFilmId, setSelectedFilmId] = useState("past-lives");
  const [selectedEntityId, setSelectedEntityId] = useState("bryce-dessner");
  const [venueFilter, setVenueFilter] = useState<VenueFilter>("ALL");
  const [selectedVenueId, setSelectedVenueId] = useState("prince-charles");
  const [showCulturalLinks, setShowCulturalLinks] = useState(true);
  const [openEvidenceId, setOpenEvidenceId] = useState("adjacency");
  const [test, setTest] = useState<TestCard>(initialTestCard);
  const [editorDraft, setEditorDraft] = useState<TestCard | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);

  useEffect(() => {
    const sections = Array.from(document.querySelectorAll<HTMLElement>("[data-chapter]"));
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!visible) return;
        const section = visible.target as HTMLElement;
        setActiveChapter(section.dataset.chapter ?? "cinema");
        section.classList.add("is-entered");
      },
      { threshold: [0.18, 0.36, 0.55], rootMargin: "-8% 0px -12% 0px" },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!editorOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setEditorOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [editorOpen]);

  const selectedFilm = films.find((film) => film.id === selectedFilmId) ?? films[0];
  const selectedEntity = graphEntities.get(selectedEntityId) ?? culturalEntities[0];
  const selectedVenue = venues.find((venue) => venue.id === selectedVenueId) ?? venues[0];
  const visibleVenues = venues.filter((venue) => venueFilter === "ALL" || venue.category === venueFilter);
  const betParts = test.bet.split("×").map((part) => part.trim());
  const betLead = betParts.length > 1 ? betParts[0] : "Cinema";
  const betTerritory = betParts.length > 1 ? betParts.slice(1).join(" × ") : betParts[0];
  const activeNavId = activeChapter === "where" || activeChapter === "bet"
    ? "opportunity"
    : activeChapter === "test-card"
      ? "test-card"
      : activeChapter;
  const selectedImageKey = selectedVenue.id === "barbican" || selectedVenue.id === "kings-place"
    ? "barbican"
    : selectedVenue.id === "tate-modern"
      ? "galleryVisitors"
      : selectedVenue.category === "CINEMA"
        ? "cinemaAudience"
        : "concertCrowd";

  function selectVenueFilter(filter: VenueFilter) {
    setVenueFilter(filter);
    if (filter !== "ALL" && selectedVenue.category !== filter) {
      const nextVenue = venues.find((venue) => venue.category === filter);
      if (nextVenue) setSelectedVenueId(nextVenue.id);
    }
  }

  function openEditor() {
    setEditorDraft({ ...test });
    setEditorOpen(true);
  }

  function saveEditor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (editorDraft) setTest({ ...editorDraft });
    setEditorOpen(false);
  }

  function updateDraft<K extends keyof TestCard>(key: K, value: TestCard[K]) {
    setEditorDraft((draft) => draft ? { ...draft, [key]: value } : draft);
  }

  function exportTestCard() {
    const text = [
      "ADJACENT / PROGRAMME EXPERIMENT",
      "ILLUSTRATIVE DEMO DATA - NOT AN AUDIENCE FORECAST",
      "",
      `BET: ${test.bet}`,
      `CANDIDATE: ${test.candidate}`,
      `FORMAT: ${test.format}`,
      `PARTNER TYPE: ${test.partnerType}`,
      `LOCATION: ${test.location}`,
      "",
      `HYPOTHESIS: ${test.hypothesis}`,
      "",
      "SUCCESS SIGNALS:",
      ...test.successSignals.map((signal) => `- ${signal}`),
      "",
      "FAILURE CONDITIONS:",
      ...test.failureConditions.map((condition) => `- ${condition}`),
      "",
      "Evidence is illustrative mock data. No live Qloo connection or audience prediction is used.",
    ].join("\n");
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "adjacent-programme-experiment.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <main className="adjacent-app">
      <header className={`site-header${menuOpen ? " menu-is-open" : ""}`}>
        <a className="header-brand" href="#cinema" onClick={() => setMenuOpen(false)} aria-label="Adjacent, back to the beginning">
          <span className="header-wordmark">ADJACENT</span>
          <span className="header-descriptor">CULTURAL INTELLIGENCE<br />FOR INDEPENDENT CINEMAS</span>
        </a>
        <nav className="main-nav" aria-label="Story chapters">
          {navItems.map((item, index) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className={activeNavId === item.id ? "is-current" : ""}
              onClick={() => setMenuOpen(false)}
            >
              <span className="nav-index">0{index + 1}</span>
              {item.label}
            </a>
          ))}
        </nav>
        <button className="mobile-menu-button" type="button" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
          <span>{menuOpen ? "CLOSE" : "CHAPTERS"}</span>
          <span className={`menu-mark${menuOpen ? " is-open" : ""}`} aria-hidden="true"><i /><i /></span>
        </button>
      </header>

      <section id="cinema" className="story-section hero-section" data-chapter="cinema">
        <div className="hero-image-wrap" aria-hidden="true">
          <img className="hero-image" src={images[cinema.imageKey].src} alt="" fetchPriority="high" />
        </div>
        <div className="hero-shade" aria-hidden="true" />
        <div className="hero-content">
          <p className="hero-product reveal">ADJACENT</p>
          <p className="eyebrow hero-eyebrow reveal"><span>01</span> CINEMA / A CULTURAL FIELD NOTE</p>
          <h1 className="hero-title reveal">Find the audience<br /><em>you haven't met yet.</em></h1>
          <p className="hero-deck reveal">Discover cultural territory adjacent to the films you already programme.</p>
          <a className="text-link hero-cta reveal" href="#programme">
            <span>Enter cinema</span><span className="link-arrow" aria-hidden="true">→</span>
          </a>
        </div>
        <div className="hero-footer reveal">
          <div>
            <span className="micro-label">A DEMO FOR</span>
            <strong>{cinema.name}</strong>
            <span>{cinema.city.toUpperCase()} / {cinema.country.toUpperCase()}</span>
          </div>
          <div className="hero-foot-note">
            <span className="micro-label">A DIFFERENT KIND OF PROGRAMME INTELLIGENCE</span>
            <span>Films in / cultural connections out</span>
          </div>
          <PhotoCredit imageKey={cinema.imageKey} />
        </div>
        <a className="hero-scroll" href="#programme" aria-label="Scroll to the programme">
          <span>SCROLL TO BEGIN</span><i aria-hidden="true" />
        </a>
      </section>

      <section id="programme" className="story-section programme-section" data-chapter="programme">
        <div className="section-shell">
          <div className="section-head programme-head reveal">
            <div>
              <p className="eyebrow"><span>02</span> THE STARTING POINT</p>
              <h2>What you already<br /><em>programme.</em></h2>
            </div>
            <div className="programme-intro">
              <p>Before looking outward, read the shape of the programme already in the room.</p>
              <span className="mono-note">RECENT SCREENINGS / ILLUSTRATIVE SAMPLE</span>
            </div>
          </div>

          <div className="filmstrip" aria-label="Recent programme, horizontally scrollable">
            {films.map((film, index) => {
              const image = images[film.imageKey];
              const isSelected = selectedFilm.id === film.id;
              return (
                <article key={film.id} className={`film-item${isSelected ? " is-selected" : ""}`}>
                  <button className="film-image-button" type="button" onClick={() => setSelectedFilmId(film.id)} aria-pressed={isSelected} aria-label={`Inspect ${film.title}`}>
                    <img src={image.src} alt={`${image.alt} Editorial photography, not official artwork for ${film.title}.`} loading="lazy" />
                    <span className="film-image-shade" aria-hidden="true" />
                    <span className="film-number">0{index + 1}</span>
                    <span className="film-hover-meta"><span>{film.director}</span><span>{film.genre}</span></span>
                  </button>
                  <div className="film-caption">
                    <div className="film-title-line"><h3>{film.title}</h3><span>{film.year}</span></div>
                    <p>{film.genre}</p>
                    <a href={image.attributionUrl} target="_blank" rel="noreferrer" className="film-credit">PHOTO / {image.photographer}</a>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="programme-bottom reveal">
            <div className="film-detail" aria-live="polite">
              <span className="micro-label">IN THE SAMPLE / {selectedFilm.year}</span>
              <span className="film-detail-name">{selectedFilm.title}</span>
              <span className="film-detail-note">{selectedFilm.programmeNote}</span>
            </div>
            <div className="strip-instruction"><span>DRAG TO EXPLORE</span><span aria-hidden="true">↔</span></div>
          </div>
          <p className="image-note">Editorial photography, not official film stills. Image credits link to their Pexels source.</p>
        </div>
      </section>

      <section id="field" className="story-section field-section" data-chapter="field">
        <div className="section-shell">
          <div className="section-head field-heading reveal">
            <div>
              <p className="eyebrow"><span>03</span> CULTURAL FIELD / MOCK DATA</p>
              <h2>A programme is<br />a <em>cultural fingerprint.</em></h2>
            </div>
            <p className="section-deck">Follow the relationships outward. The useful signal is not a movie to recommend; it is a cultural territory the cinema could choose to enter.</p>
          </div>

          <div className="field-layout">
            <div className="field-stage reveal">
              <GraphField selectedId={selectedEntity.id} onSelect={setSelectedEntityId} />
              <div className="graph-legend"><span><i className="legend-dot legend-dot--anchor" /> PROGRAMME ANCHOR</span><span><i className="legend-dot legend-dot--signal" /> CULTURAL CONNECTION</span><span>SELECT A NODE TO INSPECT</span></div>
            </div>
            <aside className="entity-inspector reveal" aria-live="polite">
              <span className="micro-label">ENTITY / {selectedEntity.kind}</span>
              <h3>{selectedEntity.name}</h3>
              <p className="entity-domain">{selectedEntity.domain}</p>
              <p className="entity-description">{selectedEntity.description}</p>
              <dl className="evidence-readout">
                <div><dt>RELATION</dt><dd>{selectedEntity.relationship}</dd></div>
                <div><dt>ADJACENCY</dt><dd>{selectedEntity.adjacency}</dd></div>
                <div><dt>EVIDENCE</dt><dd>Illustrative cultural graph / programme sample</dd></div>
              </dl>
              <p className="demo-disclaimer">This field is mock data for the demo. It does not represent a live Qloo result or an audience forecast.</p>
            </aside>
          </div>
          <div className="field-footline"><span>PROGRAMME</span><i /> <span>CREATIVE PRACTICE</span><i /> <span>PLACE</span><span className="field-footline-note">RELATIONSHIPS ARE CULTURAL, NOT DEMOGRAPHIC.</span></div>
        </div>
      </section>

      <section id="opportunity" className="story-section gap-section" data-chapter="opportunity">
        <div className="section-shell">
          <div className="gap-header reveal">
            <div>
              <p className="eyebrow"><span>04</span> THE OPPORTUNITY / A PROGRAMME GAP</p>
              <h2>The cultural territory<br />you are <em>not yet exploring.</em></h2>
            </div>
            <p className="gap-deck">An adjacent direction should feel close enough to belong, and new enough to create a reason to visit.</p>
          </div>

          <div className="territory-comparison reveal">
            <div className="territory-column territory-current">
              <div className="territory-title"><span>01 / EXPRESSED</span><h3>What the cinema<br /><em>already programmes.</em></h3></div>
              <div className="density-list">
                {[
                  ["Independent film", "92%"],
                  ["Auteur-led work", "80%"],
                  ["Contemporary stories", "72%"],
                  ["Drama / romance", "63%"],
                  ["Visual authorship", "57%"],
                ].map(([label, width]) => (
                  <div className="density-row" key={label}>
                    <span>{label}</span><i><b style={{ width }} /></i><small>PRESENT</small>
                  </div>
                ))}
              </div>
            </div>
            <div className="territory-bridge" aria-hidden="true"><span>EXTEND</span><i /><b>→</b></div>
            <div className="territory-column territory-adjacent">
              <div className="territory-title"><span>02 / NEIGHBOURING</span><h3>Adjacent<br /><em>territory.</em></h3></div>
              <div className="density-list">
                {[
                  ["Contemporary classical", "86%"],
                  ["Live performance", "78%"],
                  ["Composer-led events", "69%"],
                  ["Experimental sound", "62%"],
                  ["Cultural venues", "55%"],
                ].map(([label, width]) => (
                  <div className="density-row" key={label}>
                    <span>{label}</span><i><b style={{ width }} /></i><small>ADJACENT</small>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="gap-conclusion reveal">
            <span className="micro-label">A DISTINCTION THAT MATTERS</span>
            <p>We are not predicting an audience.<br /><em>We are identifying a cultural direction worth testing.</em></p>
            <span className="gap-source">Illustrative visual summary / no audience percentages or attendance claims</span>
          </div>
        </div>
      </section>

      <section id="where" className="story-section where-section" data-chapter="where">
        <div className="section-shell">
          <div className="section-head where-heading reveal">
            <div>
              <p className="eyebrow"><span>05</span> WHERE / LONDON CULTURAL FIELD</p>
              <h2>Follow the culture<br /><em>into the city.</em></h2>
            </div>
            <p className="section-deck">A partner landscape, not an audience heatmap. Cultural places make the adjacent territory concrete.</p>
          </div>

          <div className="map-controls reveal">
            <div className="map-filters" role="group" aria-label="Filter map venues by type">
              {(["ALL", "CINEMA", "MUSIC", "ART", "CULTURAL SPACE"] as VenueFilter[]).map((filter) => (
                <button key={filter} type="button" className={venueFilter === filter ? "is-active" : ""} onClick={() => selectVenueFilter(filter)}>
                  {filter === "ALL" ? "ALL PLACES" : filter}
                </button>
              ))}
            </div>
            <button className={`map-layer-toggle${showCulturalLinks ? " is-on" : ""}`} type="button" onClick={() => setShowCulturalLinks(!showCulturalLinks)} aria-pressed={showCulturalLinks}>
              <span className="layer-switch" aria-hidden="true"><i /></span> CULTURAL LINKS
            </button>
          </div>

          <div className="map-layout">
            <div className="map-frame reveal">
              <div className="map-topline"><span>WEST / CENTRAL LONDON</span><span>DEMO VENUE FIELD / {visibleVenues.length} PLACES</span></div>
              <div className="map-plane">
                <svg className="london-map-svg" viewBox="0 0 1000 620" preserveAspectRatio="none" aria-hidden="true">
                  <defs>
                    <pattern id="map-grain" width="6" height="6" patternUnits="userSpaceOnUse">
                      <circle cx="1" cy="1" r="0.45" fill="#d2c9b5" opacity="0.18" />
                    </pattern>
                  </defs>
                  <rect width="1000" height="620" fill="#11120f" />
                  <path d="M35 54 L247 39 L276 148 L167 191 L33 165 Z M415 39 L573 40 L596 164 L438 188 Z M734 43 L965 64 L948 180 L767 192 Z M44 224 L186 201 L243 336 L91 365 Z M330 221 L469 213 L489 344 L361 375 Z M620 211 L772 220 L794 355 L654 345 Z M843 228 L973 219 L985 353 L868 378 Z" className="map-blocks" />
                  {mapRoads.map((road, index) => <path key={index} d={road} className="map-road" />)}
                  <path d="M-20 476 C 104 444 161 445 258 457 S 392 435 481 458 S 635 489 744 461 S 900 427 1020 465" className="river-bank" />
                  <path d="M-20 476 C 104 444 161 445 258 457 S 392 435 481 458 S 635 489 744 461 S 900 427 1020 465" className="river" />
                  <text x="484" y="483" className="river-label" transform="rotate(-4 484 483)">RIVER THAMES</text>
                  <text x="332" y="297" className="map-area-label">SOHO</text>
                  <text x="660" y="260" className="map-area-label">BARBICAN</text>
                  <text x="706" y="421" className="map-area-label">BANKSIDE</text>
                  <text x="409" y="90" className="map-area-label">CAMDEN</text>
                  <text x="182" y="515" className="map-area-label">SOUTH KENSINGTON</text>
                  {showCulturalLinks && visibleVenues.map((venue) => {
                    if (venue.id === "prince-charles") return null;
                    const origin = mapPoint(venues[0]);
                    const target = mapPoint(venue);
                    return <line key={venue.id} className={`map-connection map-connection--${categoryClass(venue.category)}`} x1={origin.x} y1={origin.y} x2={target.x} y2={target.y} />;
                  })}
                  <rect width="1000" height="620" fill="url(#map-grain)" />
                </svg>
                {visibleVenues.map((venue) => {
                  const position = mapPoint(venue);
                  const selected = selectedVenue.id === venue.id;
                  return (
                    <button
                      key={venue.id}
                      type="button"
                      className={`map-place map-place--${categoryClass(venue.category)}${selected ? " is-selected" : ""}`}
                      style={{ left: `${position.x / 10}%`, top: `${position.y / 6.2}%` }}
                      onClick={() => setSelectedVenueId(venue.id)}
                      aria-label={`${venue.name}, ${venue.type}, ${venue.area}`}
                      aria-pressed={selected}
                    >
                      <i className="map-point" aria-hidden="true" />
                      <span className="map-label">{venue.name}</span>
                    </button>
                  );
                })}
                <div className="map-north" aria-hidden="true"><span>N</span><i /></div>
                <div className="map-scale" aria-hidden="true"><i /><span>2 KM</span></div>
              </div>
              <div className="map-caption"><span>SCHEMATIC GEOGRAPHIC VIEW / VENUE LOCATIONS APPROXIMATED</span><span>NO AUDIENCE DENSITY IMPLIED</span></div>
            </div>

            <aside className="venue-inspector reveal" aria-live="polite">
              <span className="micro-label">PLACE / {selectedVenue.category}</span>
              <h3>{selectedVenue.name}</h3>
              <p className="venue-type">{selectedVenue.type}</p>
              <ImageFigure imageKey={selectedImageKey} className="venue-image" />
              <dl className="venue-readout">
                <div><dt>AREA</dt><dd>{selectedVenue.area}</dd></div>
                <div><dt>CULTURAL RELATION</dt><dd>{selectedVenue.relationship}</dd></div>
              </dl>
              <p className="venue-note">Mapped places are context for partner discovery. They are not evidence of shared attendance.</p>
            </aside>
          </div>
        </div>
      </section>

      <section id="bet" className="story-section bet-section" data-chapter="bet">
        <div className="bet-photo-wrap" aria-hidden="true">
          <img src={images.livePerformance.src} alt="" loading="lazy" />
        </div>
        <div className="bet-shade" aria-hidden="true" />
        <div className="bet-layout">
          <div className="bet-main reveal">
            <p className="eyebrow"><span>06</span> PROGRAMME BET / ONE THING TO TEST</p>
            <p className="bet-overline">ONE THING TO TEST</p>
            <h2><span>{betLead}</span><i aria-hidden="true">×</i><em>{betTerritory}</em></h2>
            <div className="bet-candidate"><span className="micro-label">ILLUSTRATIVE CANDIDATE</span><strong>{test.candidate}</strong><span>Composer / performer / cross-disciplinary practice</span></div>
            <a className="text-link bet-next" href="#test-card"><span>Make it a test</span><span className="link-arrow" aria-hidden="true">→</span></a>
          </div>
          <aside className="bet-rationale reveal">
            <div className="bet-rationale-head"><span className="micro-label">WHY THIS?</span><span className="demo-stamp">ILLUSTRATIVE DEMO / NOT A LIVE RECOMMENDATION</span></div>
            <p className="bet-summary">{programmeBet.summary}</p>
            <div className="bet-evidence-list">
              {programmeBet.evidence.map((evidence, index) => {
                const isOpen = openEvidenceId === evidence.id;
                return (
                  <div className={`bet-evidence${isOpen ? " is-open" : ""}`} key={evidence.id}>
                    <button type="button" aria-expanded={isOpen} onClick={() => setOpenEvidenceId(isOpen ? "" : evidence.id)}>
                      <span className="evidence-index">0{index + 1}</span>
                      <span className="evidence-source">{evidence.source}</span>
                      <span className="evidence-type">{evidence.type.replace(/_/g, " ")}</span>
                      <span className="evidence-toggle" aria-hidden="true">{isOpen ? "−" : "+"}</span>
                    </button>
                    {isOpen && <div className="evidence-detail"><p>{evidence.description}</p><span>STATUS / {evidence.status}</span></div>}
                  </div>
                );
              })}
            </div>
            <p className="bet-no-prediction">Cultural adjacency is a programming lens, not an audience prediction.</p>
          </aside>
        </div>
        <PhotoCredit imageKey="livePerformance" />
      </section>

      <section id="test-card" className="story-section test-section" data-chapter="test-card">
        <div className="test-shell">
          <div className="test-topline reveal">
            <p className="eyebrow"><span>07</span> TAKE IT INTO THE WORLD</p>
            <span className="test-edition">ADJACENT / FIELD NOTE 001<br />LONDON / WORKING COPY</span>
          </div>
          <div className="test-heading reveal">
            <h2>Programme<br /><em>experiment.</em></h2>
            <p>A bounded test of a cultural adjacency. Not a new identity for the cinema.</p>
          </div>

          <article className="test-sheet reveal" aria-label="Programme experiment test card">
            <div className="sheet-rule sheet-rule--top"><span>PROGRAMME EXPERIMENT</span><span>DEMO DATA / EDITABLE</span></div>
            <div className="sheet-bet-row">
              <div className="sheet-bet"><span className="micro-label">THE BET</span><h3>{test.bet}</h3><p>Candidate / {test.candidate}</p></div>
              <dl className="sheet-meta">
                <div><dt>FORMAT</dt><dd>{test.format}</dd></div>
                <div><dt>PARTNER TYPE</dt><dd>{test.partnerType}</dd></div>
                <div><dt>LOCATION</dt><dd>{test.location}</dd></div>
              </dl>
            </div>
            <div className="sheet-hypothesis">
              <span className="micro-label">HYPOTHESIS</span>
              <p>“{test.hypothesis}”</p>
            </div>
            <div className="sheet-signals">
              <div><span className="micro-label">SUCCESS SIGNALS</span><ul>{test.successSignals.map((signal) => <li key={signal}>{signal}</li>)}</ul></div>
              <div><span className="micro-label">FAILURE CONDITIONS</span><ul>{test.failureConditions.map((condition) => <li key={condition}>{condition}</li>)}</ul></div>
            </div>
            <div className="sheet-rule sheet-rule--bottom"><span>NO ATTENDANCE TARGETS / NO CONVERSION CLAIMS</span><span>REVIEW AFTER THE EXPERIMENT</span></div>
          </article>

          <div className="test-actions reveal">
            <div className="test-disclaimer">This demo is built from illustrative mock data. It has no live cultural data connection, booking information or audience forecast.</div>
            <div className="action-group">
              <button className="button-primary" type="button" onClick={exportTestCard}>Export test card <span aria-hidden="true">↓</span></button>
              <button className="button-secondary" type="button" onClick={openEditor}>Edit bet</button>
              <a className="button-tertiary" href="#field">Back to cultural field <span aria-hidden="true">↗</span></a>
            </div>
          </div>
          <footer className="test-footer"><span>ADJACENT / CULTURAL INTELLIGENCE FOR INDEPENDENT CINEMAS</span><span>HERE IS THE DECISION. NOW GO TEST IT.</span></footer>
        </div>
      </section>

      {editorOpen && editorDraft && (
        <div className="modal-scrim" onMouseDown={(event) => { if (event.target === event.currentTarget) setEditorOpen(false); }}>
          <section className="editor-dialog" role="dialog" aria-modal="true" aria-labelledby="editor-title">
            <div className="editor-header"><div><span className="micro-label">REFINE THE EXPERIMENT</span><h2 id="editor-title">Edit the bet.</h2></div><button type="button" className="editor-close" onClick={() => setEditorOpen(false)} aria-label="Close editor">×</button></div>
            <form onSubmit={saveEditor}>
              <label>Programme bet<input value={editorDraft.bet} onChange={(event) => updateDraft("bet", event.target.value)} /></label>
              <label>Candidate<input value={editorDraft.candidate} onChange={(event) => updateDraft("candidate", event.target.value)} /></label>
              <label>Format<input value={editorDraft.format} onChange={(event) => updateDraft("format", event.target.value)} /></label>
              <label>Partner type<input value={editorDraft.partnerType} onChange={(event) => updateDraft("partnerType", event.target.value)} /></label>
              <label>Location<input value={editorDraft.location} onChange={(event) => updateDraft("location", event.target.value)} /></label>
              <label>Hypothesis<textarea rows={3} value={editorDraft.hypothesis} onChange={(event) => updateDraft("hypothesis", event.target.value)} /></label>
              <div className="editor-actions"><button className="button-primary" type="submit">Save experiment</button><button className="button-secondary" type="button" onClick={() => setEditorOpen(false)}>Cancel</button></div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}

export default App;