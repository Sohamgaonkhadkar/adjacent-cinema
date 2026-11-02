# Adjacent Cinema — evidence-based positioning (2 November 2026)

**Status:** Post-submission communication/research note, **not** a modification of the judged Devpost application or a walkthrough-video document. The submitted main branch and deployed interface should remain unchanged during judging.

## One sentence

**Adjacent Cinema uses Qloo-powered cultural intelligence to help independent filmmakers and cinema programmers discover unexpected cultural connections, inspect the evidence, and turn promising ideas into testable decisions.**

The primary product benefit proposed is **cultural exploration and accountable decision-making**, not proven accuracy of audience preferences, ticket-sales lift, or sponsor conversion.

## Natural 30-second explanation

> I built Adjacent Cinema for filmmakers and independent cinemas that want to understand where a film might connect beyond its obvious genre. The user gives a film brief or cinema programme; the app checks the references, uses Qloo to explore related cultural worlds, and shows the signals and limitations behind each recommendation. Instead of simply saying "this audience will like it," the app offers positioning ideas that a human can inspect, challenge, and turn into an experiment. It also has a separate, human-reviewed sponsorship workflow.

## More technical 60-second explanation

> Adjacent Cinema is not just a chatbot wrapping an API. The backend uses a bounded plan–select–act–evaluate–stop workflow with typed Qloo operations, entity verification, request budgets, and traceable provider calls. In Creator Studio, it builds a cultural fingerprint and compares evidence-backed positioning strategies. In Cinema Mode, it proposes a programming direction, explains the evidence, and lets the operator challenge the ranking within the retrieved pool. FilmSponsor handles brand discovery and creator-reviewed drafts, but it does not treat affinity as proof of a sponsorship deal. The important design choice is that facts, interpretations and hypotheses remain separate; if evidence is missing, the system can say so rather than inventing a result.

## The evidence to quote accurately

| Question | Evidence that exists | What it means |
| --- | --- | --- |
| Is this a deployed application? | Public Next.js frontend and backend, with production route and fixture API smoke tests passed on 2 November. | The hosted routes and labelled fixture endpoints worked at the time checked. It does not prove every browser interaction. |
| Does it actually call Qloo? | A measured, live study verified and scored all 12/12 candidate films in a single context, with recorded call ID and a locked non-Qloo candidate set. | Real Qloo data were used and produced a different ordering from the metadata heuristic on that one task. |
| Did Qloo improve the ranking? | On the 12-film horror universe, Qloo #1 was **Videodrome** while metadata #1 was **The Witch**; top-5 overlap was **2/5**. | Difference is shown; superior accuracy or user value is **not established**. |
| Does it match historical audience ratings better? | Exploratory post-submission MovieLens analysis: among 5,929 qualifying users, Qloo ordered observed preference pairs correctly **48.0%** versus **52.6%** for metadata. | **No** advantage established. For a stricter 2,500-user group the difference was inconclusive. |
| Is there evidence of more cultural breadth? | Post-hoc top-five comparison: Qloo covered **3 countries / 5 directors** versus metadata **1 country / 4 directors**; lower mean genre Jaccard (0.517 vs 0.717). | More diverse films under this author's metadata definitions in **one** example, not a proven general user benefit. |
| Did it raise revenue or attendance? | No prospective experimental observations or ticket-sales data presented. | **No such claim.** |

**Important chronology:** The MovieLens rating evaluation and the diversity analysis are **post-submission exploratory work**, conducted 2 November 2026. Never present them as original Devpost-submitted results or independent proof that the app wins on recommendation quality.

## How to handle sceptical questions

**“Why Qloo instead of metadata-only recommendations?”**  
“Genre, director and country are useful, and we explicitly compare against them. Qloo offers another view of cultural adjacency, which can change and broaden what the team considers. We use it as a research signal with provenance, not as an oracle. In our historical-ratings proxy the metadata heuristic actually did better, so I would not claim Qloo is a better predictor of ratings.”

**“What does your agent actually do?”**  
“Application code orchestrates a bounded state machine: plan what information is needed, select approved tools, execute Qloo requests, validate the returned evidence, and either produce a supported brief or stop with an explicit limitation. The core retrieval and decisions are not a free-running LLM; optional LLM synthesis sits downstream.”

**“What's the real-world impact?”**  
“The plausible impact is helping small film teams explore unfamiliar positioning options and make transparent, testable choices. We haven't measured real attendance or marketing uplift yet. That is a next-stage validation task.”

**“Can sponsorship be automated?”**  
“No. FilmSponsor is an assisted workflow for discovery, evidence review, draft creation and human approval. It does not automatically send outreach or establish a brand's willingness to sponsor.”

**“Are the sample demos real Qloo calls?”**  
“No. They are explicitly labelled fixture examples. Separately, we have reproducible measured Qloo results and live-provider tests. We keep those two evidence statuses distinct.”

**“Can you share a video?”**  
“A video is not prepared. The hosted application, source code, test evidence and honest data-status labels are available.” Do not claim a video exists.

## What would establish a stronger outcome claim later?

Run a **prospective, blinded cinema-programmer comparison** with a preregistered rubric for novelty, contextual fit, programming viability, and evidence quality; keep an independently selected common film pool and measure participant agreement. Then, where practical and with consent, randomize audience-facing positioning in real campaigns and record independently measured outcomes, with denominators and confidence intervals. Treat any adverse result as meaningful evidence. This is a future validation proposal, **not work already completed**.

## Source-of-truth locations

- Submitted product README: `README.md` on `main`.
- Live Qloo fixed-candidate experiment: `docs/LIVE_COMMON_UNIVERSE_RESULT_20261102.md` and `data/processed/m14_common_universe_live_20261102.json` on `main`.
- Post-submission MovieLens and diversity results: `research/POST_SUBMISSION_AUDIENCE_EVALUATION_20261102.md` on this research branch.
- Deployed route/fixture smoke: GitHub Actions run `41472790062`; successful builds on PR #37.
