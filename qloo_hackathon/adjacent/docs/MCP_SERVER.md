# MCP server — three read-only tools over the existing pipeline

`backend/app/mcp_server.py` exposes Adjacent's own analysis to an MCP client
(an agent host). It is an **adapter**, not a second product:

- every tool calls the same runner, the same Qloo reader and the same domain
  functions the website calls;
- there is no second ranker, no second scorer and no scoring arithmetic in
  `mcp_server.py`;
- running a tool changes nothing that a later website request would read.

## Tools

| Tool | What it does | Provider calls |
|---|---|---|
| `analyze_film_positioning` | Runs the existing analysis for up to five film references and returns the ranked cohorts, the counterfactual summary, the data status, the limits and the trace call ids. | Fixture mode: none. Live mode: the normal live pipeline, at most twice per server session. |
| `compare_film_groups` | One `/v2/analysis/compare` call between two groups of resolved Qloo entity ids, read by the same reader the website uses. | One compare call. |
| `get_evidence_report` | Returns a completed run's result, evidence, limits and provenance without changing its decision. Reads runs created in this MCP session, or completed runs from the Adjacent API when `ADJACENT_MCP_API_ORIGIN` is set. | At most one HTTP GET to the Adjacent API. |

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
- **No fabrication.** A provider failure becomes `unavailable`/`failed`; a
  fixture run states that it is a fixture and that the submitted titles were not
  the ones analysed.
- **stdio only.** `python -m app.mcp_server` runs the SDK's stdio transport. No
  listener is opened, so there is no public endpoint and no origin policy to
  get wrong.

## Install and run

The SDK is an optional extra so the web API never depends on it:

```bash
cd qloo_hackathon/adjacent
python -m pip install -e '.[dev,mcp]'
PYTHONPATH=backend python -m app.mcp_server
```

A client configuration (placeholders only — no real paths or keys):

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

To read completed runs from a running API, add
`"ADJACENT_MCP_API_ORIGIN": "http://127.0.0.1:8000"` (or the origin the API is
actually served from). Without it, `get_evidence_report` only sees runs created
in the same MCP session, and says so.

## Tests

```bash
python -m pytest backend/tests/test_mcp_server.py -q
```

The suite covers the registry (exactly three read-oriented tools), the input
validation, the fixture labelling, the live refusal without the operator flag,
the session caps, the API-unreachable path, and one real client↔server round
trip over the SDK's in-memory streams — so the tools are proven reachable
through the protocol, not merely importable. If the SDK is not installed the
module skips rather than failing, and CI installs it so the suite actually runs.

## What this is not

It is not an "agentic" layer: no tool decides anything, ranks anything or
narrates a conclusion. It returns the evidence the website already computes, in
a form an agent host can read, with the same limits attached.
