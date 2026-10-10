# ADR-002: Qloo Integration Boundary

## Status

FROZEN (with one correction from live testing)

## Date

4 October 2026 (research) / 6 October 2026 (freeze)

## Decision

One client (`qloo/client.py`), allowlisted parameters (`params.py`), GET-only, `X-Api-Key` header, every response → TraceRow.

**CORRECTION from live testing:** Entity resolution uses `/search` as primary (not `/entities` with external IDs), because Qloo does not return external IDs in the `/entities` response, making verification impossible.

## Rationale

1. **Single point of control.** No httpx import outside `qloo/client.py`. Every Qloo call is auditable.
2. **Allowlisted parameters.** Unknown parameters raise before the request. This is how "silently ignored parameters" stop being silent.
3. **GET only.** POST-with-body is rejected by the API despite the docs.
4. **404 = data outcome.** Not an error. Flows into the unresolved list.
5. **Trace rows.** Every call produces a TraceRow for the Evidence Panel.

## Live Testing Correction

The architecture research claimed `/entities` with external IMDb IDs "kills ~80% of entity-resolution risk." Live testing proved this is UNSAFE: Qloo returns entities but doesn't include the external IDs in the response, making it impossible to verify which input mapped to which entity.

**Correct implementation:** `/search` with title+year verification is the primary path. `/entities` with external IDs is supplementary, only used if the external ID is confirmed in the response.

## Alternative Considered

- Multiple Qloo clients (one per endpoint) — rejected: violates single-point-of-control
- Direct httpx calls from tools — rejected: bypasses allowlist and trace

## Consequence

- All Qloo integration changes happen in one package
- Parameter changes require updating the allowlist (explicit, auditable)
- Response parser changes require updating models.py (typed, testable)

## Trigger to Revisit

If Qloo adds a new endpoint that requires POST, or if the allowlist becomes too restrictive.