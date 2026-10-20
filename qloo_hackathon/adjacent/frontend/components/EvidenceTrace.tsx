import type { TraceRow } from "@/types/adjacent";

const sensitiveParameterName = /(?:^key$|api.?key|authorization|\bauth\b|token|secret|password|credential)/i;

function safeAnchorPart(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}

export function traceAnchorId(callId: string, scope?: string): string {
  const prefix = scope ? `${safeAnchorPart(scope)}-` : "";
  return `${prefix}evidence-trace-${safeAnchorPart(callId)}`;
}

function redactParameterValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactParameterValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, nested]) => [
        key,
        sensitiveParameterName.test(key) ? "***REDACTED***" : redactParameterValue(nested),
      ])
    );
  }
  return value;
}

function sourceLabel(source: string | undefined): string {
  if (source === "qloo") return "QLOO";
  if (source === "mock") return "MOCK";
  return "SOURCE UNKNOWN";
}

function dataStatusLabel(status: string | undefined): string {
  if (status === "measured") return "MEASURED";
  if (status === "fixture") return "FIXTURE";
  return "STATUS UNKNOWN";
}

function TraceRowDetails({ row, scope }: { row: TraceRow; scope?: string }) {
  const params = redactParameterValue(row.params ?? {}) as Record<string, unknown>;
  const parameterEntries = Object.entries(params);
  const countLabel =
    row.result_count != null
      ? `${row.result_count} returned`
      : row.error
        ? "error recorded · count unavailable"
        : "count not reported";
  const statusLabel =
    row.status != null
      ? `HTTP ${row.status}`
      : row.error
        ? "No HTTP response · failure recorded"
        : "HTTP status not reported";
  const entryKind = row.tool === "build_and_rank_cohorts" ? "Logical operation" : "Recorded call";

  return (
    <li>
      <details className="evidence-trace-row" id={traceAnchorId(row.call_id, scope)}>
        <summary>
          <span className="evidence-trace-id">{row.call_id}</span>
          <span className="evidence-trace-tool">{row.tool || "Tool not reported"}</span>
          <span className="evidence-trace-status">
            {sourceLabel(row.source)} · {dataStatusLabel(row.data_status)}
          </span>
          <span className="evidence-trace-count">{countLabel}</span>
        </summary>
        <div className="evidence-trace-body">
          <dl>
            <div><dt>Entry kind</dt><dd>{entryKind}</dd></div>
            <div><dt>Endpoint</dt><dd>{row.method || "GET"} {row.endpoint || "not reported"}</dd></div>
            <div><dt>HTTP status</dt><dd>{statusLabel}</dd></div>
            <div>
              <dt>Returned records</dt>
              <dd>{row.result_count != null ? row.result_count : "Not reported"}</dd>
            </div>
            <div>
              <dt>Duration</dt>
              <dd>{row.duration_ms != null ? `${row.duration_ms} ms` : "Not reported"}</dd>
            </div>
            <div><dt>Cache</dt><dd>{row.cache || "Not reported"}</dd></div>
            <div><dt>Attempt</dt><dd>{row.attempt ?? "Not reported"}</dd></div>
            {row.backfill_detected && <div><dt>Backfill</dt><dd>Detected</dd></div>}
          </dl>

          {row.error && (
            <p className="evidence-trace-error">
              A failure was recorded. Provider error details are not repeated in this redacted view.
            </p>
          )}

          {parameterEntries.length > 0 && (
            <details className="evidence-trace-params">
              <summary>Request parameters · redacted before display</summary>
              <pre>{JSON.stringify(params, null, 2)}</pre>
            </details>
          )}

          {(row.notes?.length ?? 0) > 0 && (
            <details className="evidence-trace-notes">
              <summary>Trace notes ({row.notes?.length})</summary>
              <ul>{row.notes?.map((note, index) => <li key={index}>{note}</li>)}</ul>
            </details>
          )}
        </div>
      </details>
    </li>
  );
}

export function EvidenceReferences({
  refs,
  traceRows,
  scope,
  availability,
}: {
  refs: string[];
  traceRows: TraceRow[];
  scope?: string;
  availability?: "loading" | "unavailable";
}) {
  if (refs.length === 0) return null;

  return (
    <span className="evidence-trace-references">
      {refs.map((callId, index) => {
        const isRecorded = traceRows.some((row) => row.call_id === callId);
        const traceState = availability === "loading"
          ? "trace loading"
          : availability === "unavailable"
            ? "trace unavailable"
            : "trace not linked";
        return isRecorded ? (
          <a
            key={`${callId}-${index}`}
            href={`#${traceAnchorId(callId, scope)}`}
            aria-label={`Open recorded evidence trace ${callId}`}
          >
            {callId}
          </a>
        ) : (
          <span
            key={`${callId}-${index}`}
            className="evidence-trace-unresolved"
            title={availability === "loading"
              ? "The source run trace is still loading."
              : availability === "unavailable"
                ? "The source run trace could not be retrieved."
                : "No matching trace entry was included in this run response."}
          >
            {callId} · {traceState}
          </span>
        );
      })}
    </span>
  );
}

export function EvidenceTraceLog({ rows, scope }: { rows: TraceRow[]; scope?: string }) {
  const headingId = `evidence-trace-heading-${scope ? safeAnchorPart(scope) : "current"}`;
  return (
    <section className="evidence-trace-log" aria-labelledby={headingId}>
      <div className="evidence-trace-log-heading">
        <div>
          <span className="micro-label">PROVENANCE · THIS RUN ONLY</span>
          <h4 id={headingId}>Recorded evidence trace</h4>
        </div>
        <span className="mono-note">{rows.length} {rows.length === 1 ? "ENTRY" : "ENTRIES"}</span>
      </div>
      <p className="evidence-trace-intro">
        The trace distinguishes recorded calls from logical operations. Source, fixture/live status,
        returned-record counts (including zero), and server-redacted request parameters are shown as recorded.
      </p>
      {rows.length > 0 ? (
        <ol className="evidence-trace-list">
          {rows.map((row, index) => <TraceRowDetails key={`${row.call_id}-${index}`} row={row} scope={scope} />)}
        </ol>
      ) : (
        <p className="evidence-trace-empty" role="status">
          No trace entries were included in this response. Evidence references above remain identifiers;
          their source cannot be inspected from this run response.
        </p>
      )}
    </section>
  );
}
