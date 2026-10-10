# Applying the Adjacent M13.6.5 patch

**Patch base:** Git HEAD `9ce72640097d1b557f4871132706cb8da4f38f40` (M13.6 source ZIP).

This bundle contains only the changed/new code, tests, script, and frontend README. It deliberately excludes the database, `.env`, Git history, dependencies, and generated artifacts.

## Important version note

The Arena transcript describes a later M13.6.4 state at commit `8a0c527`, but that commit was not present in the source ZIP available for this patch. Do **not** blindly overwrite a newer workspace with this patch. Reconcile the corresponding files onto the current branch, preserve the M13.6.4 read-only audit and empty-feature recollection fix, then re-run all tests and the audit against the current database.

## Apply and verify

From the repository root matching the patch base, first test applicability:

```bash
git apply --check Adjacent_M13_6_5_Code_Patch_2026-10-09.patch
```

Then apply:

```bash
git apply Adjacent_M13_6_5_Code_Patch_2026-10-09.patch
```

Verify backend changes:

```bash
python -m pytest -o addopts='' backend/tests -q --tb=short -k 'not test_live_search_resolves_known_films and not test_live_filter_results_entities_contract and not test_live_explainability_provenance'
python -m py_compile backend/app/domain/qloo_signal.py backend/app/domain/outcome_repository.py backend/app/api/routes.py research/scripts/m13_5_canonicalize.py research/scripts/m13_6_prospective.py research/scripts/m13_6_5_integrity_audit.py
python research/scripts/m13_6_5_integrity_audit.py --db data/processed/outcome_ledger.db --json-out /tmp/m13_6_5_integrity_audit.json
```

The verification recorded for the isolated source copy is 431 passed, 4 skipped, 3 deselected. Three Qloo-dependent tests could not reach the external API due to DNS/network restrictions. The frontend build/typecheck remains unverified because dependency installation was unavailable offline.

## Secret hygiene

The uploaded source archive included an ignored `.env` with a non-empty Qloo key. This patch omits it. If that archive was sent or uploaded to any untrusted/shared destination, revoke/rotate the key and ensure `.env` is excluded from all source bundles.
