"use client";

/**
 * Participant page for an Audience Pulse link.
 *
 * This is the only route in the app that an unauthenticated visitor is meant to
 * use, and it is deliberately the smallest page here: one question, the options
 * the creator wrote, and a submit. It reads through the same `/api` proxy as the
 * rest of the app, so the backend stays server-side.
 *
 * It shows a state, never a substitute:
 *   • loading            — the ballot is being fetched;
 *   • unavailable/error  — the link is unknown or the deployment cannot serve it;
 *   • open               — the ballot;
 *   • answered           — one response per session, totals hidden while open;
 *   • closed/expired     — the window is over, with the stored totals.
 *
 * No vote is created locally, and a failed request never renders as a
 * successful submission.
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  PulseRequestError,
  readSharedPulse,
  submitPulseResponse,
} from "@/lib/api";
import {
  buildBallotState,
  describeCollection,
  formatShare,
  pulseErrorMessage,
  type BallotState,
  type SharedPulse,
} from "@/lib/pulse";
import { cn } from "@/lib/cn";

export default function AudiencePulseBallotPage() {
  const params = useParams<{ token: string }>();
  const token = typeof params?.token === "string" ? params.token : "";

  const [state, setState] = useState<BallotState>({ kind: "loading" });
  const [payload, setPayload] = useState<SharedPulse | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) {
      setState({
        kind: "unavailable",
        title: "This poll is not available",
        detail: "The link did not include a poll token.",
      });
      return;
    }
    setState({ kind: "loading" });
    try {
      const data = await readSharedPulse(token);
      setPayload(data);
      setState(buildBallotState({ data }));
    } catch (err) {
      const status = err instanceof PulseRequestError ? err.status : null;
      setPayload(null);
      setState(
        buildBallotState({
          status,
          error: pulseErrorMessage(status, err instanceof Error ? err.message : null),
        }),
      );
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit() {
    if (!selected) {
      setMessage("Choose one option before submitting.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await submitPulseResponse(token, selected);
      setMessage("Response recorded. Thank you — this is the only time this browser can answer.");
      await load();
    } catch (err) {
      const status = err instanceof PulseRequestError ? err.status : null;
      setMessage(pulseErrorMessage(status, err instanceof Error ? err.message : null));
      if (status === 409) await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-14 md:px-8">
      <p className="type-kicker">Audience Pulse</p>
      <h1 className="mt-3 font-serif text-3xl leading-tight text-paper md:text-4xl">
        One question from the filmmaker
      </h1>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-mute">
        Your answer is recorded once and counted with the rest. This is a small poll, not a survey
        of an audience: the people who open the link are the sample.
      </p>

      <div className="mt-8 border border-line p-5">
        {state.kind === "loading" && (
          <p role="status" className="text-sm text-mute">
            Opening the poll…
          </p>
        )}

        {state.kind === "unavailable" && (
          <>
            <p className="font-serif text-xl text-paper">{state.title}</p>
            <p className="mt-2 text-sm leading-relaxed text-mute">{state.detail}</p>
            <p className="caption mt-3">
              Nothing is shown in place of the poll. Ask the filmmaker for a current link.
            </p>
          </>
        )}

        {state.kind === "error" && (
          <>
            <p className="font-serif text-xl text-paper">The poll could not be opened</p>
            <p className="mt-2 text-sm leading-relaxed text-mute">{state.detail}</p>
            <button type="button" className="btn-ghost mt-3" onClick={() => void load()}>
              Try again
            </button>
          </>
        )}

        {state.kind === "open" && (
          <>
            <p className="font-serif text-xl leading-snug text-paper">{state.question}</p>
            <p className="mt-1 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-dim">
              Open {state.window}
            </p>
            <fieldset className="mt-5 grid gap-2">
              <legend className="sr-only">Choose one option</legend>
              {state.options.map((option) => (
                <label
                  key={option.option_id}
                  className={cn(
                    "flex cursor-pointer items-center gap-3 border px-3 py-3 text-sm transition-colors",
                    selected === option.option_id
                      ? "border-amber bg-amber/10 text-paper"
                      : "border-line text-paper-2 hover:border-line-strong",
                  )}
                >
                  <input
                    type="radio"
                    name="pulse-option"
                    value={option.option_id}
                    checked={selected === option.option_id}
                    onChange={() => setSelected(option.option_id)}
                    className="accent-amber"
                  />
                  {option.label}
                </label>
              ))}
            </fieldset>
            <button
              type="button"
              className="btn-amber mt-4"
              disabled={busy || !selected}
              onClick={() => void submit()}
            >
              {busy ? "Recording…" : "Submit response"}
            </button>
          </>
        )}

        {state.kind === "answered" && (
          <>
            <p className="font-serif text-xl text-paper">Already answered</p>
            <p className="mt-2 text-sm leading-relaxed text-mute">{state.detail}</p>
            <p className="mt-2 text-sm leading-relaxed text-mute">{state.question}</p>
          </>
        )}

        {state.kind === "closed" && (
          <>
            <p className="font-serif text-xl text-paper">Collection has finished</p>
            <p className="mt-2 text-sm leading-relaxed text-mute">{state.reason}</p>
            <p className="mt-2 text-sm text-paper-2">{state.question}</p>
            {state.counts && state.counts.total > 0 ? (
              <ul className="mt-4 grid gap-1">
                {state.counts.options.map((option) => (
                  <li
                    key={option.option_id}
                    className="flex items-center justify-between gap-3 border-b border-line py-1 text-sm text-paper-2"
                  >
                    <span>{option.label}</span>
                    <span className="font-mono text-[0.62rem] text-dim">
                      {option.count} · {formatShare(option.share)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="caption mt-3">
                {state.counts
                  ? "No responses were recorded before the window closed."
                  : "Totals are not shown for this link."}
              </p>
            )}
          </>
        )}

        {payload && !payload.collection.accepting_responses && (
          <p className="caption mt-4">
            {describeCollection(payload.collection).label} ·{" "}
            {describeCollection(payload.collection).detail}
          </p>
        )}

        {state.kind !== "loading" && state.kind !== "unavailable" && state.limitations.length > 0 && (
          <ul className="mt-4 grid gap-1">
            {state.limitations.map((limit) => (
              <li key={limit} className="text-[0.7rem] leading-relaxed text-dim">
                {limit}
              </li>
            ))}
          </ul>
        )}

        {message && (
          <p role="status" aria-live="polite" className="mt-4 font-mono text-[0.62rem] text-amber">
            {message}
          </p>
        )}
      </div>

      <p className="caption mt-6">
        Adjacent Cinema · this page records your answer only. No account, email or location is
        requested, and your address is not stored.
      </p>
    </div>
  );
}
