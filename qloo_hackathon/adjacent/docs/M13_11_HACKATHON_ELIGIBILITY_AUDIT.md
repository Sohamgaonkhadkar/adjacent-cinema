# M13.11 — Hackathon Eligibility Audit

Audit date: **2026-10-11**. Primary source: the official rules at
https://qloo.devpost.com/rules (fetched this session) and the event page
https://qloo.devpost.com/.

## 1. Official rules — relevant quotations (verbatim)

**Dates:** "Registration and Submission Period: September 30, 2026 (9:00 am Eastern
Time) – October 30, 2026 (11:45 pm Eastern Time)". Judging 2–16 Nov 2026; winners
on/around 23 Nov 2026.

**Project Requirements:** "Entrants must create a working software application that
integrates the Qloo API and that either (a) functions as an agentic tool, (b) is built
using an agent framework, or (c) integrates the Qloo API into an existing agent."

**New & Existing:** "Projects must be either newly created by the Entrant or, if the
Entrant's Project existed prior to the Hackathon Submission Period, must have Qloo
after the start of the Hackathon Submission Period. Entrants should explain how their
Project was significantly updated during the Submission Period."
*(Note: the official text contains an apparent typo — a verb such as "added/integrated"
is missing after "must have Qloo". Read in context, the clause requires the Qloo
integration to post-date 2026-09-30 for pre-existing projects.)*

**Submission requirements (for readiness tracking):** functional demo application link;
public repository on GitHub/GitLab/Bitbucket "with all necessary source code, assets,
and instructions"; "must be public and open source by including an open source license
file … detectable and visible at the top of the repository page"; text description of
features. API access is granted via a Google Form
(docs.qloo.com developer guide). Multiple submissions allowed if substantially different.

## 2. Git evidence examined (this repository)

| Evidence | Value | Verified how |
|---|---|---|
| First commit in history | `ee7363e` "Initial commit", **2026-10-10 13:36:37 +0530 (= 08:06 UTC)** | `git log --date=iso` |
| Qloo integration present in first commit | yes — `qloo_hackathon/adjacent/backend/app/qloo/` first added in `ee7363e` | `git log --diff-filter=A -- .../app/qloo` → same timestamp |
| All subsequent commits | 2026-10-10 → 2026-10-11 (milestones M13.6.9 → M13.11, each with dated verification docs in `docs/`) | `git log` |
| Current HEAD | `d7c9e08` (M13.10) + M13.11 work (this commit) on branch `arena/6462c00a-adjacent-cinema` | `git log` |

## 3. Conclusion

**ELIGIBLE — conditional on one owner confirmation.**

- The repository's entire documented history begins **2026-10-10**, inside the
  Registration & Submission Period (started 2026-09-30). Qloo integration exists from
  the very first commit. On the available evidence the project is "newly created by the
  Entrant" within the period.
- The project also satisfies the Project Requirement as **(a) an agentic tool**: a
  typed-tool orchestrator (PLAN→SELECT→ACT→EVALUATE→STOP, `backend/app/agent/`) drives
  real Qloo operations; M13.11 adds the structured cultural-investigation layer on top.

**Uncertainty (stated honestly):** the history starts with a single squashed
"Initial commit" created by the development environment. Git alone therefore cannot
prove that no earlier version of this project existed elsewhere before 2026-09-30.
Only the Entrant knows this. If a pre-existing version did exist, the fallback clause
still appears strongly supported (Qloo work and substantial functionality — the entire
documented milestone chain with verification reports — post-dates the period start),
and the rules ask the Entrant to "explain how their Project was significantly updated
during the Submission Period", for which `docs/` provides dated evidence.

**Next action needed:** the Entrant (repository owner) should (1) confirm whether any
prior public/private version existed before 2026-09-30, and (2) if there is any doubt,
request written clarification from the organisers via Devpost before submitting.

## 4. Submission-readiness gaps found during this audit

1. **Open-source license file: MISSING** at the repository root at audit time. An MIT
   `LICENSE` was added in this milestone as the conventional default — **the licence
   choice is the owner's decision and can be changed before submission.**
2. **Functional demo link:** requires deployment by the owner (the app currently runs
   locally: uvicorn :8000 + next :3000). Not verified in this environment.
3. **Repository visibility:** the remote's public/private status could not be checked
   (GitHub unreachable from this environment); the owner must confirm it is public with
   the licence visible in the About section.

---

## Re-verification (2026-10-14)

The official rules page (https://qloo.devpost.com/rules) was re-fetched on
2026-10-14. No material changes since the original audit:

- Registration & Submission Period unchanged: **September 30, 2026 9:00 am
  ET – October 30, 2026 11:45 pm ET**; Judging Nov 2–16; winners ~Nov 23.
- The "New & Existing" clause text is unchanged (still renders with a
  garbled verb: "must have Qloo 4after the start of the Hackathon Submission
  Period"), followed by: "Entrants should explain how their Project was
  significantly updated during the Submission Period."
- Submission requirements unchanged (functional demo link, public OSS repo
  with license visible at top, text description).

**Conclusion stands: ELIGIBLE — conditional on the same single owner
confirmation** (whether any version of the project existed before
2026-09-30). The documented milestone chain (2026-10-10 through 2026-10-11,
M1–M13.14 with dated verification reports in `docs/`) continues to provide
the "significantly updated during the Submission Period" evidence the rules
request. 16 days remain until the submission deadline as of this
re-verification.
