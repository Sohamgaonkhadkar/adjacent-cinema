"use client";

/**
 * IntakeForm — the real programme intake for Adjacent.
 *
 * The programmer enters their venue, city and recent film titles. Nothing is
 * submitted implicitly: the sample programme is a deliberate, labelled demo
 * action, and the submitted values are exactly what reaches the backend.
 */

import { useState } from "react";
import { DEMO_PROGRAMME, type ProgrammeItemInput } from "@/lib/api";

interface Row {
  title: string;
  year: string;
  imdb: string;
}

interface RowErrors {
  title?: string;
  year?: string;
  imdb?: string;
}

interface Props {
  onSubmit: (city: string, venue: string, programme: ProgrammeItemInput[]) => void;
  loading: boolean;
}

const EMPTY_ROW: Row = { title: "", year: "", imdb: "" };

function isEmptyRow(row: Row): boolean {
  return !row.title.trim() && !row.year.trim() && !row.imdb.trim();
}

export default function IntakeForm({ onSubmit, loading }: Props) {
  const [venue, setVenue] = useState("");
  const [city, setCity] = useState("");
  const [rows, setRows] = useState<Row[]>([{ ...EMPTY_ROW }, { ...EMPTY_ROW }, { ...EMPTY_ROW }]);
  const [venueError, setVenueError] = useState<string | null>(null);
  const [cityError, setCityError] = useState<string | null>(null);
  const [rowErrors, setRowErrors] = useState<RowErrors[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [sampleLoaded, setSampleLoaded] = useState(false);

  function updateRow(index: number, field: keyof Row, value: string) {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, [field]: value } : r)));
    setSampleLoaded(false);
  }

  function addRow() {
    setRows((prev) => [...prev, { ...EMPTY_ROW }]);
  }

  function removeRow(index: number) {
    setRows((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)));
    setSampleLoaded(false);
  }

  function loadSample() {
    setRows(
      DEMO_PROGRAMME.map((p) => ({
        title: p.title,
        year: p.year != null ? String(p.year) : "",
        imdb: p.imdb_id ?? "",
      }))
    );
    setSampleLoaded(true);
    setRowErrors([]);
    setFormError(null);
  }

  function validate(): { venue: string; city: string; programme: ProgrammeItemInput[] } | null {
    const errors: RowErrors[] = rows.map(() => ({}));
    let venueErr: string | null = null;
    let cityErr: string | null = null;
    let formErr: string | null = null;

    const venueTrimmed = venue.trim();
    const cityTrimmed = city.trim();
    if (!venueTrimmed) venueErr = "Enter the cinema or venue name.";
    if (!cityTrimmed) cityErr = "Enter the city or locality.";

    const programme: ProgrammeItemInput[] = [];
    rows.forEach((row, i) => {
      if (isEmptyRow(row)) return; // blank rows are simply ignored
      const title = row.title.trim();
      if (!title) {
        errors[i].title = "A row with a year or IMDb ID needs a title.";
        return;
      }
      let year: number | undefined;
      if (row.year.trim()) {
        const parsed = Number(row.year.trim());
        if (!Number.isInteger(parsed) || parsed < 1888 || parsed > 2100) {
          errors[i].year = "Year must be between 1888 and 2100.";
        } else {
          year = parsed;
        }
      }
      let imdb: string | undefined;
      if (row.imdb.trim()) {
        const value = row.imdb.trim();
        if (!/^tt\d{7,8}$/i.test(value)) {
          errors[i].imdb = "IMDb IDs look like tt0109424.";
        } else {
          imdb = value;
        }
      }
      if (!errors[i].title && !errors[i].year && !errors[i].imdb) {
        programme.push({ title, year, imdb_id: imdb });
      }
    });

    if (programme.length === 0 && !formErr) {
      formErr = "Add at least one film title to analyse.";
    }

    setVenueError(venueErr);
    setCityError(cityErr);
    setRowErrors(errors);
    setFormError(formErr);

    if (venueErr || cityErr || formErr || errors.some((e) => e.title || e.year || e.imdb)) {
      return null;
    }
    return { venue: venueTrimmed, city: cityTrimmed, programme };
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return; // no duplicate submissions
    const valid = validate();
    if (!valid) return;
    // Entries stay in the form after submit — if the run fails, nothing is lost.
    onSubmit(valid.city, valid.venue, valid.programme);
  }

  return (
    <form onSubmit={handleSubmit} className="intake-card" noValidate>
      <div className="intake-head">
        <div>
          <span className="micro-label">YOUR PROGRAMME IN / CULTURAL FIELD OUT</span>
          <h3 className="intake-title">
            Run an analysis <em>on your programme.</em>
          </h3>
        </div>
        <button
          type="button"
          className="intake-sample-btn"
          onClick={loadSample}
          disabled={loading}
          title="Load six verified sample titles — a deliberate demo choice"
        >
          Load sample programme
        </button>
      </div>

      {sampleLoaded && (
        <p className="intake-sample-note">
          <span className="intake-sample-badge">SAMPLE</span>
          Six verified demo titles loaded. They will be resolved and analysed like any other
          programme — nothing here is a pre-computed result.
        </p>
      )}

      <div className="intake-grid">
        <div className="intake-field">
          <label className="micro-label" htmlFor="intake-venue">CINEMA / VENUE</label>
          <input
            id="intake-venue"
            className={`intake-input${venueError ? " has-error" : ""}`}
            type="text"
            value={venue}
            onChange={(e) => setVenue(e.target.value)}
            placeholder="e.g. Prince Charles Cinema"
            maxLength={120}
            autoComplete="organization"
          />
          {venueError && <span className="intake-field-error">{venueError}</span>}
        </div>
        <div className="intake-field">
          <label className="micro-label" htmlFor="intake-city">CITY / LOCALITY</label>
          <input
            id="intake-city"
            className={`intake-input${cityError ? " has-error" : ""}`}
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="e.g. London, UK"
            maxLength={120}
            autoComplete="address-level2"
          />
          {cityError && <span className="intake-field-error">{cityError}</span>}
        </div>
      </div>

      <div className="intake-rows-head">
        <span className="micro-label">RECENT / RELEVANT FILMS</span>
        <span className="mono-note">TITLE REQUIRED · YEAR AND IMDb ID HELP RESOLUTION</span>
      </div>

      <div className="intake-rows">
        {rows.map((row, i) => (
          <div className="intake-row" key={i}>
            <span className="intake-row-index">0{i + 1}</span>
            <div className="intake-row-fields">
              <input
                className={`intake-input${rowErrors[i]?.title ? " has-error" : ""}`}
                type="text"
                value={row.title}
                onChange={(e) => updateRow(i, "title", e.target.value)}
                placeholder="Film title"
                aria-label={`Film ${i + 1} title`}
                maxLength={200}
              />
              {rowErrors[i]?.title && <span className="intake-field-error">{rowErrors[i].title}</span>}
            </div>
            <div className="intake-row-fields intake-year">
              <input
                className={`intake-input${rowErrors[i]?.year ? " has-error" : ""}`}
                type="text"
                inputMode="numeric"
                value={row.year}
                onChange={(e) => updateRow(i, "year", e.target.value)}
                placeholder="Year"
                aria-label={`Film ${i + 1} year`}
                maxLength={4}
              />
              {rowErrors[i]?.year && <span className="intake-field-error">{rowErrors[i].year}</span>}
            </div>
            <div className="intake-row-fields intake-imdb">
              <input
                className={`intake-input${rowErrors[i]?.imdb ? " has-error" : ""}`}
                type="text"
                value={row.imdb}
                onChange={(e) => updateRow(i, "imdb", e.target.value)}
                placeholder="tt0109424"
                aria-label={`Film ${i + 1} IMDb ID`}
                maxLength={12}
              />
              {rowErrors[i]?.imdb && <span className="intake-field-error">{rowErrors[i].imdb}</span>}
            </div>
            <button
              type="button"
              className="intake-remove"
              onClick={() => removeRow(i)}
              disabled={rows.length <= 1 || loading}
              aria-label={`Remove film ${i + 1}`}
              title="Remove this row"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="intake-actions">
        <button type="button" className="intake-add-btn" onClick={addRow} disabled={loading}>
          + Add film
        </button>
        <button type="submit" className="intake-submit" disabled={loading}>
          {loading ? "Starting analysis…" : "Analyse programme with Qloo"}
        </button>
      </div>

      {formError && <p className="intake-form-error">{formError}</p>}

      <p className="intake-fineprint">
        Films are resolved against the Qloo taste graph. Unresolved titles are reported, never
        guessed. A live analysis requires a configured QLOO_API_KEY on the backend — without one
        the run fails with an explicit message.
      </p>
    </form>
  );
}
