# Qloo API Setup — Adjacent

> **RUN ONLY AFTER THE QLOO API KEY IS RECEIVED**
>
> Every section below that touches a live Qloo endpoint requires a valid
> `QLOO_API_KEY`.  Without it, our probes exit with code 2 and write nothing.

---

## 1. Environment variables

Adjacent reads three Qloo-related env vars (all handled by `backend/app/config.py`):

| Variable | Default | Purpose |
|---|---|---|
| `QLOO_API_KEY` | *(none — mock mode when absent)* | Hackathon API key |
| `QLOO_BASE_URL` | `https://hackathon.api.qloo.com` | Primary Qloo endpoint |
| `QLOO_TRUSTED_BASE_URL` | `https://hackathon.api.qloo.com` | Trusted URL used by the official harness |

Create a local `.env` file (gitignored) in the repo root:

```
QLOO_API_KEY=<your-key-here>
QLOO_BASE_URL=https://hackathon.api.qloo.com
QLOO_TRUSTED_BASE_URL=https://hackathon.api.qloo.com
```

**Never commit the key.** The `.gitignore` excludes `.env` and `.env.*` (but allows `.env.example`).

### Verifying the mode

```bash
# From the repo root:
python3 -c "
import sys; sys.path.insert(0, 'backend')
from app.config import Settings
s = Settings.from_env()
print(s.redacted())
"
```

The output will include `"mode": "live"` when a key is present and `"mode": "mock"` otherwise.

---

## 2. Official Qloo harness (optional — additional validation only)

The official harness (`@qloo/qloo-harness`) is an independent sanity-check tool.
It does **not** replace our Python Qloo client.

### Install

```bash
npm install --global @qloo/qloo-harness
```

> **Note:** The harness requires Node.js ≥ 22.19.0.  If your sandbox has an
> older Node (e.g. 20.x), the harness will crash at runtime.

### Configure

```bash
export QLOO_BASE_URL=https://hackathon.api.qloo.com
export QLOO_TRUSTED_BASE_URL=https://hackathon.api.qloo.com
```

### Set up and verify

```bash
qloo setup --qloo
qloo setup --status
```

Expected success text:

```
Qloo data: ready
```

Ignore Model/Chat status — only Qloo data matters.

### Run the official kit (optional)

```bash
git clone https://github.com/qloo/qloo-hackathon-kit.git
cd qloo-hackathon-kit/starter/cli-workflow
qloo exec find_tags --input-file request.json
```

---

## 3. Adjacent live probes

### Dry-run (no key required)

```bash
make probe
```

Prints `Mode: dry-run (mock)` and writes `docs/api_probe_results.json` + `docs/API_NOTES.md`.

### Live verified

```bash
make probe-live
```

Requires `QLOO_API_KEY`.  Exits 2 if the key is missing.

### Live with unverified parameters

```bash
make probe-live-unverified
```

Same key requirement.  Also tests parameters not yet in official docs.

### What the probes test

| ID | Probe | Endpoint |
|---|---|---|
| A | External ID entity resolution | `GET /entities` |
| B | Programme → tag affinity (Taste DNA) | `GET /v2/insights` (urn:tag) |
| C | Cross-domain artist adjacency | `GET /v2/insights` (urn:entity:artist) |
| D | filter.results.entities completeness | `GET /v2/insights` (filter.results.entities) |
| E | Heatmap coverage (3 cities) | `GET /v2/insights` (urn:heatmap) |
| F | feature.explainability payload | `GET /v2/insights` (explainability) |
| G | Audience catalogue | `GET /v2/audiences` |
| H | Rate limit behaviour | 10 rapid calls |

---

## 4. Security reminders

- The key must **never** appear in source code, logs, traces, JSON, markdown, commits, or frontend assets.
- The `Settings.redacted()` method prints `qloo_api_key: "***set***"` — never the key itself.
- `key_fingerprint()` returns `sha256:<first-12-hex>·len=<n>` — sufficient to confirm identity without exposing material.
- The `/health` endpoint reports `mode` and `qloo_trusted_base_url` but never the key.