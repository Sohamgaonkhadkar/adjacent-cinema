export type RunRecoveryRecord = { status: string };
export type RunStreamEvent = { event: string; data?: unknown };

type RecoveryOptions<T extends RunRecoveryRecord> = {
  isCurrent: () => boolean;
  fetchRun: (runId: string) => Promise<T>;
  onRun: (run: T) => void;
  onExhausted: () => void;
  delaysMs?: number[];
  schedule?: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>;
  cancel?: (timer: ReturnType<typeof setTimeout>) => void;
};

type WatchOptions<T extends RunRecoveryRecord, E extends RunStreamEvent> = RecoveryOptions<T> & {
  stream: (runId: string, onEvent: (event: E) => void, onError: (error: Error) => void) => () => void;
  onEvent: (event: E) => void;
};

const TERMINAL_STATUSES = new Set(["completed", "failed", "insufficient"]);
const TERMINAL_EVENTS = new Set(["done", "error", "insufficiency"]);
const DEFAULT_DELAYS_MS = [250, 500, 1000, 2000, 4000, 5000];

/** Reconcile once immediately, then poll a bounded backoff until terminal. */
export function startRunStatusRecovery<T extends RunRecoveryRecord>(
  runId: string,
  options: RecoveryOptions<T>,
): () => void {
  const schedule = options.schedule ?? setTimeout;
  const cancel = options.cancel ?? clearTimeout;
  const delays = options.delaysMs ?? DEFAULT_DELAYS_MS;
  let stopped = false;
  let inFlight = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let retriesScheduled = 0;

  const stop = () => {
    stopped = true;
    if (timer !== null) {
      cancel(timer);
      timer = null;
    }
  };

  const poll = async () => {
    if (stopped || inFlight || !options.isCurrent()) return;
    inFlight = true;
    let response: T | null = null;
    try {
      response = await options.fetchRun(runId);
    } catch {
      // A transient status-endpoint failure gets the same bounded retry path.
    } finally {
      inFlight = false;
    }

    if (stopped || !options.isCurrent()) return;
    if (response) {
      options.onRun(response);
      if (TERMINAL_STATUSES.has(response.status)) {
        stop();
        return;
      }
    }

    if (retriesScheduled >= delays.length) {
      options.onExhausted();
      stop();
      return;
    }
    const delay = delays[retriesScheduled++];
    timer = schedule(() => {
      timer = null;
      void poll();
    }, delay);
  };

  void poll();
  return stop;
}

/** Own the SSE connection and all status reconciliation for one run. */
export function watchRunWithRecovery<
  T extends RunRecoveryRecord,
  E extends RunStreamEvent,
>(runId: string, options: WatchOptions<T, E>): () => void {
  let stopped = false;
  let streamStop: (() => void) | null = null;
  let recoveryStop: (() => void) | null = null;
  const isCurrent = () => !stopped && options.isCurrent();

  const stopStream = () => {
    streamStop?.();
    streamStop = null;
  };
  const stopRecovery = () => {
    recoveryStop?.();
    recoveryStop = null;
  };
  const reconcile = () => {
    if (!isCurrent()) return;
    stopRecovery();
    recoveryStop = startRunStatusRecovery(runId, {
      ...options,
      isCurrent,
      onRun: (run) => {
        if (!isCurrent()) return;
        options.onRun(run);
        if (TERMINAL_STATUSES.has(run.status)) {
          stopRecovery();
          stopStream();
        }
      },
    });
  };

  streamStop = options.stream(
    runId,
    (event) => {
      if (!isCurrent()) return;
      options.onEvent(event);
      if (TERMINAL_EVENTS.has(event.event)) reconcile();
    },
    () => reconcile(),
  );

  return () => {
    stopped = true;
    stopRecovery();
    stopStream();
  };
}
