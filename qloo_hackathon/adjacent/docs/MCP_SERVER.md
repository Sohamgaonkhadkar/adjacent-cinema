# MCP server (optional, read-only)

`backend/app/mcp_server.py` exposes three tools over the Model Context Protocol
so an external agent can inspect the same analysis the website shows. It is a
**thin adapter**: every tool calls the existing runner, reader and domain
functions. It contains no scoring, ranking, counterfactual or evaluation logic of
its own, opens no socket, and stores nothing.

## Tools

| Tool | What it does | Provider calls |
| --- | --- | --- |
| `analyze_film_positioning(programme, city=None, mode="fixture")` | Runs the standard pipeline (identity resolution → expansion → cohort construction → ranking → Decision Challenge) and returns the top three cohorts, the rejections, the challenge summary, the pairwise comparison, the trace call ids and the bounded attribution record. **Fixture mode runs the labelled fixture programme**, echoes the submitted titles in `requested_programme` and says in `programme_note` that they were not analysed. | Fixture: none. Live: the run's normal budget. |
| `compare_film_groups(group_a, group_b, filter_type="urn:entity:movie", mode="fixture")` | One `/v2/analysis/compare` call between two groups of Qloo entity ids, read by the same reader the website uses (`app/domain/pairwise.py` semantics via `compare_entity_groups`). **The call is made and traced, but no metric is interpreted** until Qloo publishes a response schema: expect `metric: null` with `no_readable_field` (live) or `not_modelled_in_fixture` (fixture), plus the observed key names. | At most one compare call. |
| `get_evidence_report(run_id)` | Returns a run's full report unchanged: programme resolution, cohorts, challenge, pairwise, trace ids, limits. Reads runs created in this session, or completed runs from the Adjacent API when `ADJACENT_MCP_API_ORIGIN` is set. | At most one HTTP `GET` to the Adjacent API. |

Every payload opens with `"schema": "adjacent.mcp-tool-result/1"` and a
`status`. A status of `error`, `unavailable`, `no_readable_field` or
`not_modelled_in_fixture` means exactly that: nothing is inferred from a state
that produced no value.

## Safety properties

- **Fixture by default.** `mode` defaults to `fixture`. Live mode requires the
  operator to set `ADJACENT_MCP_ALLOW_LIVE=1` *and* a configured `QLOO_API_KEY`;
  otherwise the tool returns `unavailable` with the reason and no run id.
- **Bounded.** Live analyses are capped at `ADJACENT_MCP_MAX_LIVE_RUNS`
  (default 2) per server session, and fixture analyses at 10. The cap resets when
  the server restarts, because it is a per-process counter, not a licence.
- **Nothing private.** The tools read no experiment records, no guest sessions
  and no environment values. Provider errors are reported by type, never with
  the key or the full upstream payload.
- **A run id is an identifier, not a path.** `get_evidence_report` accepts 1–64
  letters, digits, hyphens or underscores and rejects `../`, slashes, spaces,
  percent-escapes and query strings before it builds a URL.
- **No fabrication.** A provider failure becomes `unavailable`/`failed`; a
  fixture run states that it is a fixture and that the submitted titles were not
  analysed. No tool invents a value, a cohort, an entity id or a success.
- **No public surface.** The transport is stdio. There is no listener, so there
  is no endpoint to expose, rate-limit or authenticate at the network layer.

## Running it

```bash
python -m pip install -e '.[mcp]'          # backend/ has the extra
PYTHONPATH=backend python -m app.mcp_server
```

Client configuration (placeholders, no real values):

```json
{
  "mcpServers": {
    "adjacent-cinema": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/qloo_hackathon/adjacent/backend",
        "ADJACENT_MCP_ALLOW_LIVE": "0"
      }
    }
  }
}
```

Optional environment variables: `ADJACENT_MCP_ALLOW_LIVE` (`0`/`1`),
`ADJACENT_MCP_MAX_LIVE_RUNS` (default `2`), `ADJACENT_MCP_API_ORIGIN` (base URL
used only by `get_evidence_report` for runs created elsewhere).

## Tests

```bash
python -m pytest backend/tests/test_mcp_server.py -q
```

The suite drives the server through the SDK's in-memory transport (`mcp` is an
optional dependency, so the module skips when it is absent) and asserts:

- the registry exposes exactly the three tool names, and the export names stay
  `[a-z][a-z0-9_]*` so the read-only surface cannot drift;
- a fixture analysis returns call ids, cohorts, the challenge summary and the
  limits while stating that the submitted titles were not analysed;
- a fixture comparison reports `not_modelled_in_fixture` with no metric;
- the `compare_film_groups` description served to a host model says no metric is
  interpreted, so an agent cannot build on a value that cannot exist;
- invalid programmes, entity ids, entity types, modes and run ids return
  `status: "error"` instead of raising;
- live mode without the operator flag, or without a key, returns `unavailable`
  and never falls back to a fixture;
- the session cap is enforced (the test resets the counter to the bound);
- `get_evidence_report` round-trips a session run byte-for-byte, and a run id
  that could address another resource is refused.

The suite does **not** exercise a live provider call: that needs a key this
repository does not hold, and is reported as unverified.
