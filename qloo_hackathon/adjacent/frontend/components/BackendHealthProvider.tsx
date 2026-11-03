"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  waitForBackendReady,
  type BackendHealth,
} from "@/lib/api";

type WakeState = "waking" | "ready" | "unavailable";

type BackendHealthContextValue = {
  backendHealth: BackendHealth | null;
  wakeState: WakeState;
  wakeAttempts: number;
  wakeError: string | null;
  ensureReady: () => Promise<BackendHealth>;
};

const BackendHealthContext = createContext<BackendHealthContextValue | null>(null);
const FAILED_WAKE_RETRY_MS = 15_000;

export function BackendHealthProvider({ children }: { children: ReactNode }) {
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [wakeState, setWakeState] = useState<WakeState>("waking");
  const [wakeAttempts, setWakeAttempts] = useState(0);
  const [wakeError, setWakeError] = useState<string | null>(null);
  const inFlight = useRef<Promise<BackendHealth> | null>(null);

  const ensureReady = useCallback((): Promise<BackendHealth> => {
    if (inFlight.current) return inFlight.current;

    setWakeState("waking");
    setWakeError(null);
    setBackendHealth(null);
    setWakeAttempts(0);

    // The browser's GET /api/health request is the wake-up signal. Give a
    // sleeping Render Free instance a longer window to become available.
    const pending = waitForBackendReady({
      maxWaitMs: 300_000,
      requestTimeoutMs: 30_000,
      retryDelayMs: 5_000,
      onAttempt: setWakeAttempts,
    });
    inFlight.current = pending;

    void pending
      .then((health) => {
        setBackendHealth(health);
        setWakeState("ready");
        setWakeError(null);
      })
      .catch((reason: unknown) => {
        const message =
          reason instanceof Error ? reason.message : "Could not connect to the analysis backend.";
        setBackendHealth(null);
        setWakeError(message);
        setWakeState("unavailable");
      })
      .finally(() => {
        if (inFlight.current === pending) inFlight.current = null;
      });

    return pending;
  }, []);

  // Start the backend from the user's browser as soon as the frontend loads.
  useEffect(() => {
    void ensureReady().catch(() => undefined);
  }, [ensureReady]);

  // A bounded attempt must not become a permanent failure state. Retry from
  // this frontend tab until the backend responds or the tab is closed.
  useEffect(() => {
    if (wakeState !== "unavailable") return;

    const retry = window.setTimeout(() => {
      void ensureReady().catch(() => undefined);
    }, FAILED_WAKE_RETRY_MS);

    return () => window.clearTimeout(retry);
  }, [wakeState, ensureReady]);

  // If this tab was left open while Render went idle, re-check on return.
  useEffect(() => {
    const recheckOnReturn = () => {
      if (document.visibilityState !== "visible" || wakeState === "waking") return;
      void ensureReady().catch(() => undefined);
    };

    window.addEventListener("focus", recheckOnReturn);
    document.addEventListener("visibilitychange", recheckOnReturn);
    return () => {
      window.removeEventListener("focus", recheckOnReturn);
      document.removeEventListener("visibilitychange", recheckOnReturn);
    };
  }, [wakeState, ensureReady]);

  const value = useMemo(
    () => ({ backendHealth, wakeState, wakeAttempts, wakeError, ensureReady }),
    [backendHealth, wakeState, wakeAttempts, wakeError, ensureReady],
  );

  return (
    <BackendHealthContext.Provider value={value}>
      {children}
      {wakeState === "waking" && (
        <div
          className="fixed bottom-4 right-4 z-[100] max-w-sm border border-amber/30 bg-ink/95 px-4 py-3 text-paper shadow-xl backdrop-blur"
          role="status"
          aria-live="polite"
        >
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-amber">
            Connecting to analysis engine
          </p>
          <p className="mt-1 text-xs leading-relaxed text-paper-2">
            The backend may be asleep. This page is trying to start it · attempt {wakeAttempts}.
          </p>
        </div>
      )}
      {wakeState === "unavailable" && (
        <div
          className="fixed bottom-4 right-4 z-[100] max-w-sm border border-amber/40 bg-ink/95 px-4 py-3 text-paper shadow-xl backdrop-blur"
          role="alert"
        >
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-amber">
            Analysis engine still starting
          </p>
          <p className="mt-1 text-xs leading-relaxed text-paper-2">
            {wakeError} The page will automatically retry in 15 seconds. Keep this tab open, or retry now.
          </p>
          <button
            type="button"
            onClick={() => void ensureReady().catch(() => undefined)}
            className="mt-3 border border-amber/50 px-3 py-1.5 font-mono text-[0.62rem] uppercase tracking-[0.12em] text-amber transition-colors hover:bg-amber/10"
          >
            Retry connection
          </button>
        </div>
      )}
    </BackendHealthContext.Provider>
  );
}

export function useBackendHealth(): BackendHealthContextValue {
  const value = useContext(BackendHealthContext);
  if (!value) {
    throw new Error("useBackendHealth must be used inside BackendHealthProvider.");
  }
  return value;
}
