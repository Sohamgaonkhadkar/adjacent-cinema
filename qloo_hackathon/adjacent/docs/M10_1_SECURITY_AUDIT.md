# M10.1: Security Audit — API Key Exposure

**Date:** 2026-10-06
**Status:** DOCUMENTED — KEY ROTATION REQUIRED

---

## Executive Summary

The Qloo API key was hardcoded in source code and committed to Git history. The key has been removed from the working tree but remains in Git history. **The key must be treated as compromised and rotated/revoked.**

---

## Key Exposure Timeline

| Commit | Date | Action |
|--------|------|--------|
| `72d2a01` | 2026-10-06 | Key committed in `research/scripts/qloo_validation.py` |
| `e9082e2` | 2026-10-06 | Key removed from working tree (M10) |
| Current | 2026-10-06 | Key still in Git history |

---

## Current Status

### Working Tree
- ✅ No tracked files contain the key
- ✅ `.env` is in `.gitignore`
- ✅ Scripts load key from environment variable only

### Git History
- ❌ Key exists in commit `72d2a01`
- ❌ Key exists in commit `e9082e2` (in M10_DATA_INTEGRITY_REPORT.md as example)
- ❌ Key cannot be removed from history without force-pushing

---

## Required Actions

### Immediate (M10.1)

1. **Document exposure** — ✅ DONE (this file)
2. **Remove key from working tree** — ✅ DONE
3. **Verify no current files contain key** — ✅ DONE

### Required (Before Production)

1. **Rotate/Revoke the credential**
   - Contact Qloo to revoke the exposed key
   - Generate a new API key
   - Store new key in secure environment only
   - **Status:** PENDING — requires Qloo action

2. **Verify new credential is secure**
   - New key must be in environment variable only
   - New key must not be committed to Git
   - New key must not be printed in logs/reports
   - **Status:** PENDING — awaiting new key

3. **Consider Git history cleanup**
   - Option A: Force-push to remove key from history (destructive)
   - Option B: Accept key is in history, ensure it's revoked
   - **Recommendation:** Option B — revoke key, don't force-push

---

## Evidence

### Commit 72d2a01

```
research/scripts/qloo_validation.py:
QLOO_API_KEY = '<REDACTED - was hardcoded key>'
```

### Commit e9082e2

```
docs/M10_DATA_INTEGRITY_REPORT.md:
QLOO_API_KEY = '<REDACTED - was hardcoded key>'
```

### Current Working Tree

```
$ grep -r "hack_383" . --include="*.py" --include="*.md"
(no results)
```

---

## Security Recommendations

### For This Project

1. **Never hardcode API keys** — always use environment variables
2. **Add pre-commit hook** to scan for key patterns
3. **Use `.env.example`** to document required variables
4. **Never print keys** in logs, reports, or diffs

### For Git History

1. **Accept the exposure** — key is in history
2. **Revoke the key** — invalidate the compromised credential
3. **Generate new key** — store in secure environment only
4. **Document the incident** — for future reference

---

## Conclusion

**Status:** The API key `hack_383...` was committed to Git history in commit `72d2a01`. The key has been removed from the working tree but remains in Git history.

**Required Action:** Rotate/revoke the credential. Do not claim security is resolved until the credential itself has been rotated/revoked.

**Recommendation:** Contact Qloo to revoke the exposed key and generate a new one. Store the new key in the secure environment only.

**SECURITY_STATUS = BLOCKED_PENDING_CREDENTIAL_ROTATION**

Credential rotation cannot be performed from this environment. The exposed credential must be treated as compromised until Qloo performs rotation/revocation.

---

**Report Generated:** 2026-10-06
**Status:** BLOCKED_PENDING_CREDENTIAL_ROTATION