# Lint policy and legacy debt (M13.6.10)

**Tool:** `ruff`, pinned to `0.17.0` via `[tool.ruff] required-version` in
`pyproject.toml` and installed at exactly that version in CI. Local and CI
results are therefore identical.

## The enforceable gate

```bash
ruff check .        # must exit 0 — this is the CI lint gate
```

Scope: the active production code and tests in `backend/` (plus the root
conftest). As of commit 46cb73a+M13.6.10 the gate is **clean** — 332 findings
in `backend/` were fixed mechanically (import order, whitespace, `datetime.UTC`,
`contextlib.suppress`, set/dict comprehensions, dummy-prefixed unused locals),
with two deliberate `# noqa: SIM102` annotations on nested migration guards in
`outcome_repository.py` where the nested form reads clearer.

## Tracked legacy debt (deliberately NOT mass-reformatted)

`research/` and `scripts/` are excluded from the gate via `extend-exclude` in
`pyproject.toml`. These are historical milestone artefacts; reformatting ~1.2k
lines would churn the research record for no behavioural gain.

Measured with ruff 0.17.0 on 2026-10-10 (explicit file list, because excluded
directories are skipped during discovery):

```bash
ruff check $(find research scripts -name '*.py' | sort) --statistics
```

| Scope | Findings | Auto-fixable |
|---|---|---|
| `research/` | 1,161 | ~1,030 |
| `scripts/` (M11-era live-run helpers) | 88 | 88 |
| **Total** | **1,249** | **1,110** |

Top rules: `W293` (843, blank-line whitespace), `F541` (135, empty f-strings),
`UP017` (42, `datetime.UTC`), `F401` (41, unused imports), `E402` (39,
intentional sys.path bootstraps), `W292` (28), `I001` (23).

**Policy:** any *new* file added under `research/` or `scripts/` should be
written lint-clean; existing files are only reformatted when they are already
being substantially edited. CI reports (never gates) the debt count so it
cannot grow silently.
