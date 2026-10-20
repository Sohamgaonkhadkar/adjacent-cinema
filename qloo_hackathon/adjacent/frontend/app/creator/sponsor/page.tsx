"use client";

// FilmSponsor — Creator Mode sponsorship workflow.
//
// Campaign intake → live brand discovery (evidence + limits) → creator-editable
// sponsorship drafts → official-source review → approval → export → manual
// outreach/outcomes. Brand candidates and affinity values appear ONLY from a
// live, measured discovery report; without the backend Qloo key the discovery
// section reports the unavailable-service state honestly. Nothing on this page
// fabricates brands, affinity values, programmes, or outcomes.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  addSponsorOutreach,
  addSponsorSourceReview,
  approveSponsorDraft,
  createSponsorCampaign,
  exportSponsorCampaign,
  getHealth,
  initializeSponsorGuestSession,
  getSponsorCampaign,
  listSponsorCampaigns,
  runSponsorDiscovery,
  saveSponsorDraft,
  type BackendHealth,
} from "@/lib/api";
import type {
  SponsorBrand,
  SponsorCampaign,
  SponsorCampaignDetail,
  SponsorDiscovery,
  SponsorDraft,
  SponsorExportPackage,
  SponsorFilmResolution,
  SponsorOutreachRecord,
} from "@/types/adjacent";

function matchTone(status: string) {
  if (status === "VERIFIED") return { color: "#7aba8a", border: "rgba(62,122,76,0.4)" };
  if (status === "AMBIGUOUS") return { color: "#c29a6e", border: "rgba(194,154,110,0.4)" };
  return { color: "#c97a6a", border: "rgba(201,122,106,0.4)" };
}

function affinityLabel(affinity: number | null): string {
  // Zero is an observed value; missing is never shown as zero.
  return affinity === null ? "no score" : affinity.toFixed(2);
}

const READING_LIMITS = [
  "Cultural affinity is not sponsorship likelihood, eligibility, budget, availability, or ROI.",
  "Brand candidates are for human relevance review only; no outreach or contact discovery is performed.",
  "Affinity values are per-query normalised; values from different queries are not comparable.",
  "Only entities with explicit brand-type evidence are presented as brands.",
];

