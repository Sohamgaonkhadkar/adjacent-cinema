"use client";

import { useEffect, useState } from "react";
import {
  getSynthesisStatus,
  saveExperiment,
  synthesizeRun,
  type SynthesisResponse,
  type SynthesisStatus,
} from "@/lib/api";
import type { InvestigationData, TraceRow } from "@/types/adjacent";
import { EvidenceReferences } from "@/components/EvidenceTrace";
import { Field, TextArea } from "./Field";
import { ClaimChip } from "./Chips";

/**
 * Optional Synthesis (Role B) panel — ported from the existing Creator
 * implementation and restyled in the Project Nightfall language.
 *
 * It is provider-gated: no provider means an honest "unavailable" line, never a
 * simulated brief. The model's proposal only becomes a saved plan through an
 * explicit, editable review, and the saved record keeps the model's original
 * wording distinct from the creator's edits.
 */
export function SynthesisPanel({
  runId,
  filmTitle,
  investigation,
  traceRows,
  onSaved,
}: {
  runId: string;
  filmTitle: string;
  investigation: InvestigationData;
  traceRows: TraceRow[];
  onSaved: (message: string) => void;
}) {
  const [status, setStatus] = useState<SynthesisStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [brief, setBrief] = useState<SynthesisResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<{
    hypothesis: string;
    action_plan: string;
    success_criteria: string;
    observation_window: string;
  } | null>(null);
  const [adoptMessage, setAdoptMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStatusLoading(true);
    setStatus(null);
    setStatusError(null);
    setBrief(null);
    setDraft(null);
    setAdoptMessage(null);
    setError(null);
    getSynthesisStatus()
      .then((next) => {
        if (!cancelled) setStatus(next);
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setStatus(null);
          setStatusError(
            reason instanceof Error ? reason.message : "Synthesis availability could not be checked",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setStatusLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  function generate() {
    setBusy(true);
    setError(null);
    synthesizeRun(runId)
      .then(setBrief)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Could not generate the brief"),
      )
      .finally(() => setBusy(false));
  }

  function startAdoption() {
    if (!brief) return;
    const proposal = brief.synthesis.experiment_proposal;
    setAdoptMessage(null);
    setDraft({
      hypothesis:
        proposal.kind === "test"
          ? proposal.hypothesis
          : "No supported hypothesis yet — this is an information-gathering step, not a positioning test.",
      action_plan: proposal.action_plan,
      success_criteria: proposal.success_criteria,
      observation_window: proposal.observation_window,
    });
  }

  async function confirmAdoption() {
    if (!brief || !draft) return;
    setBusy(true);
    setError(null);
    try {
      const proposal = brief.synthesis.experiment_proposal;
      const response = await saveExperiment({
        request_id: `exp-${runId}`,
        film_title: filmTitle,
        hypothesis: draft.hypothesis,
        success_criteria: draft.success_criteria,
        observation_window: draft.observation_window,
        action_plan: draft.action_plan,
        data_status: investigation.data_status,
        source_run_id: runId,
        source_bet: {},
        provenance: {},
        film_context: (investigation.film ?? {}) as Record<string, unknown>,
        investigation_summary: {
          investigation_id: investigation.investigation_id,
          data_status: investigation.data_status,
          primary_hypothesis: investigation.hypotheses.primary?.statement ?? null,
          limitations: investigation.limitations ?? [],
          open_questions: investigation.open_questions ?? [],
        },
        evidence_refs: investigation.provenance?.call_ids ?? [],
        synthesis_snapshot: {
          investigation_id: investigation.investigation_id,
          source_run_id: runId,
          schema_version: brief.metadata.schema_version,
          method: brief.metadata.method,
          provider_kind: brief.metadata.provider_kind,
          model: brief.metadata.model,
          validation: brief.metadata.validation,
          summary: brief.synthesis.summary,
          hypothesis_restated: brief.synthesis.hypothesis_restated,
          claims: brief.synthesis.claims,
          caveats: brief.synthesis.caveats,
          limitations: investigation.limitations ?? [],
          evidence_refs: investigation.provenance?.call_ids ?? [],
          data_status: investigation.data_status,
          experiment_proposal: proposal,
        },
        adopted_proposal: {
          kind: proposal.kind,
          hypothesis: proposal.hypothesis,
          action_plan: proposal.action_plan,
          success_criteria: proposal.success_criteria,
          observation_window: proposal.observation_window,
          falsification: proposal.falsification,
          relevant_metrics: proposal.relevant_metrics,
          assumptions: proposal.assumptions,
          limitations: proposal.limitations,
        },
      });
      setDraft(null);
      setAdoptMessage(
        response.duplicate
          ? "This analysis run already has a saved decision — showing the original. Nothing was overwritten."
          : proposal.kind === "information_gathering"
            ? "Saved as an information-gathering plan (no positioning hypothesis was supported). It has not been executed."
            : "Saved as a planned experiment from the adopted proposal. This records intent; it does not execute the experiment.",
      );
      onSaved(
        response.duplicate
          ? "Existing saved decision retained."
          : "Adopted proposal saved as the planned experiment.",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the adopted experiment");
    } finally {
      setBusy(false);
    }
  }

  const method = brief?.metadata.method;
  const methodLabel =
    method === "live_llm"
      ? "LIVE MODEL SYNTHESIS"
      : method === "stub"
        ? "STUB PROVIDER — NOT A REAL MODEL RESULT"
        : method === "deterministic_fallback"
          ? "DETERMINISTIC FALLBACK — MODEL OUTPUT UNAVAILABLE OR REJECTED"
          : null;

  return (
    <div className="border border-line p-5">
      <p className="type-kicker">Optional synthesis</p>
      <h3 className="font-display mt-2 text-2xl md:text-3xl">A written brief over the evidence.</h3>
      <p className="mt-2 text-sm leading-relaxed text-mute">
        A provider-backed brief can summarise this investigation. It cannot add evidence: the
        investigation above is complete without it, and a missing provider is reported as
        unavailable.
      </p>

      {statusLoading && <p className="mt-4 text-xs text-mute">Checking synthesis availability…</p>}
      {!statusLoading && statusError && (
        <p role="alert" className="mt-4 text-xs text-mute">
          Availability could not be checked — {statusError}. The investigation above remains
          available; no model result is assumed.
        </p>
      )}
      {!statusLoading && !statusError && !status && (
        <p className="mt-4 text-xs text-mute">No synthesis availability status was returned.</p>
      )}
      {!statusLoading && status && !status.available && (
        <p className="mt-4 text-xs text-mute">
          Unavailable — {status.blocked_reason ?? "no provider configured."}
        </p>
      )}
      {!statusLoading && status?.available && !brief && (
        <button type="button" className="btn-ghost mt-4" onClick={generate} disabled={busy}>
          {busy ? "Generating…" : "Generate decision brief"}
        </button>
      )}
      {error && (
        <p role="alert" className="mt-4 text-sm text-warn">
          {error}
        </p>
      )}

      {brief && (
        <div className="mt-5 space-y-4">
          {methodLabel && <p className="type-meta text-amber">{methodLabel}</p>}
          {brief.metadata.llm_error && (
            <p className="text-xs text-mute">Reason · {brief.metadata.llm_error}</p>
          )}
          <p className="text-sm leading-relaxed text-paper-2">{brief.synthesis.summary}</p>
          <p className="text-sm leading-relaxed text-paper-2">
            <span className="caption">Hypothesis · </span>
            {brief.synthesis.hypothesis_restated}
          </p>

          {brief.synthesis.claims?.length > 0 && (
            <div>
              <p className="type-meta">Claims &amp; evidence</p>
              <ul className="mt-2 space-y-3">
                {brief.synthesis.claims.map((claim, index) => (
                  <li key={`${claim.statement}-${index}`} className="text-xs leading-relaxed text-paper-2">
                    <ClaimChip kind={claim.claim_type} /> {claim.statement}
                    {claim.evidence_refs?.length > 0 ? (
                      <EvidenceReferences refs={claim.evidence_refs} traceRows={traceRows} scope={`synthesis-${runId}`} />
                    ) : (
                      <span className="ml-1 text-dim">· no call reference supplied</span>
                    )}
                    {claim.limitations && <em className="text-mute"> — {claim.limitations}</em>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {brief.synthesis.caveats?.length > 0 && (
            <div>
              <p className="type-meta">Caveats</p>
              <ul className="mt-2 space-y-1 text-xs leading-relaxed text-mute">
                {brief.synthesis.caveats.map((caveat, index) => (
                  <li key={`${caveat}-${index}`}>— {caveat}</li>
                ))}
              </ul>
            </div>
          )}

          {brief.synthesis.experiment_proposal && !draft && (
            <div className="border border-line p-4">
              <p className="type-meta">
                {brief.synthesis.experiment_proposal.kind === "test"
                  ? "Proposed experiment · not yet saved"
                  : "Proposed next step · information gathering"}
              </p>
              <p className="mt-2 text-xs leading-relaxed text-paper-2">
                {brief.synthesis.experiment_proposal.action_plan}
              </p>
              <button type="button" className="btn-amber mt-3" onClick={startAdoption}>
                {brief.synthesis.experiment_proposal.kind === "test"
                  ? "Review and edit proposal"
                  : "Review information-gathering plan"}
              </button>
            </div>
          )}

          {draft && (
            <div className="border border-amber/30 bg-amber/10 p-4">
              <p className="type-meta text-amber">Review &amp; edit before saving — nothing is saved yet</p>
              <div className="mt-3 space-y-3">
                {(["hypothesis", "action_plan", "success_criteria", "observation_window"] as const).map(
                  (field) => (
                    <Field key={field} label={field.replace(/_/g, " ")}>
                      <TextArea
                        value={draft[field]}
                        onChange={(event) => setDraft({ ...draft, [field]: event.target.value })}
                        aria-label={field.replace(/_/g, " ")}
                      />
                    </Field>
                  ),
                )}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" className="btn-primary" onClick={() => void confirmAdoption()} disabled={busy}>
                  {busy ? "Saving…" : "Confirm adoption and save as planned"}
                </button>
                <button type="button" className="btn-ghost" onClick={() => setDraft(null)} disabled={busy}>
                  Cancel
                </button>
              </div>
            </div>
          )}

          {adoptMessage && (
            <p role="status" aria-live="polite" className="text-xs text-amber">
              {adoptMessage}
            </p>
          )}
          <p className="font-mono text-[0.58rem] leading-relaxed text-dim">
            method: {brief.metadata.method} · validation: {brief.metadata.validation}
          </p>
        </div>
      )}
    </div>
  );
}
