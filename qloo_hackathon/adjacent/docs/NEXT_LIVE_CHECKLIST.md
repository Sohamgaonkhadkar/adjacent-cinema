# Next: Live Qloo Integration Checklist

> **Status:** Pre-key preparation complete. Key now available.
>
> This checklist bridges from "key arrived" to "ready for product implementation."
> Each step has a clear pass/fail criterion.

---

## Step 1 — Add the key locally

```bash
# Create .env in the repo root (gitignored):
echo "QLOO_API_KEY=<your-key>" > .env
echo "QLOO_BASE_URL=https://hackathon.api.qloo.com" >> .env
echo "QLOO_TRUSTED_BASE_URL=https://hackathon.api.qloo.com" >> .env
chmod 600 .env
```

**Pass:** `python3 -c "import sys; sys.path.insert(0,'backend'); from app.config import Settings; s=Settings.from_env(); print(s.redacted())"` shows `"mode": "live"` and `"qloo_api_key": "***set***"`.

---

## Step 2 — Official harness setup (optional, requires Node ≥22.19)

```bash
export QLOO_BASE_URL=https://hackathon.api.qloo.com
export QLOO_TRUSTED_BASE_URL=https://hackathon.api.qloo.com
npm install --global @qloo/qloo-harness
qloo setup --qloo
qloo setup --status
```

**Pass:** `qloo setup --status` shows `Qloo data: ready`.

**Skip if:** Node version < 22.19. Our Python probes are the primary validation.

---

## Step 3 — Run live probes

```bash
make probe-live
```

**Pass:** Exit 0. Output shows `Mode: LIVE (real Qloo)` and all probes green:
- `[A] External ID entity resolution: N result(s)` — OK
- `[B] Programme → tag affinity (taste DNA): N result(s)` — OK
- `[C] Programme → artist cross-domain adjacency: N result(s)` — OK
- `[D] filter.results.entities completeness: N result(s)` — OK
- `[E] Heatmap coverage by city: N result(s)` — OK
- `[F] feature.explainability payload` — OK
- `[G] Audience catalogue: N result(s)` — OK
- `[H] Rate limit behaviour` — OK

---

## Step 4 — Run unverified probes

```bash
make probe-live-unverified
```

**Pass:** Same as above, plus:
- `[B2] Taste DNA with filter.parents.types` — OK
- `[C2] Artist adjacency with signal.location.query` — OK
- `[G2] filter.tags` — expected to fail (not supported)

---

## Step 5 — Verify filter.results.entities

**Pass (already confirmed in live testing):**
- 50 candidates supplied → 50 returned → 50 scored
- Verdict: **SAFE** — rank all candidate cohorts in a single query

---

## Step 6 — Verify heatmap coverage

**Pass (already confirmed):**

| City | Cells | Status |
|---|---|---|
| London, UK | 207 | ✅ Usable |
| New York, NY | 203 | ✅ Usable |
| Portland, Oregon | 19 | ✅ Usable (but sparse) |

---

## Step 7 — Verify explainability

**Pass (already confirmed):**
- `feature.explainability=true` adds `entity.query.explainability.signal.interests.entities[]`
- Per-signal-entity attribution scores sum ≈ affinity
- Tags do NOT receive explainability

---

## Step 8 — Lock demo city

**Recommendation:** London, UK (207 cells — highest density).

Portland has only 19 cells, which is too sparse for a compelling geographic demo.

**Pass:** A city is locked when:
- Heatmap returns ≥ 10 cells
- Cells span a meaningful geographic area
- At least one venue/cohort in that city is identified

---

## Step 9 — Run full test suite

```bash
python -m pytest -q
python -m ruff check .
```

**Pass:** All tests green, ruff clean.

---

## Step 10 — Continue to product implementation

With live Qloo evidence confirmed, the next milestone is:
- Wire the deterministic pipeline to use real Qloo (not mock)
- Implement the Taste DNA output
- Implement ranked adjacent cohorts
- Implement heatmap + geographic rings
- Build the Programme Bet from ranked cohorts
- Build the frontend against the response contract

**Do NOT proceed until steps 1–9 pass.**