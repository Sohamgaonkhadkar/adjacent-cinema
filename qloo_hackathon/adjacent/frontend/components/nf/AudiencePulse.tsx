"use client";

/**
 * Audience Pulse — the poll attached to a saved decision.
 *
 * Three ideas, in this order:
 *
 * 1. the rule is written here, before collection, and the backend freezes it on
 *    the first response (a database trigger, not a promise);
 * 2. participants answer through one token link and the panel shows the counts
 *    that were actually stored;
 * 3. evaluating applies that frozen rule and records the outcome — including
 *    INCONCLUSIVE when the sample is smaller than the creator's own minimum.
 *
 * The panel never fills a gap: no responses reads as zero responses, a disabled
 * deployment says so, and every number on screen came from a stored record.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  PulseRequestError,
  closePulse,
  createPulse as createPulseRequest,
  evaluatePulse as evaluatePulseRequest,
  listPulses,
} from "@/lib/api";
import {
  PULSE_MAX_OPTIONS,
  PULSE_MIN_OPTIONS,
  buildOwnerPulseView,
  describeOutcome,
  distributionRows,
  evaluationLine,
  evaluationRequestSeed,
  formatPulseWindow,
  pulseErrorMessage,
  remainingEvidenceLine,
  validatePulseDraft,
  type OwnerPulseView,
  type PulseDraft,
  type PulsePollRow,
} from "@/lib/pulse";
import { stableRequestId } from "@/lib/requestId";
import { cn } from "@/lib/cn";

const TONE_TEXT: Record<string, string> = {
  live: "text-sage",
  neutral: "text-paper-2",
  warn: "text-amber",
  fail: "text-blood",
};

function defaultDraft(): PulseDraft {
  const now = new Date();
  const opens = new Date(now.getTime() - 60 * 1000);
  const closes = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000);
  return {
    question: "",
    options: ["", ""],
    opensAt: toLocalInput(opens),
    closesAt: toLocalInput(closes),
    ruleOptionIndex: 0,
    thresholdPercent: 60,
    minResponses: 10,
  };
}

function toLocalInput(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export function AudiencePulse({
  experimentId,
  hypothesis,
  onChanged,
}: {
  experimentId: string;
  hypothesis: string;
  onChanged: () => Promise<void>;
}) {
  const [view, setView] = useState<OwnerPulseView | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<{ message: string; status: number } | null>(null);
  const [draft, setDraft] = useState<PulseDraft>(defaultDraft);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const current = ++requestId.current;
    setLoading(true);
    try {
      const payload = await listPulses(experimentId);
      if (current !== requestId.current) return;
      setView(buildOwnerPulseView(payload));
      setLoadError(null);
    } catch (err) {
      if (current !== requestId.current) return;
      const status = err instanceof PulseRequestError ? err.status : 0;
      setView(null);
      setLoadError({
        status,
        message: pulseErrorMessage(status, err instanceof Error ? err.message : null),
      });
    } finally {
      if (current === requestId.current) setLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    void load();
    return () => {
      requestId.current += 1;
    };
  }, [load]);

  const validation = validatePulseDraft(draft);
  const hasOpenPoll = Boolean(view?.rows.some((row) => row.collectionStatus === "OPEN"));

  async function publish() {
    if (!validation.ok || !validation.payload) {
      setMessage("Fix the highlighted fields before publishing.");
      return;
    }
    setBusy("create");
    setMessage(null);
    try {
      const payload = validation.payload;
      await createPulseRequest(experimentId, {
        request_id: stableRequestId(`pulse-${experimentId}`, payload),
        ...payload,
      });
      setMessage("Poll published. The rule is now locked in when the first response arrives.");
      setDraft(defaultDraft());
      setShowForm(false);
      await load();
      await onChanged();
    } catch (err) {
      const status = err instanceof PulseRequestError ? err.status : 0;
      setMessage(pulseErrorMessage(status, err instanceof Error ? err.message : null));
    } finally {
      setBusy(null);
    }
  }

  async function close(row: PulsePollRow) {
    setBusy(`close-${row.pollId}`);
    setMessage(null);
    try {
      await closePulse(experimentId, row.pollId);
      setMessage("Collection closed. Stored responses are unchanged and can still be evaluated.");
      await load();
    } catch (err) {
      const status = err instanceof PulseRequestError ? err.status : 0;
      setMessage(pulseErrorMessage(status, err instanceof Error ? err.message : null));
    } finally {
      setBusy(null);
    }
  }

  async function evaluate(row: PulsePollRow) {
    setBusy(`evaluate-${row.pollId}`);
    setMessage(null);
    try {
      const result = await evaluatePulseRequest(
        experimentId,
        row.pollId,
        stableRequestId(`pulse-eval-${row.pollId}`, evaluationRequestSeed(row)),
      );
      const outcome = describeOutcome(result.evaluation.outcome);
      setMessage(
        `${outcome.label} — recorded against the pre-registered rule. Earlier evaluations stay in the history.`,
      );
      await load();
    } catch (err) {
      const status = err instanceof PulseRequestError ? err.status : 0;
      setMessage(pulseErrorMessage(status, err instanceof Error ? err.message : null));
    } finally {
      setBusy(null);
    }
  }

  async function copyLink(path: string) {
    const absolute = `${window.location.origin}${path}`;
    try {
      await navigator.clipboard.writeText(absolute);
      setCopied(path);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      setMessage(`Copy failed. The link is ${absolute}`);
    }
  }

  if (loading && !view) {
    return (
      <section aria-label="Audience Pulse" className="border border-line p-4">
        <p className="type-kicker">Audience Pulse</p>
        <p role="status" className="mt-2 text-sm text-mute">
          Loading the poll registry…
        </p>
      </section>
    );
  }

  if (loadError) {
    const unavailable = loadError.status === 404 || loadError.status === 503;
    return (
      <section aria-label="Audience Pulse" className="border border-dashed border-line-strong p-4">
        <p className="type-kicker">Audience Pulse · unavailable</p>
        <p className="mt-2 text-sm leading-relaxed text-mute">{loadError.message}</p>
        <p className="caption mt-2">
          {unavailable
            ? "A poll needs a backend that can store responses and serve the participant link. Nothing is simulated here."
            : "The request failed; no poll data was invented to fill the panel."}
        </p>
        <button type="button" className="btn-ghost mt-3" onClick={() => void load()}>
          Retry
        </button>
      </section>
    );
  }

  return (
    <section aria-label="Audience Pulse" className="border border-line p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="type-kicker">Audience Pulse · pre-registered poll</p>
        <p className="font-mono text-[0.6rem] uppercase tracking-[0.12em] text-dim">
          Rule frozen on first response
        </p>
      </div>

      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-mute">
        Ask one question, write down the bar that would support or contradict the hypothesis, and
        share a link. The counts below are the responses the backend actually stored; a share of a
        self-selected sample is not attendance, revenue or a prediction about an audience.
      </p>

      {view && !view.sharingEnabled && (
        <p role="status" className="mt-3 border border-amber/40 bg-amber/10 px-3 py-2 text-sm text-amber">
          Participant links are disabled on this deployment. The backend needs
          <span className="font-mono"> ADJACENT_PULSE_SHARE_ENABLED=1</span> before a published poll
          can collect anything.
        </p>
      )}

      {view?.rows.length === 0 && (
        <p className="mt-3 text-sm text-mute">
          No poll yet. The saved hypothesis travels with it, so the poll cannot be judged against a
          rule written afterwards.
        </p>
      )}

      <ul className="mt-4 grid gap-4">
        {view?.rows.map((row) => {
          return (
            <li key={row.pollId} className="border border-line p-3">
              <p className="text-sm leading-relaxed text-paper-2">{row.question}</p>
              <p className="mt-1 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-dim">
                {row.collection.label} · {row.window}
                {row.frozen ? " · definition frozen" : " · not frozen yet"}
              </p>
              <p className="caption mt-1">{row.collection.detail}</p>
              <p
                className={cn(
                  "mt-2 font-mono text-[0.62rem] uppercase tracking-[0.12em]",
                  TONE_TEXT[row.collection.tone],
                )}
              >
                {row.headline}
              </p>
              <div className="mt-2 grid gap-1">
                {distributionRows(row.counts).map((option) => (
                  <div key={option.optionId} className="flex items-center gap-2">
                    <span className="w-32 shrink-0 truncate text-xs text-mute">{option.label}</span>
                    <span className="h-1.5 flex-1 bg-line">
                      <span
                        className="block h-1.5 bg-amber"
                        style={{ width: `${option.widthPercent}%` }}
                      />
                    </span>
                    <span className="w-16 shrink-0 text-right font-mono text-[0.6rem] text-dim">
                      {option.count}
                      {option.share === null ? "" : ` · ${Math.round(option.share * 100)}%`}
                    </span>
                  </div>
                ))}
              </div>
              <p className="caption mt-2">Rule · {row.ruleStatement}</p>
              <p className="mt-1 text-xs leading-relaxed text-mute">
                {evaluationLine(row.latest ?? row.preview)}
              </p>
              {remainingEvidenceLine(row.latest ?? row.preview) && (
                <p className="mt-1 text-xs text-amber">
                  {remainingEvidenceLine(row.latest ?? row.preview)}
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {row.sharePath && (
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => void copyLink(row.sharePath as string)}
                  >
                    {copied === row.sharePath ? "Link copied" : "Copy participant link"}
                  </button>
                )}
                {row.collectionStatus === "OPEN" && (
                  <button
                    type="button"
                    className="btn-ghost"
                    disabled={busy !== null}
                    onClick={() => void close(row)}
                  >
                    Close collection
                  </button>
                )}
                <button
                  type="button"
                  className="btn-amber"
                  disabled={busy !== null}
                  onClick={() => void evaluate(row)}
                >
                  {busy === `evaluate-${row.pollId}` ? "Applying the rule…" : "Evaluate against the rule"}
                </button>
              </div>
            </li>
          );
        })}
      </ul>

      {!hasOpenPoll && (
        <div className="mt-4">
          {!showForm ? (
            <button type="button" className="btn-ghost" onClick={() => setShowForm(true)}>
              Draft a poll from this hypothesis
            </button>
          ) : (
            <div className="grid gap-3">
              <p className="caption">
                Hypothesis this poll is judged against · {hypothesis}
              </p>
              <label className="block">
                <span className="field-label">Question · one line, answerable</span>
                <input
                  className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                  value={draft.question}
                  maxLength={240}
                  onChange={(event) => setDraft({ ...draft, question: event.target.value })}
                />
                {validation.errors.question && (
                  <span className="mt-1 block text-xs text-blood">{validation.errors.question}</span>
                )}
              </label>

              <div className="grid gap-2">
                <span className="field-label">Options · {PULSE_MIN_OPTIONS}–{PULSE_MAX_OPTIONS}</span>
                {draft.options.map((option, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <input
                      className="w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                      value={option}
                      maxLength={120}
                      aria-label={`Option ${index + 1}`}
                      onChange={(event) => {
                        const options = [...draft.options];
                        options[index] = event.target.value;
                        setDraft({ ...draft, options });
                      }}
                    />
                    {draft.options.length > PULSE_MIN_OPTIONS && (
                      <button
                        type="button"
                        className="btn-ghost"
                        aria-label={`Remove option ${index + 1}`}
                        onClick={() =>
                          setDraft({
                            ...draft,
                            options: draft.options.filter((_, position) => position !== index),
                          })
                        }
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                {draft.options.length < PULSE_MAX_OPTIONS && (
                  <button
                    type="button"
                    className="btn-ghost justify-self-start"
                    onClick={() => setDraft({ ...draft, options: [...draft.options, ""] })}
                  >
                    Add option
                  </button>
                )}
                {validation.errors.options && (
                  <span className="text-xs text-blood">{validation.errors.options}</span>
                )}
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="field-label">Collection opens</span>
                  <input
                    type="datetime-local"
                    className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                    value={draft.opensAt}
                    onChange={(event) => setDraft({ ...draft, opensAt: event.target.value })}
                  />
                  {validation.errors.opensAt && (
                    <span className="mt-1 block text-xs text-blood">{validation.errors.opensAt}</span>
                  )}
                </label>
                <label className="block">
                  <span className="field-label">Collection closes · the link expires here</span>
                  <input
                    type="datetime-local"
                    className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                    value={draft.closesAt}
                    onChange={(event) => setDraft({ ...draft, closesAt: event.target.value })}
                  />
                  {validation.errors.closesAt && (
                    <span className="mt-1 block text-xs text-blood">{validation.errors.closesAt}</span>
                  )}
                </label>
                <label className="block">
                  <span className="field-label">Supporting option</span>
                  <select
                    className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                    value={draft.ruleOptionIndex}
                    onChange={(event) =>
                      setDraft({ ...draft, ruleOptionIndex: Number(event.target.value) })
                    }
                  >
                    {draft.options.map((option, index) => (
                      <option key={index} value={index}>
                        {option.trim() || `Option ${index + 1}`}
                      </option>
                    ))}
                  </select>
                  {validation.errors.ruleOptionIndex && (
                    <span className="mt-1 block text-xs text-blood">
                      {validation.errors.ruleOptionIndex}
                    </span>
                  )}
                </label>
                <label className="block">
                  <span className="field-label">Supporting share · percent</span>
                  <input
                    inputMode="numeric"
                    className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                    value={draft.thresholdPercent}
                    onChange={(event) =>
                      setDraft({ ...draft, thresholdPercent: Number(event.target.value) })
                    }
                  />
                  {validation.errors.thresholdPercent && (
                    <span className="mt-1 block text-xs text-blood">
                      {validation.errors.thresholdPercent}
                    </span>
                  )}
                </label>
                <label className="block">
                  <span className="field-label">Minimum responses before the rule decides</span>
                  <input
                    inputMode="numeric"
                    className="mt-1 w-full border border-line bg-ink px-3 py-2 text-sm text-paper-2"
                    value={draft.minResponses}
                    onChange={(event) =>
                      setDraft({ ...draft, minResponses: Number(event.target.value) })
                    }
                  />
                  {validation.errors.minResponses && (
                    <span className="mt-1 block text-xs text-blood">
                      {validation.errors.minResponses}
                    </span>
                  )}
                </label>
              </div>

              <p className="caption">
                Window on publish ·{" "}
                {validation.errors.opensAt || validation.errors.closesAt
                  ? "not set yet"
                  : formatPulseWindow(
                      new Date(draft.opensAt).toISOString(),
                      new Date(draft.closesAt).toISOString(),
                    )}
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-amber"
                  disabled={busy !== null || !validation.ok}
                  onClick={() => void publish()}
                >
                  {busy === "create" ? "Publishing…" : "Publish poll"}
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={busy !== null}
                  onClick={() => {
                    setShowForm(false);
                    setMessage(null);
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {message && (
        <p role="status" aria-live="polite" className="mt-3 font-mono text-[0.62rem] text-amber">
          {message}
        </p>
      )}

      <p className="caption mt-3">
        One response per browser session, throttled per connection. Participants choose to open the
        link, so the sample is self-selected — the evaluation says so in its own words.
      </p>
    </section>
  );
}
