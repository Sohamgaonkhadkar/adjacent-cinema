# ADR-003: PostgreSQL Cache (Not Redis)

## Status

FROZEN

## Date

4 October 2026

## Decision

Use a PostgreSQL table with TTL for Qloo response caching. Not Redis.

## Rationale

1. **One fewer service.** No Redis deployment, no Redis credentials, no Redis monitoring.
2. **Inspectable.** A judge can query the cache table and see hit/miss rates.
3. **Sufficient.** The hackathon workload is ~5 runs/hour, not 500 rps.
4. **Same database.** The runs table already needs PostgreSQL.

## Alternative Considered

Redis. Also considered in-memory dict (no persistence across restarts).

## Why Rejected

- Redis: adds deployment complexity, another credential, another service to monitor. Worthwhile only past ~5 rps.
- In-memory: lost on restart; demo fixtures would need re-warming.

## Consequence

- Cache key = `sha256(method + path + sorted(params))`
- TTLs vary by endpoint: /entities 7d, /search 24h, /v2/insights 12h, heatmap 6h
- Cache hits are visible in the trace (provenance requirement)

## Trigger to Revisit

If response times become unacceptable (>2s per run) or if the hackathon workload exceeds ~20 runs/hour.