export default function SponsorPage() {
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [guestAccess, setGuestAccess] = useState<"checking" | "ready" | "blocked" | "expired" | "error">("checking");
  const [guestAccessError, setGuestAccessError] = useState<string | null>(null);
  const [restartingGuest, setRestartingGuest] = useState(false);
  const [campaigns, setCampaigns] = useState<SponsorCampaign[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(true);
  const [campaignsError, setCampaignsError] = useState<string | null>(null);

  // Intake form
  const [filmTitle, setFilmTitle] = useState("");
  const [filmYear, setFilmYear] = useState("");
  const [imdbId, setImdbId] = useState("");
  const [themesText, setThemesText] = useState("");
  const [goals, setGoals] = useState("");
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  // Selected campaign
  const [detail, setDetail] = useState<SponsorCampaignDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Discovery
  const [discovering, setDiscovering] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [discoveryUnavailable, setDiscoveryUnavailable] = useState<string | null>(null);

  // Drafts
  const [draftBrand, setDraftBrand] = useState("");
  const [draftPitch, setDraftPitch] = useState("");
  const [editingDraftId, setEditingDraftId] = useState<string | null>(null);
  const [draftBusy, setDraftBusy] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);

  // Source review (per draft)
  const [reviewDraftId, setReviewDraftId] = useState<string | null>(null);
  const [reviewUrl, setReviewUrl] = useState("");
  const [reviewClaim, setReviewClaim] = useState("");
  const [reviewStatus, setReviewStatus] = useState("SUPPORTED_BY_OFFICIAL_SOURCE");
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  // Outreach
  const [outreachStatus, setOutreachStatus] = useState("CONTACTED");
  const [outreachMeasurement, setOutreachMeasurement] = useState("OBSERVED");
  const [outreachDraftId, setOutreachDraftId] = useState("");
  const [outreachDate, setOutreachDate] = useState("");
  const [outreachReplies, setOutreachReplies] = useState("");
  const [outreachMeetings, setOutreachMeetings] = useState("");
  const [outreachOutcome, setOutreachOutcome] = useState("");
  const [outreachNotes, setOutreachNotes] = useState("");
  const [outreachBusy, setOutreachBusy] = useState(false);
  const [outreachError, setOutreachError] = useState<string | null>(null);

  // Export
  const [exportPkg, setExportPkg] = useState<SponsorExportPackage | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [copied, setCopied] = useState(false);

  const reloadDetail = useCallback(async (campaignId: string) => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      setDetail(await getSponsorCampaign(campaignId));
    } catch {
      setDetailError("Could not load the campaign. It may have been removed.");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const reloadCampaigns = useCallback(async () => {
    setCampaignsLoading(true);
    setCampaignsError(null);
    try {
      setCampaigns(await listSponsorCampaigns());
    } catch {
      setCampaignsError("Could not load campaigns.");
    } finally {
      setCampaignsLoading(false);
    }
  }, []);

  const startGuestWorkspace = useCallback(async () => {
    setGuestAccess("checking");
    setGuestAccessError(null);
    setCampaignsLoading(true);
    try {
      const backend = await getHealth();
      setHealth(backend);
      if (backend.public_demo && !backend.filmsponsor_guest_enabled) {
        setGuestAccess("blocked");
        setCampaignsLoading(false);
        return;
      }
      if (backend.filmsponsor_guest_enabled) await initializeSponsorGuestSession();
      setGuestAccess("ready");
      await reloadCampaigns();
    } catch (err) {
      setGuestAccess("error");
      setGuestAccessError(err instanceof Error ? err.message : "Guest workspace is unavailable.");
      setCampaignsLoading(false);
    }
  }, [reloadCampaigns]);

  useEffect(() => {
    void startGuestWorkspace();
    const expired = () => setGuestAccess("expired");
    window.addEventListener("filmsponsor-session-expired", expired);
    return () => window.removeEventListener("filmsponsor-session-expired", expired);
  }, [startGuestWorkspace]);

  async function handleGuestRecovery() {
    setRestartingGuest(true);
    try {
      await startGuestWorkspace();
      setDetail(null);
      setExportPkg(null);
    } finally {
      setRestartingGuest(false);
    }
  }

  if (guestAccess !== "ready") {
    const message = guestAccess === "checking"
      ? "Initializing an isolated workspace…"
      : guestAccess === "blocked"
        ? "This public demo has not enabled isolated FilmSponsor guest workspaces. Shared campaigns remain protected."
        : guestAccess === "expired"
          ? "This guest workspace expired or was revoked. Start a new isolated workspace to continue."
          : guestAccessError || "FilmSponsor could not initialize. Please retry.";
    return (
      <main style={{ background: "var(--void)", minHeight: "100vh", color: "var(--paper)" }}>
        <header style={{ padding: "20px 32px", borderBottom: "1px solid var(--rule)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <span className="micro-label">ADJACENT · CREATOR MODE · SPONSOR</span>
            <h1 style={{ fontFamily: "var(--display)", fontSize: 28, fontWeight: 400, margin: "4px 0 0" }}>Sponsorship campaigns with <em style={{ color: "#bcb4a7" }}>receipts.</em></h1>
          </div>
          <Link href="/creator" className="intake-sample-btn" style={{ textDecoration: "none" }}>← Creator</Link>
        </header>
        <section role="status" aria-live="polite" className="evidence-panel" style={{ maxWidth: 760, margin: "48px auto", padding: 24, borderColor: guestAccess === "blocked" ? "var(--amber)" : "var(--rule)" }}>
          <strong className="mono-note">{guestAccess === "blocked" ? "GUEST WORKSPACE UNAVAILABLE" : guestAccess === "expired" ? "SESSION ENDED" : guestAccess === "checking" ? "SECURE WORKSPACE" : "WORKSPACE ERROR"}</strong>
          <p style={{ color: "#b3aea4", lineHeight: 1.7 }}>{message}</p>
          {(guestAccess === "expired" || guestAccess === "error") && <button type="button" className="intake-sample-btn" disabled={restartingGuest} onClick={() => void handleGuestRecovery()}>{restartingGuest ? "Starting…" : "Start or retry workspace"}</button>}
          <p style={{ color: "#8c877e", fontSize: 12, lineHeight: 1.6 }}>Each guest workspace is private to this browser session, expires after eight hours, and does not contain sample brands or fabricated sponsorship claims.</p>
        </section>
      </main>
    );
  }

  async function handleCreate() {
    if (!filmTitle.trim()) {
      setIntakeError("A working title is required.");
      return;
    }
    setCreating(true);
    setIntakeError(null);
    try {
      const year = filmYear.trim() ? Number(filmYear) : null;
      const themes = themesText
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean)
        .slice(0, 5);
      const result = await createSponsorCampaign({
        request_id: `spc-${Date.now()}`,
        film_title: filmTitle.trim(),
        film_year: year && Number.isFinite(year) ? year : null,
        imdb_id: imdbId.trim() || null,
        themes,
        goals: goals.trim(),
      });
      await reloadCampaigns();
      await reloadDetail(result.campaign.campaign_id);
      setFilmTitle("");
      setFilmYear("");
      setImdbId("");
      setThemesText("");
      setGoals("");
    } catch (err) {
      setIntakeError(err instanceof Error ? err.message : "Could not create the campaign.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDiscover() {
    if (!detail) return;
    setDiscovering(true);
    setDiscoveryError(null);
    setDiscoveryUnavailable(null);
    try {
      const result = await runSponsorDiscovery(detail.campaign.campaign_id, `spd-${Date.now()}`);
      void result;
      await reloadDetail(detail.campaign.campaign_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Brand discovery failed.";
      // 503/502 surface as the honest unavailable-service state.
      if (/not configured|could not complete|discovery is unavailable/i.test(message)) {
        setDiscoveryUnavailable(message);
      } else {
        setDiscoveryError(message);
      }
    } finally {
      setDiscovering(false);
    }
  }

  async function handleSaveDraft() {
    if (!detail || !draftBrand.trim()) return;
    setDraftBusy(true);
    setDraftError(null);
    try {
      await saveSponsorDraft(detail.campaign.campaign_id, {
        request_id: `spd-draft-${Date.now()}`,
        brand_name: draftBrand.trim(),
        pitch: draftPitch.trim(),
        supersedes_id: editingDraftId,
      });
      setDraftBrand("");
      setDraftPitch("");
      setEditingDraftId(null);
      await reloadDetail(detail.campaign.campaign_id);
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : "Could not save the draft.");
    } finally {
      setDraftBusy(false);
    }
  }

  function startEditDraft(draft: SponsorDraft) {
    setEditingDraftId(draft.supersedes_id === null ? draft.draft_id : draft.supersedes_id);
    setDraftBrand(draft.brand_name);
    setDraftPitch(draft.pitch);
  }

  async function handleSourceReview(draftId: string) {
    if (!detail) return;
    setReviewBusy(true);
    setReviewError(null);
    try {
      await addSponsorSourceReview(detail.campaign.campaign_id, draftId, {
        request_id: `spd-rev-${Date.now()}`,
        source_url: reviewUrl.trim(),
        claim_checked: reviewClaim.trim(),
        verification_status: reviewStatus,
        notes: reviewNotes.trim() || null,
      });
      setReviewDraftId(null);
      setReviewUrl("");
      setReviewClaim("");
      setReviewNotes("");
      await reloadDetail(detail.campaign.campaign_id);
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Could not record the review.");
    } finally {
      setReviewBusy(false);
    }
  }

  async function handleApprove(draftId: string) {
    if (!detail) return;
    setDraftError(null);
    try {
      await approveSponsorDraft(detail.campaign.campaign_id, draftId);
      await reloadDetail(detail.campaign.campaign_id);
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : "Approval refused.");
    }
  }

  async function handleOutreach() {
    if (!detail) return;
    setOutreachBusy(true);
    setOutreachError(null);
    try {
      const metrics: Record<string, number | null> = {};
      if (outreachReplies.trim() !== "") metrics.replies = Number(outreachReplies);
      if (outreachMeetings.trim() !== "") metrics.meetings = Number(outreachMeetings);
      await addSponsorOutreach(detail.campaign.campaign_id, {
        request_id: `spd-out-${Date.now()}`,
        contact_status: outreachStatus,
        measurement_status: outreachMeasurement,
        draft_id: outreachDraftId || null,
        observed_on: outreachDate || null,
        metrics,
        outcome: outreachOutcome.trim() || null,
        notes: outreachNotes.trim() || null,
      });
      setOutreachOutcome("");
      setOutreachNotes("");
      setOutreachReplies("");
      setOutreachMeetings("");
      await reloadDetail(detail.campaign.campaign_id);
    } catch (err) {
      setOutreachError(err instanceof Error ? err.message : "Could not record outreach.");
    } finally {
      setOutreachBusy(false);
    }
  }

  async function handleExport() {
    if (!detail) return;
    setExporting(true);
    setExportError(null);
    try {
      setExportPkg(await exportSponsorCampaign(detail.campaign.campaign_id));
      setCopied(false);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  const latestDiscovery: SponsorDiscovery | null =
    detail && detail.discoveries.length > 0
      ? detail.discoveries[detail.discoveries.length - 1]
      : null;
  const report = latestDiscovery?.report ?? null;

  return (
    <main style={{ background: "var(--void)", minHeight: "100vh", color: "var(--paper)" }}>
      <header
        style={{
          padding: "20px 32px",
          borderBottom: "1px solid var(--rule)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <span className="micro-label">ADJACENT · CREATOR MODE · SPONSOR</span>
          <h1 style={{ fontFamily: "var(--display)", fontSize: 28, fontWeight: 400, margin: "4px 0 0" }}>
            Sponsorship campaigns with <em style={{ color: "#bcb4a7" }}>receipts.</em>
          </h1>
        </div>
        <span style={{ display: "flex", gap: 8 }}>
          <Link href="/creator" className="intake-sample-btn" style={{ textDecoration: "none" }}>
            ← Creator
          </Link>
          <Link href="/" className="intake-sample-btn" style={{ textDecoration: "none" }}>
            Home
          </Link>
        </span>
      </header>

      <div style={{ maxWidth: 980, margin: "0 auto", padding: "40px 24px 80px" }}>
        <div className="evidence-panel" role="note" style={{ borderColor: "var(--amber)", marginBottom: 22 }}>
          <strong className="mono-note" style={{ display: "block", color: "var(--amber)" }}>
            WHAT THIS WORKFLOW DOES AND DOES NOT CLAIM
          </strong>
          <ul style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.8, margin: "10px 0 0", paddingLeft: 18 }}>
            {READING_LIMITS.map((limit) => (
              <li key={limit}>{limit}</li>
            ))}
          </ul>
        </div>

        {health?.public_demo && (
          <div className="evidence-panel" role="status" style={{ borderColor: "var(--amber)", marginBottom: 22 }}>
            <strong className="mono-note" style={{ display: "block", color: "var(--amber)" }}>
              PUBLIC DEMO MODE · SPONSORSHIP CAMPAIGNS ARE DISABLED
            </strong>
            <p style={{ color: "#b3aea4", fontSize: 12, lineHeight: 1.7, margin: "8px 0 0" }}>
              Shared campaign storage is not exposed to anonymous visitors. Run the
              backend locally as its operator to use this workflow.
            </p>
          </div>
        )}

        {/* ── Campaign intake ─────────────────────────────────────────── */}
        <div className="evidence-panel" id="intake">
          <h3>Start a campaign</h3>
          <span className="mono-note" style={{ display: "block", marginBottom: 16 }}>
            FILM IDENTITY IS RESOLVED SAFELY BEFORE ANY BRAND SIGNAL · AMBIGUOUS MATCHES ARE NEVER PROMOTED
          </span>
          <div style={{ display: "grid", gap: 12 }}>
            <label className="micro-label" style={{ display: "grid", gap: 6 }}>
              WORKING TITLE *
              <input
                className="intake-input"
                maxLength={200}
                value={filmTitle}
                onChange={(e) => setFilmTitle(e.target.value)}
                placeholder="Neon Harbour"
              />
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                YEAR (OPTIONAL)
                <input
                  className="intake-input"
                  maxLength={4}
                  inputMode="numeric"
                  value={filmYear}
                  onChange={(e) => setFilmYear(e.target.value)}
                  placeholder="2026"
                />
              </label>
              <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                IMDb ID (OPTIONAL)
                <input
                  className="intake-input"
                  maxLength={20}
                  value={imdbId}
                  onChange={(e) => setImdbId(e.target.value)}
                  placeholder="tt0000000"
                />
              </label>
            </div>
            <label className="micro-label" style={{ display: "grid", gap: 6 }}>
              THEMES (COMMA-SEPARATED, MAX 5)
              <input
                className="intake-input"
                maxLength={604}
                value={themesText}
                onChange={(e) => setThemesText(e.target.value)}
                placeholder="isolation, night workers, coastal towns"
              />
            </label>
            <label className="micro-label" style={{ display: "grid", gap: 6 }}>
              GOALS (OPTIONAL)
              <textarea
                className="intake-input"
                rows={2}
                maxLength={1000}
                value={goals}
                onChange={(e) => setGoals(e.target.value)}
                placeholder="Find brand partners for the festival premiere."
              />
            </label>
          </div>
          {intakeError && (
            <p className="intake-form-error" role="alert" style={{ marginTop: 10 }}>
              {intakeError}
            </p>
          )}
          <div className="intake-actions" style={{ marginTop: 16 }}>
            <button className="intake-submit" onClick={handleCreate} disabled={creating}>
              {creating ? "Creating…" : "Create campaign"}
            </button>
          </div>
        </div>

        {/* ── Campaign list ───────────────────────────────────────────── */}
        <div className="evidence-panel" style={{ marginTop: 22 }}>
          <h3>Your campaigns</h3>
          {campaignsLoading && <p className="mono-note">LOADING…</p>}
          {campaignsError && (
            <p className="intake-form-error" role="alert">
              {campaignsError}
            </p>
          )}
          {!campaignsLoading && !campaignsError && campaigns.length === 0 && (
            <p style={{ color: "#a7a39b", fontSize: 13, lineHeight: 1.8 }}>
              No campaigns yet. Create one above — nothing is sent anywhere until you
              run discovery yourself.
            </p>
          )}
          {campaigns.map((campaign) => (
            <button
              key={campaign.campaign_id}
              className="intake-sample-btn"
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                marginBottom: 8,
                borderColor:
                  detail?.campaign.campaign_id === campaign.campaign_id ? "var(--amber)" : undefined,
              }}
              onClick={() => {
                setExportPkg(null);
                setDiscoveryUnavailable(null);
                setDiscoveryError(null);
                void reloadDetail(campaign.campaign_id);
              }}
            >
              <strong>{campaign.film_title}</strong>
              {campaign.film_year ? ` (${campaign.film_year})` : ""}
              <span className="mono-note" style={{ display: "block", marginTop: 4 }}>
                {campaign.discovery_count ?? 0} DISCOVERIES · {campaign.draft_count ?? 0} DRAFTS ·{" "}
                {campaign.outreach_count ?? 0} OUTREACH RECORDS
              </span>
            </button>
          ))}
        </div>

        {/* ── Selected campaign ───────────────────────────────────────── */}
        {detail && (
          <div style={{ marginTop: 22, display: "grid", gap: 22 }}>
            {detailLoading && <p className="mono-note">LOADING CAMPAIGN…</p>}
            {detailError && (
              <p className="intake-form-error" role="alert">
                {detailError}
              </p>
            )}

            {/* Discovery */}
            <div className="evidence-panel" id="discovery">
              <h3>Brand discovery · {detail.campaign.film_title}</h3>
              <span className="mono-note" style={{ display: "block", marginBottom: 12 }}>
                LIVE QLOO ONLY · NO KEY MEANS AN HONEST UNAVAILABLE STATE, NEVER FIXTURE BRANDS
              </span>
              <button className="intake-submit" onClick={handleDiscover} disabled={discovering}>
                {discovering
                  ? "Discovering (live Qloo)…"
                  : latestDiscovery
                    ? "Run discovery again"
                    : "Run live brand discovery"}
              </button>
              {discoveryUnavailable && (
                <div
                  className="insufficient-panel"
                  role="status"
                  style={{ marginTop: 14 }}
                >
                  <h3>Live brand discovery is unavailable</h3>
                  <p>{discoveryUnavailable}</p>
                </div>
              )}
              {discoveryError && (
                <p className="intake-form-error" role="alert" style={{ marginTop: 10 }}>
                  {discoveryError}
                </p>
              )}

              {report && (
                <div style={{ marginTop: 16, display: "grid", gap: 14 }}>
                  <span className="mono-note">
                    MEASURED QLOO DATA · SAVED {latestDiscovery?.created_at?.slice(0, 10)} ·{" "}
                    {report.call_ids?.length ?? 0} CALLS
                  </span>

                  {/* Film identity resolution — ambiguous/mismatch preserved */}
                  {Array.isArray(report.films) && report.films.length > 0 && (
                    <div>
                      <span className="micro-label">FILM IDENTITY RESOLUTION</span>
                      {report.films.map((film: SponsorFilmResolution) => (
                        <div
                          key={film.input_title}
                          style={{
                            display: "flex",
                            gap: 10,
                            alignItems: "baseline",
                            flexWrap: "wrap",
                            marginTop: 6,
                            fontSize: 12,
                          }}
                        >
                          <strong>{film.input_title}</strong>
                          <span
                            className="mono-note"
                            style={{
                              color: matchTone(film.match_status).color,
                              border: `1px solid ${matchTone(film.match_status).border}`,
                              padding: "1px 8px",
                            }}
                          >
                            {film.match_status}
                          </span>
                          <span style={{ color: "#a7a39b" }}>
                            {film.usable && film.candidate
                              ? `→ ${film.candidate.name}${film.candidate.year ? ` (${film.candidate.year})` : ""}`
                              : film.match_status === "AMBIGUOUS"
                                ? "kept unusable — multiple candidates; nothing was promoted"
                                : "kept unusable — no verified match"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Brand candidates with per-query observations */}
                  <div>
                    <span className="micro-label">BRAND CANDIDATES (HUMAN REVIEW ONLY)</span>
                    {Array.isArray(report.brands) && report.brands.length > 0 ? (
                      <div style={{ display: "grid", gap: 10, marginTop: 8 }}>
                        {report.brands.map((brand: SponsorBrand) => (
                          <div
                            key={brand.entity_id ?? brand.name}
                            style={{
                              border: "1px solid var(--rule)",
                              padding: "10px 12px",
                              display: "grid",
                              gap: 6,
                            }}
                          >
                            <strong style={{ fontSize: 13 }}>{brand.name}</strong>
                            {brand.observations.map((observation, index) => (
                              <span key={`${brand.entity_id}-${index}`} className="mono-note">
                                {observation.source.toUpperCase()} · AFFINITY{" "}
                                {affinityLabel(observation.affinity)}
                                {observation.band ? ` · ${String(observation.band).toUpperCase()}` : ""}
                                {observation.call_id ? ` · CALL ${observation.call_id}` : ""}
                              </span>
                            ))}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ color: "#a7a39b", fontSize: 12, marginTop: 6 }}>
                        No typed brand candidates were returned. That is a finding, not an
                        error — nothing has been filled in.
                      </p>
                    )}
                  </div>

                  {/* Non-brand results kept visible */}
                  {Array.isArray(report.non_brand_results) && report.non_brand_results.length > 0 && (
                    <div>
                      <span className="micro-label">RETURNED BUT NOT BRAND-TYPED</span>
                      {report.non_brand_results.map((row) => (
                        <p key={`${row.entity_id}-${row.reason_code}`} className="mono-note" style={{ marginTop: 4 }}>
                          {row.name ?? row.entity_id} · {row.reason_code.toUpperCase()}
                        </p>
                      ))}
                    </div>
                  )}

                  {/* Interpretation limits */}
                  <div>
                    <span className="micro-label">INTERPRETATION LIMITS</span>
                    <ul
                      style={{
                        color: "#b3aea4",
                        fontSize: 12,
                        lineHeight: 1.8,
                        margin: "6px 0 0",
                        paddingLeft: 18,
                      }}
                    >
                      {(report.interpretation_limits ?? []).map((limit) => (
                        <li key={limit}>{limit}</li>
                      ))}
                    </ul>
                  </div>

                  {report.halt_reason ? (
                    <p className="mono-note" style={{ color: "#c97a6a" }}>
                      DISCOVERY STOPPED EARLY:{" "}
                      {String((report.halt_reason as Record<string, unknown>).error_type ?? "provider error")}
                    </p>
                  ) : null}
                </div>
              )}
            </div>

            {/* Drafts + source review + approval */}
            <div className="evidence-panel" id="drafts">
              <h3>Sponsorship drafts</h3>
              <span className="mono-note" style={{ display: "block", marginBottom: 12 }}>
                EDITING CREATES A NEW VERSION · APPROVAL REQUIRES AN OFFICIAL-SOURCE REVIEW ·
                EXPORT INCLUDES APPROVED VERSIONS ONLY
              </span>
              <div style={{ display: "grid", gap: 10 }}>
                <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                  BRAND NAME
                  <input
                    className="intake-input"
                    maxLength={200}
                    value={draftBrand}
                    onChange={(e) => setDraftBrand(e.target.value)}
                    placeholder="Brand One"
                  />
                </label>
                <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                  PITCH (YOUR WORDS — NOT AUTO-GENERATED)
                  <textarea
                    className="intake-input"
                    rows={3}
                    maxLength={4000}
                    value={draftPitch}
                    onChange={(e) => setDraftPitch(e.target.value)}
                    placeholder="What you would send, and why this film fits their audience."
                  />
                </label>
                {draftError && (
                  <p className="intake-form-error" role="alert">
                    {draftError}
                  </p>
                )}
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    className="intake-submit"
                    onClick={handleSaveDraft}
                    disabled={draftBusy || !draftBrand.trim()}
                  >
                    {draftBusy
                      ? "Saving…"
                      : editingDraftId
                        ? "Save as new version"
                        : "Save draft"}
                  </button>
                  {editingDraftId && (
                    <button
                      className="intake-sample-btn"
                      onClick={() => {
                        setEditingDraftId(null);
                        setDraftBrand("");
                        setDraftPitch("");
                      }}
                    >
                      Cancel edit
                    </button>
                  )}
                </div>
              </div>

              <div style={{ marginTop: 18, display: "grid", gap: 12 }}>
                {detail.drafts.length === 0 && (
                  <p style={{ color: "#a7a39b", fontSize: 12 }}>
                    No drafts yet. Drafts are your words; Adjacent never writes outreach copy
                    for you.
                  </p>
                )}
                {detail.drafts.map((draft) => {
                  const reviews = detail.source_reviews.filter((r) => r.draft_id === draft.draft_id);
                  return (
                    <div
                      key={draft.draft_id}
                      style={{ border: "1px solid var(--rule)", padding: "12px 14px", display: "grid", gap: 8 }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                        <strong style={{ fontSize: 13 }}>
                          {draft.brand_name}{" "}
                          <span className="mono-note">V{draft.version}</span>
                        </strong>
                        <span
                          className="mono-note"
                          style={{
                            color: draft.status === "APPROVED" ? "#7aba8a" : "#c29a6e",
                            border: `1px solid ${draft.status === "APPROVED" ? "rgba(62,122,76,0.4)" : "rgba(194,154,110,0.4)"}`,
                            padding: "1px 8px",
                          }}
                        >
                          {draft.status}
                          {draft.approved_at ? ` · ${draft.approved_at.slice(0, 10)}` : ""}
                        </span>
                      </div>
                      <p style={{ color: "#c9c2b6", fontSize: 12, lineHeight: 1.7, margin: 0, whiteSpace: "pre-wrap" }}>
                        {draft.pitch || <em style={{ color: "#6b6964" }}>No pitch text.</em>}
                      </p>
                      {reviews.length > 0 && (
                        <div>
                          <span className="micro-label">SOURCE REVIEWS (CREATOR-RECORDED)</span>
                          {reviews.map((review) => (
                            <p key={review.review_id} className="mono-note" style={{ marginTop: 4 }}>
                              {review.verification_status} · {review.claim_checked || "claim not stated"}
                              {review.source_url ? ` · ${review.source_url}` : ""}
                            </p>
                          ))}
                        </div>
                      )}
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <button className="intake-sample-btn" onClick={() => startEditDraft(draft)}>
                          Edit (new version)
                        </button>
                        <button
                          className="intake-sample-btn"
                          onClick={() => setReviewDraftId(reviewDraftId === draft.draft_id ? null : draft.draft_id)}
                        >
                          {reviewDraftId === draft.draft_id ? "Close review form" : "Add source review"}
                        </button>
                        {draft.status !== "APPROVED" && (
                          <button
                            className="intake-sample-btn"
                            onClick={() => handleApprove(draft.draft_id)}
                          >
                            Approve
                          </button>
                        )}
                      </div>
                      {reviewDraftId === draft.draft_id && (
                        <div style={{ display: "grid", gap: 8, borderTop: "1px solid var(--rule)", paddingTop: 10 }}>
                          <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                            OFFICIAL SOURCE URL
                            <input
                              className="intake-input"
                              maxLength={2000}
                              value={reviewUrl}
                              onChange={(e) => setReviewUrl(e.target.value)}
                              placeholder="https://…"
                            />
                          </label>
                          <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                            COMMERCIAL CLAIM YOU CHECKED
                            <input
                              className="intake-input"
                              maxLength={1000}
                              value={reviewClaim}
                              onChange={(e) => setReviewClaim(e.target.value)}
                              placeholder="Brand runs an open filmmaker sponsorship programme."
                            />
                          </label>
                          <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                            YOUR VERIFICATION
                            <select
                              className="intake-input"
                              value={reviewStatus}
                              onChange={(e) => setReviewStatus(e.target.value)}
                            >
                              <option value="SUPPORTED_BY_OFFICIAL_SOURCE">Supported by official source</option>
                              <option value="CONTRADICTED">Contradicted</option>
                              <option value="UNVERIFIED">Unverified</option>
                            </select>
                          </label>
                          <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                            NOTES (OPTIONAL)
                            <input
                              className="intake-input"
                              maxLength={2000}
                              value={reviewNotes}
                              onChange={(e) => setReviewNotes(e.target.value)}
                            />
                          </label>
                          {reviewError && (
                            <p className="intake-form-error" role="alert">
                              {reviewError}
                            </p>
                          )}
                          <button
                            className="intake-submit"
                            onClick={() => handleSourceReview(draft.draft_id)}
                            disabled={reviewBusy}
                          >
                            {reviewBusy ? "Recording…" : "Record review"}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Outreach tracking */}
            <div className="evidence-panel" id="outreach">
              <h3>Outreach & actual outcomes</h3>
              <span className="mono-note" style={{ display: "block", marginBottom: 12 }}>
                MANUAL RECORDING ONLY · AN OBSERVED ZERO IS STORED AS 0 · AN UNRECORDED VALUE IS MISSING, NOT ZERO
              </span>
              <div style={{ display: "grid", gap: 10 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                    CONTACT STATUS
                    <select
                      className="intake-input"
                      value={outreachStatus}
                      onChange={(e) => setOutreachStatus(e.target.value)}
                    >
                      <option value="CONTACTED">Contacted</option>
                      <option value="RESPONDED">Responded</option>
                      <option value="PASSED">Passed</option>
                      <option value="DECLINED">Declined</option>
                      <option value="COLLABORATED">Collaborated</option>
                    </select>
                  </label>
                  <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                    MEASUREMENT STATUS
                    <select
                      className="intake-input"
                      value={outreachMeasurement}
                      onChange={(e) => setOutreachMeasurement(e.target.value)}
                    >
                      <option value="OBSERVED">Observed</option>
                      <option value="PARTIAL">Partial</option>
                      <option value="MISSING">Missing</option>
                      <option value="UNAVAILABLE">Unavailable</option>
                      <option value="FAILED">Failed</option>
                    </select>
                  </label>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                    DRAFT (OPTIONAL)
                    <select
                      className="intake-input"
                      value={outreachDraftId}
                      onChange={(e) => setOutreachDraftId(e.target.value)}
                    >
                      <option value="">— none —</option>
                      {detail.drafts.map((draft) => (
                        <option key={draft.draft_id} value={draft.draft_id}>
                          {draft.brand_name} v{draft.version}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                    OBSERVED ON (OPTIONAL)
                    <input
                      className="intake-input"
                      maxLength={32}
                      value={outreachDate}
                      onChange={(e) => setOutreachDate(e.target.value)}
                      placeholder="2026-10-20"
                    />
                  </label>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                    REPLIES (BLANK = NOT RECORDED)
                    <input
                      className="intake-input"
                      inputMode="numeric"
                      value={outreachReplies}
                      onChange={(e) => setOutreachReplies(e.target.value)}
                      placeholder="0"
                    />
                  </label>
                  <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                    MEETINGS (BLANK = NOT RECORDED)
                    <input
                      className="intake-input"
                      inputMode="numeric"
                      value={outreachMeetings}
                      onChange={(e) => setOutreachMeetings(e.target.value)}
                      placeholder="0"
                    />
                  </label>
                </div>
                <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                  OUTCOME (WHAT ACTUALLY HAPPENED)
                  <textarea
                    className="intake-input"
                    rows={2}
                    maxLength={2000}
                    value={outreachOutcome}
                    onChange={(e) => setOutreachOutcome(e.target.value)}
                  />
                </label>
                <label className="micro-label" style={{ display: "grid", gap: 6 }}>
                  NOTES (OPTIONAL)
                  <input
                    className="intake-input"
                    maxLength={2000}
                    value={outreachNotes}
                    onChange={(e) => setOutreachNotes(e.target.value)}
                  />
                </label>
                {outreachError && (
                  <p className="intake-form-error" role="alert">
                    {outreachError}
                  </p>
                )}
                <button className="intake-submit" onClick={handleOutreach} disabled={outreachBusy}>
                  {outreachBusy ? "Recording…" : "Record outreach"}
                </button>
              </div>

              <div style={{ marginTop: 16, display: "grid", gap: 8 }}>
                {detail.outreach.length === 0 && (
                  <p style={{ color: "#a7a39b", fontSize: 12 }}>
                    No outreach recorded yet. Outcomes appear here exactly as you record
                    them.
                  </p>
                )}
                {detail.outreach.map((record: SponsorOutreachRecord) => (
                  <div key={record.outreach_id} style={{ borderTop: "1px solid var(--rule)", paddingTop: 8 }}>
                    <span className="mono-note">
                      {record.contact_status} · {record.measurement_status}
                      {record.observed_on ? ` · ${record.observed_on}` : ""}
                      {Object.prototype.hasOwnProperty.call(record.metrics, "replies")
                        ? ` · REPLIES ${record.metrics.replies}`
                        : " · REPLIES NOT RECORDED"}
                      {Object.prototype.hasOwnProperty.call(record.metrics, "meetings")
                        ? ` · MEETINGS ${record.metrics.meetings}`
                        : " · MEETINGS NOT RECORDED"}
                    </span>
                    {record.outcome && (
                      <p style={{ color: "#c9c2b6", fontSize: 12, margin: "4px 0 0" }}>{record.outcome}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Export — approved only */}
            <div className="evidence-panel" id="export">
              <h3>Export</h3>
              <span className="mono-note" style={{ display: "block", marginBottom: 12 }}>
                APPROVED DRAFTS ONLY · UNAPPROVED WORK IS EXCLUDED WITH ITS REASON
              </span>
              <button className="intake-submit" onClick={handleExport} disabled={exporting}>
                {exporting ? "Preparing…" : "Prepare export package"}
              </button>
              {exportError && (
                <p className="intake-form-error" role="alert" style={{ marginTop: 10 }}>
                  {exportError}
                </p>
              )}
              {exportPkg && (
                <div style={{ marginTop: 14, display: "grid", gap: 10 }}>
                  <span className="mono-note">
                    {exportPkg.export_ready
                      ? `${exportPkg.approved_drafts.length} APPROVED DRAFT(S) READY`
                      : "NOTHING APPROVED YET — EXPORT IS EMPTY BY DESIGN"}
                  </span>
                  {exportPkg.excluded_drafts.map((excluded) => (
                    <p key={excluded.draft_id} className="mono-note" style={{ color: "#c29a6e" }}>
                      EXCLUDED · {excluded.brand_name} · {excluded.reason.toUpperCase()}
                    </p>
                  ))}
                  <div>
                    <span className="micro-label">INTERPRETATION LIMITS ATTACHED TO THE EXPORT</span>
                    <ul
                      style={{
                        color: "#b3aea4",
                        fontSize: 12,
                        lineHeight: 1.8,
                        margin: "6px 0 0",
                        paddingLeft: 18,
                      }}
                    >
                      {exportPkg.interpretation_limits.map((limit) => (
                        <li key={limit}>{limit}</li>
                      ))}
                    </ul>
                  </div>
                  <button
                    className="intake-sample-btn"
                    onClick={() => {
                      void navigator.clipboard
                        .writeText(JSON.stringify(exportPkg, null, 2))
                        .then(() => setCopied(true));
                    }}
                  >
                    {copied ? "Copied to clipboard" : "Copy package as JSON"}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
