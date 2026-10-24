"use client";

// FilmSponsor — Creator Mode sponsorship workflow.
//
// Composition ported from the source ZIP (`src/pages/Sponsor.tsx`): a
// photographic masthead, an eight-stage campaign railway, and a dossier aside.
//
// The workflow itself is this application's existing, tested one, bound to the
// real `/filmsponsor/*` API: campaign intake → live brand discovery → evidence
// inspection → creator-written drafts → official-source review → approval →
// approval-gated export → manually recorded outreach. Brand candidates and
// affinity values appear ONLY from a measured discovery report; without the
// provider key discovery reports its honest unavailable state. Nothing on this
// page fabricates brands, affinity values, reviews or outcomes.

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, Check, Clipboard, Download, Plus, Trash2 } from "lucide-react";
import {
  addSponsorOutreach,
  addSponsorSourceReview,
  approveSponsorDraft,
  createSponsorCampaign,
  exportSponsorCampaign,
  getHealth,
  getSponsorCampaign,
  initializeSponsorGuestSession,
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
import { photos } from "@/lib/photos";
import { PhotoFrame } from "@/components/nf/PhotoFrame";
import { Field, TextArea, TextInput } from "@/components/nf/Field";
import { DataChip } from "@/components/nf/Chips";
import { cn } from "@/lib/cn";

const STEPS = [
  "Intake",
  "Discovery",
  "Evidence",
  "Draft",
  "Review",
  "Approval",
  "Export",
  "Outreach",
] as const;

type Step = (typeof STEPS)[number];

const READING_LIMITS = [
  "Cultural affinity is not sponsorship likelihood, eligibility, budget, availability, or ROI.",
  "Brand candidates are for human relevance review only; no outreach or contact discovery is performed.",
  "Affinity values are per-query normalised; values from different queries are not comparable.",
  "Only entities with explicit brand-type evidence are presented as brands.",
];

/** Zero is an observed value; a missing score is never rendered as zero. */
function affinityLabel(affinity: number | null): string {
  return affinity === null ? "no score" : affinity.toFixed(2);
}

function matchTone(status: string) {
  if (status === "VERIFIED") return "text-sage border-sage/40";
  if (status === "AMBIGUOUS") return "text-amber border-amber/40";
  return "text-blood border-blood/40";
}

export default function SponsorPage() {
  const [step, setStep] = useState<Step>("Intake");

  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [guestAccess, setGuestAccess] = useState<
    "checking" | "ready" | "blocked" | "expired" | "error"
  >("checking");
  const [guestAccessError, setGuestAccessError] = useState<string | null>(null);
  const [restartingGuest, setRestartingGuest] = useState(false);
  const workspaceInitializationRequest = useRef(0);

  const [campaigns, setCampaigns] = useState<SponsorCampaign[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(true);
  const [campaignsError, setCampaignsError] = useState<string | null>(null);

  // Intake
  const [filmTitle, setFilmTitle] = useState("");
  const [filmYear, setFilmYear] = useState("");
  const [imdbId, setImdbId] = useState("");
  const [themesText, setThemesText] = useState("");
  const [goals, setGoals] = useState("");
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const createRequest = useRef<{ signature: string; requestId: string } | null>(null);

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

  // Source review
  const [reviewDraftId, setReviewDraftId] = useState<string | null>(null);
  const [reviewUrl, setReviewUrl] = useState("");
  const [reviewClaim, setReviewClaim] = useState("");
  const [reviewStatus, setReviewStatus] = useState("SUPPORTED_BY_OFFICIAL_SOURCE");
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  // Approvals
  const [approvalBusy, setApprovalBusy] = useState<string | null>(null);
  const [approvalError, setApprovalError] = useState<string | null>(null);

  // Outreach
  const [outreachStatus, setOutreachStatus] = useState("");
  const [outreachMeasurement, setOutreachMeasurement] = useState("");
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
    } catch (err) {
      setCampaignsError(err instanceof Error ? err.message : "Could not load campaigns.");
    } finally {
      setCampaignsLoading(false);
    }
  }, []);

  const startGuestWorkspace = useCallback(async () => {
    const requestId = ++workspaceInitializationRequest.current;
    setGuestAccess("checking");
    setGuestAccessError(null);
    setCampaignsLoading(true);
    try {
      const backend = await getHealth();
      if (requestId !== workspaceInitializationRequest.current) return;
      setHealth(backend);
      if (backend.public_demo && !backend.filmsponsor_guest_enabled) {
        setGuestAccess("blocked");
        setCampaignsLoading(false);
        return;
      }
      if (backend.filmsponsor_guest_enabled) {
        await initializeSponsorGuestSession();
        if (requestId !== workspaceInitializationRequest.current) return;
      }
      setGuestAccess("ready");
      void reloadCampaigns();
    } catch (err) {
      if (requestId !== workspaceInitializationRequest.current) return;
      setGuestAccess("error");
      setGuestAccessError(err instanceof Error ? err.message : "Guest workspace is unavailable.");
      setCampaignsLoading(false);
    }
  }, [reloadCampaigns]);

  useEffect(() => {
    void startGuestWorkspace();
    const expired = () => setGuestAccess("expired");
    window.addEventListener("filmsponsor-session-expired", expired);
    return () => {
      workspaceInitializationRequest.current += 1;
      window.removeEventListener("filmsponsor-session-expired", expired);
    };
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
        .map((theme) => theme.trim())
        .filter(Boolean)
        .slice(0, 5);
      const payload = {
        film_title: filmTitle.trim(),
        film_year: year && Number.isFinite(year) ? year : null,
        imdb_id: imdbId.trim() || null,
        themes,
        goals: goals.trim(),
      };
      const signature = JSON.stringify(payload);
      if (!createRequest.current || createRequest.current.signature !== signature) {
        createRequest.current = { signature, requestId: `spc-${crypto.randomUUID()}` };
      }
      const result = await createSponsorCampaign({
        request_id: createRequest.current.requestId,
        ...payload,
      });
      createRequest.current = null;
      setFilmTitle("");
      setFilmYear("");
      setImdbId("");
      setThemesText("");
      setGoals("");
      await reloadCampaigns();
      await reloadDetail(result.campaign.campaign_id);
      setStep("Discovery");
    } catch (err) {
      setIntakeError(err instanceof Error ? err.message : "Could not create the campaign.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDiscover() {
    if (!detail) return;
    setStep("Discovery");
    setDiscovering(true);
    setDiscoveryError(null);
    setDiscoveryUnavailable(null);
    try {
      await runSponsorDiscovery(detail.campaign.campaign_id, `spd-${Date.now()}`);
      await reloadDetail(detail.campaign.campaign_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Brand discovery failed.";
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
    setStep("Draft");
  }

  function openReview(draftId: string) {
    setReviewDraftId(reviewDraftId === draftId ? null : draftId);
    setReviewError(null);
    setStep("Review");
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
      setStep("Approval");
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Could not record the review.");
    } finally {
      setReviewBusy(false);
    }
  }

  async function handleApprove(draftId: string) {
    if (!detail) return;
    setApprovalBusy(draftId);
    setApprovalError(null);
    try {
      await approveSponsorDraft(detail.campaign.campaign_id, draftId);
      await reloadDetail(detail.campaign.campaign_id);
    } catch (err) {
      setApprovalError(err instanceof Error ? err.message : "Approval refused.");
    } finally {
      setApprovalBusy(null);
    }
  }

  async function handleOutreach() {
    if (!detail) return;
    if (!outreachStatus || !outreachMeasurement) {
      setOutreachError("Choose the contact and measurement statuses that match what actually happened.");
      return;
    }
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
      setOutreachStatus("");
      setOutreachMeasurement("");
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
    setExportPkg(null);
    setExportError(null);
    setCopied(false);
    setExporting(true);
    try {
      setExportPkg(await exportSponsorCampaign(detail.campaign.campaign_id));
      setStep("Export");
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  function downloadExport() {
    if (!exportPkg) return;
    const lines = [
      "ADJACENT CINEMA — FILMSPONSOR EXPORT",
      `film: ${exportPkg.campaign.film_title}${exportPkg.campaign.film_year ? ` (${exportPkg.campaign.film_year})` : ""}`,
      `campaign: ${exportPkg.campaign.campaign_id}`,
      "",
      ...exportPkg.approved_drafts.flatMap((draft) => [
        `DRAFT v${draft.version} · ${draft.brand_name} · approved ${draft.approved_at?.slice(0, 10) ?? "—"}`,
        draft.pitch,
        ...draft.source_reviews.map(
          (review) =>
            `  SOURCE REVIEW · ${review.verification_status} · ${review.claim_checked || "claim not stated"}${review.source_url ? ` · ${review.source_url}` : ""}`,
        ),
        "",
      ]),
      ...exportPkg.excluded_drafts.map(
        (excluded) => `EXCLUDED · ${excluded.brand_name} · ${excluded.reason}`,
      ),
      "",
      "INTERPRETATION LIMITS",
      ...exportPkg.interpretation_limits.map((limit) => `- ${limit}`),
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `filmsponsor-${exportPkg.campaign.campaign_id}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const latestDiscovery: SponsorDiscovery | null =
    detail && detail.discoveries.length > 0 ? detail.discoveries[detail.discoveries.length - 1] : null;
  const report = latestDiscovery?.report ?? null;
  const approvedCount = detail?.drafts.filter((draft) => draft.status === "APPROVED").length ?? 0;
  const reviewCount = detail?.source_reviews.length ?? 0;

  function stepState(current: Step): "unavailable" | "locked" | "ready" | null {
    if (current === "Discovery" && discoveryUnavailable) return "unavailable";
    if (current === "Evidence" && !report) return "locked";
    if (current === "Draft" && !detail) return "locked";
    if (current === "Review" && (detail?.drafts.length ?? 0) === 0) return "locked";
    if (current === "Approval") {
      if (!detail || detail.drafts.length === 0) return "locked";
      return approvedCount > 0 ? "ready" : null;
    }
    if (current === "Export" && approvedCount === 0) return "locked";
    if (current === "Outreach" && !detail) return "locked";
    return null;
  }

  if (guestAccess !== "ready") {
    const message =
      guestAccess === "checking"
        ? "Initializing an isolated workspace…"
        : guestAccess === "blocked"
          ? "This public demo has not enabled isolated FilmSponsor guest workspaces. Shared campaigns remain protected."
          : guestAccess === "expired"
            ? "This guest workspace expired or was revoked. Start a new isolated workspace to continue."
            : guestAccessError || "FilmSponsor could not initialize. Please retry.";
    return (
      <div className="mx-auto max-w-[1440px] px-4 py-20 md:px-8">
        <p className="type-kicker">Creator Studio · FilmSponsor</p>
        <h1 className="font-display mt-3 max-w-[20ch] text-4xl leading-[0.95] md:text-6xl">
          Sponsorship campaigns with <span className="italic text-amber">receipts.</span>
        </h1>
        <div
          role="status"
          aria-live="polite"
          className="mt-8 max-w-2xl border border-line p-6"
        >
          <p className="chip chip-warn">
            {guestAccess === "blocked"
              ? "GUEST WORKSPACE UNAVAILABLE"
              : guestAccess === "expired"
                ? "SESSION ENDED"
                : guestAccess === "checking"
                  ? "SECURE WORKSPACE"
                  : "WORKSPACE ERROR"}
          </p>
          <p className="mt-4 text-sm leading-relaxed text-paper-2">{message}</p>
          {(guestAccess === "expired" || guestAccess === "error") && (
            <button
              type="button"
              className="btn-ghost mt-4"
              disabled={restartingGuest}
              onClick={() => void handleGuestRecovery()}
            >
              {restartingGuest ? "Starting…" : "Start or retry workspace"}
            </button>
          )}
          <p className="caption mt-4">
            Each guest workspace is private to this browser session, expires after eight hours, and
            contains no sample brands or fabricated sponsorship claims.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <section className="relative overflow-hidden border-b border-line">
        <div className="absolute inset-0 opacity-40">
          <PhotoFrame photo={photos.writing} className="h-full min-h-[320px]" credit={false} />
        </div>
        <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/85 to-ink/40" />
        <div className="relative mx-auto max-w-[1440px] px-4 py-16 md:px-8 md:py-24">
          <p className="type-kicker">FilmSponsor</p>
          <h1 className="font-display mt-3 max-w-[18ch] text-5xl leading-[0.92] md:text-7xl">
            A campaign dossier, not a CRM.
          </h1>
          <p className="mt-5 max-w-lg text-sm leading-relaxed text-paper-2">
            Intake, live discovery when configured, drafts, source review, approval, export, and
            manually recorded outreach. Brand affinity is not sponsorship likelihood.
          </p>
        </div>
      </section>

      <nav aria-label="Campaign stages" className="sticky top-[64px] z-40 border-b border-line bg-ink/95 backdrop-blur">
        <ol className="mx-auto flex max-w-[1440px] gap-0 overflow-x-auto px-2 md:px-8">
          {STEPS.map((current, index) => {
            const state = stepState(current);
            return (
              <li key={current} className="min-w-[7rem] flex-1">
                <button
                  type="button"
                  onClick={() => setStep(current)}
                  aria-current={step === current ? "step" : undefined}
                  className={cn(
                    "flex w-full flex-col border-b-2 px-2 py-3 text-left transition-colors",
                    step === current ? "border-amber" : "border-transparent hover:border-line-strong",
                  )}
                >
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="font-mono text-[0.58rem] tracking-[0.16em] text-amber">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    {state && (
                      <span
                        className={cn(
                          "font-mono text-[0.5rem] uppercase tracking-[0.1em]",
                          state === "unavailable" && "text-warn",
                          state === "locked" && "text-dim",
                          state === "ready" && "text-sage",
                        )}
                      >
                        {state}
                      </span>
                    )}
                  </span>
                  <span className={cn("text-sm", step === current ? "text-paper" : "text-mute")}>
                    {current}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      {health?.public_demo && (
        <div className="border-b border-amber/30 bg-amber/10">
          <p className="mx-auto max-w-[1440px] px-4 py-3 text-sm text-amber md:px-8">
            PUBLIC DEMO · isolated guest workspaces only. Shared campaign storage is not exposed to
            anonymous visitors, and nothing here is a predicted sponsorship outcome.
          </p>
        </div>
      )}

      <div className="mx-auto grid max-w-[1440px] gap-10 px-4 py-12 md:grid-cols-12 md:px-8">
        <div className="md:col-span-8">
          {step === "Intake" && (
            <div className="space-y-8">
              <div>
                <h2 className="font-display text-4xl">Campaign intake</h2>
                <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                  Film identity is resolved safely before any brand signal; ambiguous matches are
                  never promoted. Nothing is sent anywhere until you run discovery yourself.
                </p>
              </div>
              <div className="border border-line p-5 md:p-6">
                <div className="space-y-6">
                  <Field label="Working title *">
                    <TextInput
                      maxLength={200}
                      value={filmTitle}
                      onChange={(event) => setFilmTitle(event.target.value)}
                      placeholder="Neon Harbour"
                    />
                  </Field>
                  <div className="grid gap-6 sm:grid-cols-2">
                    <Field label="Year (optional)">
                      <TextInput
                        maxLength={4}
                        inputMode="numeric"
                        value={filmYear}
                        onChange={(event) => setFilmYear(event.target.value)}
                        placeholder="2026"
                      />
                    </Field>
                    <Field label="IMDb ID (optional)">
                      <TextInput
                        maxLength={20}
                        value={imdbId}
                        onChange={(event) => setImdbId(event.target.value)}
                        placeholder="tt0000000"
                      />
                    </Field>
                  </div>
                  <Field label="Themes" hint="Comma-separated, maximum five.">
                    <TextInput
                      maxLength={604}
                      value={themesText}
                      onChange={(event) => setThemesText(event.target.value)}
                      placeholder="isolation, night workers, coastal towns"
                    />
                  </Field>
                  <Field label="Goals (optional)">
                    <TextArea
                      maxLength={1000}
                      value={goals}
                      onChange={(event) => setGoals(event.target.value)}
                      placeholder="Find brand partners for the festival premiere."
                    />
                  </Field>
                </div>
                {intakeError && (
                  <p role="alert" className="mt-4 text-sm text-warn">
                    {intakeError}
                  </p>
                )}
                <button
                  type="button"
                  className="btn-primary mt-6"
                  onClick={() => void handleCreate()}
                  disabled={creating}
                >
                  {creating ? "Creating…" : "Create campaign"}
                  <ArrowRight size={16} />
                </button>
              </div>
              <p className="caption max-w-2xl">
                A campaign is a private dossier of your own records. It is not a mailing list, an
                eligibility check, or a sponsorship forecast.
              </p>
            </div>
          )}

          {step === "Discovery" && (
            <div>
              <h2 className="font-display text-4xl">Brand discovery</h2>
              <p className="mt-4 max-w-xl text-sm leading-relaxed text-mute">
                Discovery runs only against live Qloo when the backend has a provider key. This
                workspace will not invent brands, affinity scores, or eligibility.
              </p>
              {!detail ? (
                <Locked
                  title="Select or create a campaign first."
                  body="Discovery is a recorded call against one campaign. Without a campaign there is nothing to discover."
                  action="Go to intake"
                  onAction={() => setStep("Intake")}
                />
              ) : (
                <>
                  <p className="mt-6 text-sm text-paper-2">
                    Campaign · {detail.campaign.film_title}
                    {detail.campaign.film_year ? ` (${detail.campaign.film_year})` : ""}
                  </p>
                  <button
                    type="button"
                    className="btn-primary mt-6"
                    onClick={() => void handleDiscover()}
                    disabled={discovering}
                  >
                    {discovering
                      ? "Discovering (live Qloo)…"
                      : latestDiscovery
                        ? "Run discovery again"
                        : "Request live discovery"}
                    <ArrowRight size={16} />
                  </button>

                  {latestDiscovery && (
                    <div className="mt-6 flex flex-wrap items-center gap-3">
                      <DataChip status={latestDiscovery.data_status} />
                      <span className="caption">
                        Discovery {latestDiscovery.discovery_id} · saved{" "}
                        {latestDiscovery.created_at.slice(0, 10)} ·{" "}
                        {report?.call_ids?.length ?? 0} Qloo call(s)
                      </span>
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => setStep("Evidence")}
                      >
                        Inspect evidence
                      </button>
                    </div>
                  )}

                  {discoveryUnavailable && (
                    <div role="status" className="mt-8 border border-line p-6">
                      <p className="chip chip-warn">Unavailable</p>
                      <h3 className="font-display mt-4 text-3xl">No brands were substituted.</h3>
                      <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                        {discoveryUnavailable} Without a provider key the discover route must remain
                        empty. You may still write a draft from your own knowledge, then record an
                        official-source review before approval.
                      </p>
                    </div>
                  )}
                  {discoveryError && (
                    <p role="alert" className="mt-4 text-sm text-warn">
                      {discoveryError}
                    </p>
                  )}
                </>
              )}
            </div>
          )}

          {step === "Evidence" && (
            <div>
              <h2 className="font-display text-4xl">Evidence inspection</h2>
              <p className="mt-4 max-w-xl text-sm leading-relaxed text-mute">
                Brand affinity, when present, is a cultural-similarity signal. It is not sponsorship
                likelihood, budget, availability or ROI.
              </p>
              {report ? (
                <div className="mt-8 grid gap-8">
                  {latestDiscovery && (
                    <div className="flex flex-wrap items-center gap-3">
                      <DataChip status={latestDiscovery.data_status} />
                      <span className="caption">
                        MEASURED REPORT · SAVED {latestDiscovery.created_at.slice(0, 10)} ·{" "}
                        {report.call_ids?.length ?? 0} CALLS
                      </span>
                    </div>
                  )}

                  {report.films?.length > 0 && (
                    <div>
                      <p className="field-label">Film identity resolution</p>
                      <ul className="mt-3 space-y-2">
                        {report.films.map((film: SponsorFilmResolution) => (
                          <li key={film.input_title} className="text-sm text-paper-2">
                            <span className="font-display text-lg">{film.input_title}</span>{" "}
                            <span
                              className={cn(
                                "ml-2 border px-2 py-0.5 font-mono text-[0.55rem] uppercase tracking-[0.1em]",
                                matchTone(film.match_status),
                              )}
                            >
                              {film.match_status}
                            </span>
                            <span className="mt-1 block text-mute">
                              {film.usable && film.candidate
                                ? `→ ${film.candidate.name}${film.candidate.year ? ` (${film.candidate.year})` : ""}`
                                : film.match_status === "AMBIGUOUS"
                                  ? "Kept unusable — multiple candidates; nothing was promoted."
                                  : "Kept unusable — no verified match."}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    <p className="field-label">Brand candidates · human review only</p>
                    {report.brands.length > 0 ? (
                      <ul className="mt-3 grid gap-3">
                        {report.brands.map((brand: SponsorBrand) => (
                          <li key={brand.entity_id ?? brand.name} className="border border-line p-4">
                            <p className="font-display text-xl">{brand.name ?? brand.entity_id}</p>
                            <ul className="mt-2 space-y-1">
                              {brand.observations.map((observation, index) => (
                                <li
                                  key={`${brand.entity_id}-${index}`}
                                  className="font-mono text-[0.6rem] uppercase tracking-[0.1em] text-mute"
                                >
                                  {observation.source.toUpperCase()} · AFFINITY{" "}
                                  {affinityLabel(observation.affinity)}
                                  {observation.band
                                    ? ` · ${String(observation.band).toUpperCase()}`
                                    : ""}
                                  {observation.call_id ? ` · CALL ${observation.call_id}` : ""}
                                </li>
                              ))}
                            </ul>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div className="mt-3 border border-dashed border-line-strong p-6">
                        <p className="caption">No discovery payload · empty</p>
                        <p className="mt-2 text-sm leading-relaxed text-paper-2">
                          No typed brand candidates were returned. That is a finding, not an error —
                          sample brands would be a product violation.
                        </p>
                      </div>
                    )}
                  </div>

                  {report.non_brand_results?.length > 0 && (
                    <div>
                      <p className="field-label">Returned but not brand-typed</p>
                      <ul className="mt-3 space-y-1">
                        {report.non_brand_results.map((row) => (
                          <li key={`${row.entity_id}-${row.reason_code}`} className="caption">
                            {row.name ?? row.entity_id} · {row.reason_code.toUpperCase()}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    <p className="field-label">Interpretation limits</p>
                    <ul className="mt-3 space-y-2">
                      {(report.interpretation_limits ?? []).map((limit) => (
                        <li key={limit} className="text-sm leading-relaxed text-mute">
                          {limit}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {report.halt_reason && (
                    <p className="font-mono text-[0.62rem] uppercase tracking-[0.1em] text-blood">
                      Discovery stopped early ·{" "}
                      {String(
                        (report.halt_reason as Record<string, unknown>).error_type ?? "provider error",
                      )}
                    </p>
                  )}
                </div>
              ) : (
                <Locked
                  title="No discovery payload yet."
                  body="Evidence appears only after a measured discovery call. An empty evidence pane is the correct state until then; sample brands would be a product violation."
                  action="Run discovery"
                  onAction={() => setStep("Discovery")}
                />
              )}
            </div>
          )}

          {step === "Draft" && (
            <div>
              <h2 className="font-display text-4xl">Sponsorship draft</h2>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                Your words, versioned. Editing creates a new version; nothing is silently
                overwritten.
              </p>
              {!detail ? (
                <Locked
                  title="Select a campaign first."
                  body="Drafts belong to a campaign record, so there is nothing to write into yet."
                  action="Go to intake"
                  onAction={() => setStep("Intake")}
                />
              ) : (
                <>
                  <div className="mt-6 border border-line p-5">
                    <div className="grid gap-5">
                      <Field label="Brand name">
                        <TextInput
                          maxLength={200}
                          value={draftBrand}
                          onChange={(event) => setDraftBrand(event.target.value)}
                          placeholder="Brand One"
                        />
                      </Field>
                      <Field label="Pitch · your words, never auto-generated">
                        <TextArea
                          maxLength={4000}
                          value={draftPitch}
                          onChange={(event) => setDraftPitch(event.target.value)}
                          placeholder="What you would send, and why this film fits their audience."
                          className="min-h-[9rem]"
                        />
                      </Field>
                    </div>
                    {draftError && (
                      <p role="alert" className="mt-3 text-sm text-warn">
                        {draftError}
                      </p>
                    )}
                    <div className="mt-4 flex flex-wrap gap-3">
                      <button
                        type="button"
                        className="btn-primary"
                        onClick={() => void handleSaveDraft()}
                        disabled={draftBusy || !draftBrand.trim()}
                      >
                        {draftBusy
                          ? "Saving…"
                          : editingDraftId
                            ? "Save as new version"
                            : "Save version"}
                      </button>
                      {editingDraftId && (
                        <button
                          type="button"
                          className="btn-ghost"
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

                  <ul className="mt-8 divide-y divide-line border-y border-line">
                    {detail.drafts.length === 0 && (
                      <li className="py-6 text-sm text-mute">
                        No versions yet. Drafts are your words; Adjacent never writes outreach copy
                        for you.
                      </li>
                    )}
                    {detail.drafts.map((draft) => (
                      <li key={draft.draft_id} className="py-4">
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <p className="font-display text-xl">
                            {draft.brand_name}{" "}
                            <span className="font-mono text-[0.6rem] tracking-[0.12em] text-dim">
                              V{draft.version}
                            </span>
                          </p>
                          <span
                            className={cn(
                              "border px-2 py-0.5 font-mono text-[0.55rem] uppercase tracking-[0.1em]",
                              draft.status === "APPROVED"
                                ? "border-sage/40 text-sage"
                                : "border-amber/40 text-amber",
                            )}
                          >
                            {draft.status}
                            {draft.approved_at ? ` · ${draft.approved_at.slice(0, 10)}` : ""}
                          </span>
                        </div>
                        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-paper-2">
                          {draft.pitch || <em className="text-dim">No pitch text.</em>}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => startEditDraft(draft)}
                          >
                            Edit (new version)
                          </button>
                          <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => openReview(draft.draft_id)}
                          >
                            Add source review
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          {step === "Review" && (
            <div>
              <h2 className="font-display text-4xl">Official-source review</h2>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                You record what you checked. Adjacent does not independently verify a brand&apos;s
                willingness to sponsor.
              </p>
              {!detail || detail.drafts.length === 0 ? (
                <Locked
                  title="No draft to review yet."
                  body="A review is attached to a specific draft version. Write a draft first so the review has a subject."
                  action="Go to draft"
                  onAction={() => setStep("Draft")}
                />
              ) : (
                <>
                  <div className="mt-6 border border-line p-5">
                    <Field label="Draft version">
                      <select
                        className="mt-2 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                        value={reviewDraftId ?? ""}
                        onChange={(event) => setReviewDraftId(event.target.value || null)}
                      >
                        <option value="">Choose a draft version…</option>
                        {detail.drafts.map((draft) => (
                          <option key={draft.draft_id} value={draft.draft_id}>
                            {draft.brand_name} v{draft.version}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <div className="mt-5 grid gap-4">
                      <Field label="Official source URL">
                        <TextInput
                          maxLength={2000}
                          value={reviewUrl}
                          onChange={(event) => setReviewUrl(event.target.value)}
                          placeholder="https://…"
                        />
                      </Field>
                      <Field label="Commercial claim you checked">
                        <TextInput
                          maxLength={1000}
                          value={reviewClaim}
                          onChange={(event) => setReviewClaim(event.target.value)}
                          placeholder="Brand runs an open filmmaker sponsorship programme."
                        />
                      </Field>
                      <Field label="Your verification">
                        <select
                          className="mt-2 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                          value={reviewStatus}
                          onChange={(event) => setReviewStatus(event.target.value)}
                        >
                          <option value="SUPPORTED_BY_OFFICIAL_SOURCE">
                            Supported by official source
                          </option>
                          <option value="CONTRADICTED">Contradicted</option>
                          <option value="UNVERIFIED">Unverified</option>
                        </select>
                      </Field>
                      <Field label="Notes (optional)">
                        <TextInput
                          maxLength={2000}
                          value={reviewNotes}
                          onChange={(event) => setReviewNotes(event.target.value)}
                        />
                      </Field>
                    </div>
                    {reviewError && (
                      <p role="alert" className="mt-3 text-sm text-warn">
                        {reviewError}
                      </p>
                    )}
                    <button
                      type="button"
                      className="btn-amber mt-5"
                      disabled={reviewBusy || !reviewDraftId}
                      onClick={() => reviewDraftId && void handleSourceReview(reviewDraftId)}
                    >
                      {reviewBusy ? "Recording…" : "Record review"}
                    </button>
                  </div>

                  <ul className="mt-8 grid gap-3">
                    {detail.source_reviews.length === 0 && (
                      <li className="text-sm text-mute">
                        No reviews recorded. Approval requires one.
                      </li>
                    )}
                    {detail.source_reviews.map((review) => (
                      <li key={review.review_id} className="border border-line p-4">
                        <p className="caption">
                          {review.created_at.slice(0, 10)} ·{" "}
                          {detail.drafts.find((draft) => draft.draft_id === review.draft_id)
                            ?.brand_name ?? "draft"}{" "}
                          · {review.verification_status}
                        </p>
                        <p className="mt-1 text-sm text-paper-2">
                          {review.claim_checked || "claim not stated"}
                        </p>
                        {review.source_url && (
                          <p className="caption mt-1 break-all">{review.source_url}</p>
                        )}
                        {review.notes && <p className="mt-1 text-sm text-mute">{review.notes}</p>}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          {step === "Approval" && (
            <div>
              <h2 className="font-display text-4xl">Approval</h2>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                Approval requires a recorded official-source review for that exact draft version.
                It is a considered act on an immutable version, not a toggle.
              </p>
              {!detail || detail.drafts.length === 0 ? (
                <Locked
                  title="Nothing to approve yet."
                  body="Approval applies to a specific draft version. Write one, review it, then approve it."
                  action="Go to draft"
                  onAction={() => setStep("Draft")}
                />
              ) : (
                <ul className="mt-8 grid gap-4">
                  {detail.drafts.map((draft) => {
                    const reviews = detail.source_reviews.filter(
                      (review) => review.draft_id === draft.draft_id,
                    );
                    const approved = draft.status === "APPROVED";
                    return (
                      <li key={draft.draft_id} className="border border-line p-5">
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <p className="font-display text-2xl">
                            {draft.brand_name}{" "}
                            <span className="font-mono text-[0.6rem] tracking-[0.12em] text-dim">
                              V{draft.version}
                            </span>
                          </p>
                          {approved && (
                            <p className="chip chip-live">
                              <Check size={12} /> Approved
                            </p>
                          )}
                        </div>
                        <p className="caption mt-2">
                          Source reviews {reviews.length}
                          {reviews.length > 0
                            ? ` · ${reviews[reviews.length - 1].verification_status}`
                            : " · none recorded"}
                        </p>
                        {approved ? (
                          <p className="mt-2 text-sm text-mute">
                            Approved {draft.approved_at?.slice(0, 10)}. Later edits create a new
                            DRAFT version that must be reviewed and approved again.
                          </p>
                        ) : (
                          <>
                            <button
                              type="button"
                              className="btn-primary mt-4"
                              disabled={reviews.length === 0 || approvalBusy === draft.draft_id}
                              onClick={() => void handleApprove(draft.draft_id)}
                            >
                              {approvalBusy === draft.draft_id ? "Approving…" : "Approve this version"}
                            </button>
                            {reviews.length === 0 && (
                              <p className="mt-2 text-sm text-dim">
                                Record an official-source review before approval is offered.
                              </p>
                            )}
                          </>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
              {approvalError && (
                <p role="alert" className="mt-4 text-sm text-warn">
                  {approvalError}
                </p>
              )}
            </div>
          )}

          {step === "Export" && (
            <div>
              <h2 className="font-display text-4xl">Export</h2>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                Only approved drafts can leave. Unapproved work is excluded with its reason.
              </p>
              {!detail ? (
                <Locked
                  title="No campaign selected."
                  body="Export packages are built from one campaign record."
                  action="Go to intake"
                  onAction={() => setStep("Intake")}
                />
              ) : (
                <>
                  <button
                    type="button"
                    className="btn-primary mt-6"
                    onClick={() => void handleExport()}
                    disabled={exporting}
                  >
                    {exporting ? "Preparing…" : "Prepare export package"}
                    <Download size={16} />
                  </button>
                  {exportError && (
                    <p role="alert" className="mt-4 text-sm text-warn">
                      {exportError}
                    </p>
                  )}
                  {exportPkg && (
                    <div className="mt-6 border border-line p-5">
                      <p className="font-mono text-[0.62rem] uppercase tracking-[0.12em] text-amber">
                        {exportPkg.export_ready
                          ? `${exportPkg.approved_drafts.length} APPROVED DRAFT(S) READY`
                          : "NOTHING APPROVED YET — EXPORT IS EMPTY BY DESIGN"}
                      </p>
                      <ul className="mt-4 space-y-2">
                        {exportPkg.approved_drafts.map((draft) => (
                          <li key={draft.draft_id} className="text-sm text-paper-2">
                            APPROVED · {draft.brand_name} v{draft.version} ·{" "}
                            {draft.source_reviews.length} source review(s)
                          </li>
                        ))}
                        {exportPkg.excluded_drafts.map((excluded) => (
                          <li key={excluded.draft_id} className="text-sm text-warn">
                            EXCLUDED · {excluded.brand_name} · {excluded.reason}
                          </li>
                        ))}
                      </ul>
                      <div className="mt-5">
                        <p className="field-label">Interpretation limits attached to the export</p>
                        <ul className="mt-2 space-y-1">
                          {exportPkg.interpretation_limits.map((limit) => (
                            <li key={limit} className="text-sm leading-relaxed text-mute">
                              {limit}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div className="mt-5 flex flex-wrap gap-3">
                        <button
                          type="button"
                          className="test-card-export"
                          disabled={!exportPkg.export_ready}
                          onClick={downloadExport}
                        >
                          <span>Download .txt</span>
                          <small>APPROVED ONLY</small>
                        </button>
                        <button
                          type="button"
                          className="btn-ghost"
                          onClick={() => {
                            void navigator.clipboard
                              .writeText(JSON.stringify(exportPkg, null, 2))
                              .then(() => setCopied(true));
                          }}
                        >
                          <Clipboard size={14} />
                          {copied ? "Copied to clipboard" : "Copy package as JSON"}
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {step === "Outreach" && (
            <div>
              <h2 className="font-display text-4xl">Outreach ledger</h2>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
                Manually entered. Outcomes are observations, not model predictions. An observed zero
                is stored as 0; an unrecorded value stays missing, not zero.
              </p>
              {!detail ? (
                <Locked
                  title="No campaign selected."
                  body="Outreach records attach to a campaign and, optionally, a draft version."
                  action="Go to intake"
                  onAction={() => setStep("Intake")}
                />
              ) : (
                <>
                  <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    <Field label="Contact status">
                      <select
                        className="mt-2 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                        value={outreachStatus}
                        onChange={(event) => setOutreachStatus(event.target.value)}
                      >
                        <option value="" disabled>
                          Choose a contact status…
                        </option>
                        <option value="CONTACTED">Contacted</option>
                        <option value="RESPONDED">Responded</option>
                        <option value="PASSED">Passed</option>
                        <option value="DECLINED">Declined</option>
                        <option value="COLLABORATED">Collaborated</option>
                      </select>
                    </Field>
                    <Field label="Measurement status">
                      <select
                        className="mt-2 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                        value={outreachMeasurement}
                        onChange={(event) => setOutreachMeasurement(event.target.value)}
                      >
                        <option value="" disabled>
                          Choose a measurement status…
                        </option>
                        <option value="OBSERVED">Observed</option>
                        <option value="PARTIAL">Partial</option>
                        <option value="MISSING">Missing</option>
                        <option value="UNAVAILABLE">Unavailable</option>
                        <option value="FAILED">Failed</option>
                      </select>
                    </Field>
                    <Field label="Draft (optional)">
                      <select
                        className="mt-2 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                        value={outreachDraftId}
                        onChange={(event) => setOutreachDraftId(event.target.value)}
                      >
                        <option value="">— none —</option>
                        {detail.drafts.map((draft) => (
                          <option key={draft.draft_id} value={draft.draft_id}>
                            {draft.brand_name} v{draft.version}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Observed on (optional)">
                      <TextInput
                        maxLength={32}
                        value={outreachDate}
                        onChange={(event) => setOutreachDate(event.target.value)}
                        placeholder="2026-10-20"
                      />
                    </Field>
                    <Field label="Replies · blank = not recorded">
                      <TextInput
                        inputMode="numeric"
                        value={outreachReplies}
                        onChange={(event) => setOutreachReplies(event.target.value)}
                        placeholder="0"
                      />
                    </Field>
                    <Field label="Meetings · blank = not recorded">
                      <TextInput
                        inputMode="numeric"
                        value={outreachMeetings}
                        onChange={(event) => setOutreachMeetings(event.target.value)}
                        placeholder="0"
                      />
                    </Field>
                  </div>
                  <div className="mt-4">
                    <Field label="Outcome · what actually happened">
                      <TextArea
                        maxLength={2000}
                        value={outreachOutcome}
                        onChange={(event) => setOutreachOutcome(event.target.value)}
                      />
                    </Field>
                  </div>
                  <div className="mt-4">
                    <Field label="Notes (optional)">
                      <TextInput
                        maxLength={2000}
                        value={outreachNotes}
                        onChange={(event) => setOutreachNotes(event.target.value)}
                      />
                    </Field>
                  </div>
                  {outreachError && (
                    <p role="alert" className="mt-3 text-sm text-warn">
                      {outreachError}
                    </p>
                  )}
                  <button
                    type="button"
                    className="btn-amber mt-4"
                    onClick={() => void handleOutreach()}
                    disabled={outreachBusy}
                  >
                    {outreachBusy ? "Recording…" : "Record outreach"}
                  </button>

                  {detail.outreach.length === 0 ? (
                    <p className="mt-8 text-sm text-mute">
                      Empty on purpose. The next action is to record a real contact — or none.
                    </p>
                  ) : (
                    <ul className="mt-8 divide-y divide-line border-y border-line">
                      {detail.outreach.map((record: SponsorOutreachRecord) => (
                        <li key={record.outreach_id} className="py-4">
                          <p className="text-paper-2">
                            {record.contact_status} · {record.measurement_status}
                            {record.observed_on ? ` · ${record.observed_on}` : ""}
                          </p>
                          <p className="caption mt-1">
                            {Object.prototype.hasOwnProperty.call(record.metrics, "replies")
                              ? `REPLIES ${record.metrics.replies}`
                              : "REPLIES NOT RECORDED"}{" "}
                            ·{" "}
                            {Object.prototype.hasOwnProperty.call(record.metrics, "meetings")
                              ? `MEETINGS ${record.metrics.meetings}`
                              : "MEETINGS NOT RECORDED"}
                          </p>
                          {record.outcome && (
                            <p className="mt-2 text-sm leading-relaxed text-mute">
                              {record.outcome}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        <aside className="md:col-span-4">
          <PhotoFrame photo={photos.lanternStreet} className="aspect-[3/4]" />
          <div className="mt-6 border border-line p-5">
            <p className="type-kicker">Campaign</p>
            <p className="font-display mt-3 text-2xl">
              {detail?.campaign.film_title ?? "Nothing selected"}
            </p>
            <p className="mt-2 text-sm text-mute">
              {detail?.campaign.goals || "No goal recorded"}
            </p>
            <dl className="mt-5 space-y-2 text-sm">
              <div className="flex justify-between gap-4 border-b border-line pb-2">
                <dt className="caption">Stage</dt>
                <dd className="text-paper-2">
                  {String(STEPS.indexOf(step) + 1).padStart(2, "0")} / {STEPS.length}
                </dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-line pb-2">
                <dt className="caption">Discoveries</dt>
                <dd className="text-paper-2">{detail?.discoveries.length ?? 0}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-line pb-2">
                <dt className="caption">Draft versions</dt>
                <dd className="text-paper-2">{detail?.drafts.length ?? 0}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-line pb-2">
                <dt className="caption">Source reviews</dt>
                <dd className="text-paper-2">{reviewCount}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="caption">Approved</dt>
                <dd className="text-paper-2">{approvedCount}</dd>
              </div>
            </dl>
            {detailLoading && <p className="caption mt-4">Loading campaign…</p>}
            {detailError && (
              <p role="alert" className="mt-4 text-sm text-warn">
                {detailError}
              </p>
            )}
          </div>

          <div className="mt-6 border border-line p-5">
            <p className="type-kicker">Your campaigns</p>
            {campaignsLoading && <p className="caption mt-3">Loading…</p>}
            {campaignsError && (
              <p role="alert" className="mt-3 text-sm text-warn">
                {campaignsError}
              </p>
            )}
            {!campaignsLoading && !campaignsError && campaigns.length === 0 && (
              <p className="mt-3 text-sm text-mute">
                No campaigns yet. Create one above — nothing is sent anywhere until you run
                discovery yourself.
              </p>
            )}
            <ul className="mt-3 space-y-2">
              {campaigns.map((campaign) => (
                <li key={campaign.campaign_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setExportPkg(null);
                      setDiscoveryUnavailable(null);
                      setDiscoveryError(null);
                      void reloadDetail(campaign.campaign_id);
                    }}
                    className={cn(
                      "w-full border px-3 py-2 text-left transition-colors",
                      detail?.campaign.campaign_id === campaign.campaign_id
                        ? "border-amber/60 bg-amber/5"
                        : "border-line hover:border-line-strong",
                    )}
                  >
                    <span className="block text-sm text-paper-2">
                      {campaign.film_title}
                      {campaign.film_year ? ` (${campaign.film_year})` : ""}
                    </span>
                    <span className="caption mt-1 block">
                      {campaign.discovery_count ?? 0} DISCOVERIES · {campaign.draft_count ?? 0}{" "}
                      DRAFTS · {campaign.outreach_count ?? 0} OUTREACH
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="btn-ghost mt-4"
              onClick={() => setStep("Intake")}
            >
              <Plus size={14} /> New campaign
            </button>
          </div>

          <div className="mt-6 border border-amber/25 bg-amber/5 p-5">
            <p className="type-kicker text-amber">What this workflow does not claim</p>
            <ul className="mt-3 space-y-2">
              {READING_LIMITS.map((limit) => (
                <li key={limit} className="text-xs leading-relaxed text-mute">
                  {limit}
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Locked({
  title,
  body,
  action,
  onAction,
}: {
  title: string;
  body: string;
  action: string;
  onAction: () => void;
}) {
  return (
    <div className="mt-8 border border-dashed border-line-strong p-8">
      <p className="chip chip-warn">Not available yet</p>
      <h3 className="font-display mt-4 text-3xl">{title}</h3>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">{body}</p>
      <button type="button" className="btn-ghost mt-5" onClick={onAction}>
        {action}
        <ArrowRight size={14} />
      </button>
    </div>
  );
}
