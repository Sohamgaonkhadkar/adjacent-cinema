# M13.11 — Hackathon Eligibility Audit

Original audit: **2026-10-11**. Current rules rechecked: **2026-10-24**. Primary source: the official rules at
https://qloo.devpost.com/rules and the event page https://qloo.devpost.com/.

## 1. Official rules — relevant quotations (verbatim)

**Dates:** "Registration and Submission Period: September 30, 2026 (9:00 am Eastern
Time) – October 30, 2026 (11:45 pm Eastern Time)". Judging 2–16 Nov 2026; winners
on/around 23 Nov 2026.

**Project Requirements:** "Entrants must create a working software application that
integrates the Qloo API and that either (a) functions as an agentic tool, (b) is built
using an agent framework, or (c) integrates the Qloo API into an existing agent."

**New & Existing (verbatim as displayed on 24 October 2026):** “Projects must be either newly created by the Entrant or, if the Entrant’s Project existed prior to the Hackathon Submission Period, must have Qloo 4after the start of the Hackathon Submission Period. Entrants should explain how their Project was significantly updated during the Submission Period.”

The displayed phrase “Qloo 4after” is ambiguous. This report does not infer a missing word or determine eligibility from that phrase. Ask the organizers for written clarification if eligibility depends on its meaning.

**Submission requirements (for readiness tracking):** functional demo application link;
public repository on GitHub/GitLab/Bitbucket "with all necessary source code, assets,
and instructions"; "must be public and open source by including an open source license
file … detectable and visible at the top of the repository page"; text description of
features. API access is granted via a Google Form
(docs.qloo.com developer guide). Multiple submissions allowed if substantially different.

## 2. Historical Git evidence recorded on 2026-10-11 (not a current branch snapshot)

| Evidence | Value | Verified how |
|---|---|---|
| First commit in history | `ee7363e` "Initial commit", **2026-10-10 13:36:37 +0530 (= 08:06 UTC)** | `git log --date=iso` |
| Qloo integration present in first commit | yes — `qloo_hackathon/adjacent/backend/app/qloo/` first added in `ee7363e` | `git log --diff-filter=A -- .../app/qloo` → same timestamp |
| All subsequent commits | 2026-10-10 → 2026-10-11 (milestones M13.6.9 → M13.11, each with dated verification docs in `docs/`) | `git log` |
| Current HEAD | `d7c9e08` (M13.10) + M13.11 work (this commit) on branch `arena/6462c00a-adjacent-cinema` | `git log` |

## 3. Current status — no eligibility determination

**Eligibility is unconfirmed.** This audit does not decide whether the project qualifies, whether a prior version existed, or what the displayed “Qloo 4after” phrase means. The Git evidence below is limited to this repository's visible history and cannot establish the full project/entrant history or organizer interpretation.

**Organizer clarification needed; no message was sent from this workspace.** Suggested question:

> The current “New & Existing” rule reads: “Projects must be either newly created by the Entrant or, if the Entrant’s Project existed prior to the Hackathon Submission Period, must have Qloo 4after the start of the Hackathon Submission Period. Entrants should explain how their Project was significantly updated during the Submission Period.” Could you clarify the intended meaning of the literal phrase “Qloo 4after”? In particular, how should an entrant assess a project that existed before the Submission Period and whose Qloo integration also predates it? We will describe the project history and in-period changes factually; we do not want to assume a correction to the published wording.

The Entrant must separately confirm whether the project existed before the period and describe any significant in-period changes accurately. Do not replace the literal wording with an assumed correction or claim eligibility before the organizers/Entrant resolve the question.

## 4. Historical submission-readiness gaps recorded on 2026-10-11

The items below are a historical checklist from the original audit, not a current deployment/readiness finding. Re-check them against the current submission and hosted demo; this session did not verify hosted availability.

1. **Open-source license file: MISSING** at the repository root at audit time. An MIT
   `LICENSE` was added in this milestone as the conventional default — **the licence
   choice is the owner's decision and can be changed before submission.**
2. **Functional demo link:** requires deployment by the owner (the app currently runs
   locally: uvicorn :8000 + next :3000). Not verified in this environment.
3. **Repository visibility:** the remote's public/private status could not be checked
   (GitHub unreachable from this environment); the owner must confirm it is public with
   the licence visible in the About section.

---

## Re-verification (2026-10-24)

The official rules page (https://qloo.devpost.com/rules) was fetched again on
2026-10-24. The displayed “New & Existing” text still contains the literal
“Qloo 4after”; the exact quotation is recorded in section 1 above. The page
currently lists the submission deadline as **30 October 2026 at 11:45 pm EDT**
and requires a working application integrating Qloo, a functional demo link, a
public code repository with an open-source license, and a text description.

**No eligibility conclusion is made.** The entrant must seek organizer
clarification of “Qloo 4after” if relevant and confirm the project's prior
history. The existence of dated repository changes is not a substitute for
that clarification or owner confirmation.
