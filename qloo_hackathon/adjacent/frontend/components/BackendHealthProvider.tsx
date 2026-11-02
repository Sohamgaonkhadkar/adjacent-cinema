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

    const pending = waitForBackendReady({
      onAttempt: setWakeAttempts,
    })
      .then((health) => {
        setBackendHealth(health);
        setWakeState("ready");
        setWakeError(null);
        return health;
      })
      .catch((reason: unknown) => {
        const message =
          reason instanceof Error ? reason.message : "Could not connect to the analysis backend.";
        setBackendHealth(null);
        setWakeError(message);
        setWakeState("unavailable");
        throw reason;
      })
      .finally(() => {
        if (inFlight.current === pending) inFlight.current = null;
      });

    inFlight.current = pending;
    return pending;
  }, []);

  useEffect(() => {
    void ensureReady().catch(() => undefined);
  }, [ensureReady]);

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
            The service may need a moment to start after inactivity. Checking connection · attempt {wakeAttempts}.
          </p>
        </div>
      )}
      {wakeState === "unavailable" && (
        <div
          className="fixed bottom-4 right-4 z-[100] max-w-sm border border-amber/40 bg-ink/95 px-4 py-3 text-paper shadow-xl backdrop-blur"
          role="alert"
        >
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-amber">
            Analysis engine unavailable
          </p>
          <p className="mt-1 text-xs leading-relaxed text-paper-2">{wakeError}</p>
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
