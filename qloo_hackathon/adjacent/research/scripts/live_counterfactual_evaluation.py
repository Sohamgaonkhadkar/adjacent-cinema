#!/usr/bin/env python3
"""Generate a reproducible, live-Qloo counterfactual report for Adjacent.

This reuses the product's live runner and Decision Challenge. It does not
implement a second ranking function, call an LLM, or infer downstream outcomes.
All emitted measurements are tied to application trace rows.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.challenge import build_decision_challenge  # noqa: E402
from app.live_runner import run_live  # noqa: E402

# Inputs are explicit. The live resolver still verifies title/year/type
# consistency before admitting an entity.
PROGRAMMES: tuple[dict[str, Any], ...] = (
    {
        "id": "international-stories",
        "description": "International stories and contemporary auteur cinema",
        "items": [
            {"title": "Perfect Days", "year": 2023, "imdb_id": "tt27503384"},
            {"title": "Roma", "year": 2018, "imdb_id": "tt6155172"},
            {"title": "Shoplifters", "year": 2018, "imdb_id": "tt8075192"},
            {"title": "The Zone of Interest", "year": 2023, "imdb_id": "tt7160372"},
        ],
    },
    {
        "id": "psychological-tension",
        "description": "Psychological tension and genre-adjacent cinema",
        "items": [
            {"title": "The Lighthouse", "year": 2019, "imdb_id": "tt7984734"},
            {"title": "Uncut Gems", "year": 2019, "imdb_id": "tt5727208"},
            {"title": "Get Out", "year": 2017, "imdb_id": "tt5052448"},
            {"title": "The Babadook", "year": 2014, "imdb_id": "tt2321549"},
        ],
    },
    {
        "id": "auteur-cross-cultural",
        "description": "Auteur cinema across cultures and periods",
        "items": [
            {"title": "Paris, Texas", "year": 1984, "imdb_id": "tt0087884"},
            {"title": "Taipei Story", "year": 1985, "imdb_id": "tt0089853"},
            {"title": "Portrait of a Lady on Fire", "year": 2019, "imdb_id": "tt8613070"},
            {"title": "Drive My Car", "year": 2021, "imdb_id": "tt14039582"},
        ],
    },
)

LIMITATIONS = [
    "The counterfactual holds the retrieved and admitted candidate pool fixed; it tests ranking sensitivity, not what a fresh Qloo query would retrieve.",
    "A changed winner is not proof that Qloo is correct or that the recommendation will succeed.",
    "An unchanged winner is still reported and is not presented as evidence of Qloo necessity.",
    "Popularity-only uses the same candidates and returned popularity fields; it is not an external ground-truth or business baseline.",
    "No attendance, audience size, conversion, revenue, causal effect, or ROI is measured.",
    "All runs, including failures and insufficient-evidence results, remain in the report. Fixture data is never substituted into a live report.",
]


def _label_for(order: list[dict[str, Any]], winner_id: str | None) -> str | None:
    if winner_id is None:
        return None
    for item in order:
        if item.get("cohort_id") == winner_id:
            return item.get("label") or winner_id
    return winner_id


def summarize_run(scenario: dict[str, Any]) -> dict[str, Any]:
    """Execute one real-provider run and summarise its traceable counterfactuals."""
    base: dict[str, Any] = {
        "programme_id": scenario["id"],
        "description": scenario["description"],
        "programme": [
            {"title": item["title"], "year": item["year"], "imdb_id": item["imdb_id"]}
            for item in scenario["items"]
        ],
    }
    try:
        state = run_live(
            scenario["items"],
            render=False,
            resolver_delay_s=1.1,
        )
    except Exception as exc:  # never serialize exception payloads or request details
        return {
            **base,
            "status": "failed",
            "data_status": "unavailable",
            "error_type": type(exc).__name__,
            "app_trace_ids": [],
            "application_trace_count": 0,
        }

    trace_rows = state.trace_rows
    call_ids = sorted({
        str(row["call_id"])
        for row in trace_rows
        if isinstance(row.get("call_id"), str) and row["call_id"]
    })
    row: dict[str, Any] = {
        **base,
        "data_status": state.data_status,
        "stop_reason": state.stop_reason,
        "resolved_films": len(state.resolved_items),
        "unresolved_films": [item.title for item in state.unresolved_items],
        "app_trace_ids": call_ids,
        "application_trace_count": len(call_ids),
        "ranked_cohort_count": len(state.ranked),
        "rejected_cohort_count": len(state.rejected),
    }

    if state.data_status != "measured":
        return {**row, "status": "not_measured", "error_type": None}

    challenge = build_decision_challenge(state)
    if not challenge.get("available") or state.stop_reason != "complete":
        return {
            **row,
            "status": "not_evaluable",
            "error_type": None,
            "challenge_unavailable_reason": challenge.get("unavailable_reason")
            or state.stop_message
            or "No completed recommendation was available to challenge.",
        }

    necessity = challenge.get("necessity") or {}
    withheld = necessity.get("affinity_withheld") or {}
    popularity = necessity.get("popularity_only") or {}
    production_order = necessity.get("production_order") or []
    withheld_order = withheld.get("order") or []
    popularity_order = popularity.get("order") or []
    production_winner = challenge.get("recommendation") or {}
    withheld_winner_id = withheld.get("counterfactual_winner")
    popularity_winner_id = popularity.get("counterfactual_winner")

    # Keep affinity-gate effects separate from the order-only counterfactual.
    # The retrieved pool is fixed; this does not simulate fresh Qloo retrieval.
    gate = necessity.get("gate") or {}
    gate_suppressed = gate.get("suppressed_by_affinity_gate") or []
    structurally_admitted = gate.get("structurally_admitted") or []
    admitted_without_structure = gate.get("admitted_without_structural_support") or []
    winner_id = production_winner.get("cohort_id")
    winner_cohort = next(
        (cohort for cohort in state.ranked if cohort.cohort_id == winner_id), None
    )
    winner_score = winner_cohort.score if winner_cohort is not None else None
    contexts = list(getattr(state.ranking, "contexts", []) or [])
    contexts_by_id = {context.context_id: context for context in contexts}
    winner_context = (
        contexts_by_id.get(winner_score.context_id) if winner_score is not None else None
    )

    return {
        **row,
        "status": "evaluable",
        "error_type": None,
        "production_winner_id": winner_id,
        "production_winner": production_winner.get("label"),
        "affinity_withheld_winner_id": withheld_winner_id,
        "affinity_withheld_winner": _label_for(withheld_order, withheld_winner_id),
        "affinity_withheld_winner_changed": withheld.get("winner_changed"),
        "affinity_withheld_rank_positions_moved": withheld.get("ranks_moved", 0),
        "popularity_only_winner_id": popularity_winner_id,
        "popularity_only_winner": _label_for(popularity_order, popularity_winner_id),
        "popularity_only_winner_changed": popularity.get("winner_changed"),
        "affinity_decided_pairs": len(necessity.get("affinity_decided_pairs") or []),
        "adjacent_pairs_examined": necessity.get("adjacent_pairs_examined", 0),
        "affinity_gate_suppressed_count": len(gate_suppressed),
        "affinity_gate_suppressed_labels": [
            item.get("label") for item in gate_suppressed if item.get("label")
        ],
        "structurally_admitted_count": len(structurally_admitted),
        "admitted_without_structural_support_count": len(admitted_without_structure),
        "winner_context_domain": winner_cohort.domain if winner_cohort is not None else None,
        "winner_mean_affinity": winner_score.mean_affinity if winner_score is not None else None,
        "winner_qualifying_members": winner_score.qualifying_members if winner_score is not None else None,
        "winner_scored_members": winner_score.total_members if winner_score is not None else None,
        "winner_median_popularity": winner_score.median_popularity if winner_score is not None else None,
        "winner_explainability_status": (
            winner_context.explainability_status if winner_context is not None else None
        ),
        "scoring_contexts": [
            {
                "domain": context.domain,
                "requested": len(context.requested_ids),
                "returned": len(context.scored),
                "explainability_status": context.explainability_status,
            }
            for context in contexts
        ],
        "stability_verdict": (challenge.get("stability") or {}).get("verdict", "undetermined"),
        "stability_evidence_items_tested": (challenge.get("stability") or {}).get("evaluated", 0),
        "counterfactual_extra_qloo_calls": necessity.get("qloo_calls_made", 0),
        "production_order": production_order,
    }


def build_report(runs: list[dict[str, Any]]) -> dict[str, Any]:
    evaluable = [run for run in runs if run.get("status") == "evaluable"]
    return {
        "schema": "adjacent.live-counterfactual-evaluation/1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "evaluation_kind": "live_qloo",
        "method": (
            "Run the existing live pipeline for each listed programme, then apply the existing "
            "Decision Challenge to the same cached run. No second ranker or additional counterfactual Qloo calls."
        ),
        "summary": {
            "programmes_attempted": len(runs),
            "programmes_evaluable": len(evaluable),
            "programmes_failed_or_not_evaluable": len(runs) - len(evaluable),
            "affinity_withheld_changed_winner": sum(
                run.get("affinity_withheld_winner_changed") is True for run in evaluable
            ),
            "popularity_only_changed_winner": sum(
                run.get("popularity_only_winner_changed") is True for run in evaluable
            ),
            "programmes_with_affinity_gate_suppression": sum(
                (run.get("affinity_gate_suppressed_count") or 0) > 0 for run in evaluable
            ),
            "cohorts_suppressed_by_affinity_gate": sum(
                run.get("affinity_gate_suppressed_count", 0) for run in evaluable
            ),
            "programmes_with_affinity_decided_pairs": sum(
                (run.get("affinity_decided_pairs") or 0) > 0 for run in evaluable
            ),
        },
        "limitations": LIMITATIONS,
        "runs": runs,
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Live Qloo Counterfactual Evaluation",
        "",
        f"- Generated: **{report['generated_at_utc']}**",
        f"- Schema: **{report['schema']}**",
        f"- Programmes attempted: **{summary['programmes_attempted']}**",
        f"- Programmes evaluable: **{summary['programmes_evaluable']}**",
        f"- Failed / not evaluable: **{summary['programmes_failed_or_not_evaluable']}**",
        f"- Affinity-withheld runs that changed the winner: **{summary['affinity_withheld_changed_winner']} / {summary['programmes_evaluable']}**",
        f"- Popularity-only runs that changed the winner: **{summary['popularity_only_changed_winner']} / {summary['programmes_evaluable']}**",
        f"- Programmes with at least one cohort suppressed by the affinity gate: **{summary.get('programmes_with_affinity_gate_suppression', 0)} / {summary['programmes_evaluable']}**",
        f"- Cohorts suppressed by the affinity gate across all programmes: **{summary.get('cohorts_suppressed_by_affinity_gate', 0)}**",
        f"- Programmes where affinity decided at least one adjacent ranking pair: **{summary.get('programmes_with_affinity_decided_pairs', 0)} / {summary['programmes_evaluable']}**",
        "",
        "## Per-programme results",
        "",
        "| Programme | Status | Resolved | App trace rows | Production winner | Winner without affinity | Changed? | Popularity-only winner | Changed? | Affinity-decided pairs | Stability |",
        "|---|---|---:|---:|---|---|---|---|---|---:|---|",
    ]
    for run in report["runs"]:
        def cell(value: Any) -> str:
            return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")
        lines.append(
            "| "
            + " | ".join(
                cell(value)
                for value in (
                    run["programme_id"],
                    run["status"],
                    f"{run.get('resolved_films', 0)}/{len(run['programme'])}",
                    run.get("application_trace_count", 0),
                    run.get("production_winner"),
                    run.get("affinity_withheld_winner"),
                    run.get("affinity_withheld_winner_changed"),
                    run.get("popularity_only_winner"),
                    run.get("popularity_only_winner_changed"),
                    (
                        f"{run.get('affinity_decided_pairs', 0)}/"
                        f"{run.get('adjacent_pairs_examined', 0)}"
                        if run.get("status") == "evaluable" else "—"
                    ),
                    run.get("stability_verdict"),
                )
            )
            + " |"
        )
    lines.extend([
        "",
        "## Affinity-gate and winner-signal audit",
        "",
        "The gate audit is separate from the order-only counterfactual: it records structurally large groupings that did not clear the production evidence gate. It holds the returned candidate pool fixed and does not simulate fresh Qloo retrieval. Winner affinity is shown only alongside its own entity-type context; raw affinity values are not comparable across domains or runs.",
        "",
        "| Programme | Gate-suppressed groupings | Winning context | Winner mean affinity (context-local) | Qualifying / scored members | Winner explainability status |",
        "|---|---:|---|---:|---:|---|",
    ])
    for run in report["runs"]:
        def audit_cell(value: Any) -> str:
            return str(value if value is not None else "—").replace("|", "\\|").replace("\\n", " ")
        labels = run.get("affinity_gate_suppressed_labels") or []
        lines.append(
            "| "
            + " | ".join(
                audit_cell(value)
                for value in (
                    run.get("programme_id"),
                    f"{run.get('affinity_gate_suppressed_count', 0)}"
                    + (f": {', '.join(labels)}" if labels else ""),
                    run.get("winner_context_domain"),
                    run.get("winner_mean_affinity"),
                    (
                        f"{run.get('winner_qualifying_members')}/{run.get('winner_scored_members')}"
                        if run.get("winner_qualifying_members") is not None else None
                    ),
                    run.get("winner_explainability_status"),
                )
            )
            + " |"
        )
    lines.extend([
        "",
        "### Scoring-context coverage",
        "",
        "Per-context counts show which Qloo scoring contexts ran and whether optional provider explainability was returned/requested/omitted. Status strings come from the application trace; they are not a quality rating.",
        "",
    ])
    for run in report["runs"]:
        lines.extend([f"**{run['programme_id']}**", ""])
        contexts = run.get("scoring_contexts") or []
        if not contexts:
            lines.extend(["No scoring-context record was available.", ""])
            continue
        lines.extend(["| Context | Requested candidates | Returned candidates | Explainability status |", "|---|---:|---:|---|"])
        for context in contexts:
            lines.append(
                "| "
                + " | ".join(
                    audit_cell(context.get(key))
                    for key in ("domain", "requested", "returned", "explainability_status")
                )
                + " |"
            )
        lines.append("")

    lines.extend(["## Application trace IDs (scoped to each run)", ""])
    for run in report["runs"]:
        lines.extend(
            [
                f"### {run['programme_id']}",
                "",
                f"Status: **{run['status']}**; data status: **{run.get('data_status', 'unavailable')}**.",
                "",
                "Run-scoped application trace IDs: "
                + (", ".join(run.get("app_trace_ids", [])) or "none recorded"),
                "",
            ]
        )
        if run.get("error_type"):
            lines.append(f"Execution error class: **{run['error_type']}**. No exception payload was published.")
            lines.append("")
        if run.get("challenge_unavailable_reason"):
            lines.append(f"Reason: {run['challenge_unavailable_reason']}")
            lines.append("")
    lines.extend(["## Interpretation and limits", ""])
    lines.extend(f"- {limit}" for limit in report["limitations"])
    lines.extend(
        [
            "",
            "A result with no winner change is retained as-is; it is not described as evidence that Qloo was necessary. "
            "These runs describe ranking sensitivity for the selected programmes, not downstream success.",
            "",
        ]
    )
    return "\n".join(lines)


def self_test() -> None:
    """Exercise report rendering and booleans without provider calls."""
    sample = {
        "generated_at_utc": "2026-01-01T00:00:00+00:00",
        "schema": "adjacent.live-counterfactual-evaluation/1",
        "summary": {
            "programmes_attempted": 1,
            "programmes_evaluable": 1,
            "programmes_failed_or_not_evaluable": 0,
            "affinity_withheld_changed_winner": 0,
            "popularity_only_changed_winner": 1,
            "programmes_with_affinity_gate_suppression": 1,
            "cohorts_suppressed_by_affinity_gate": 1,
            "programmes_with_affinity_decided_pairs": 1,
        },
        "limitations": LIMITATIONS,
        "runs": [
            {
                "programme_id": "self-test",
                "status": "evaluable",
                "data_status": "measured",
                "programme": [{"title": "Example", "year": 2020, "imdb_id": "tt0000000"}],
                "resolved_films": 1,
                "application_trace_count": 2,
                "app_trace_ids": ["call-a", "call-b"],
                "production_winner": "Winner A",
                "affinity_withheld_winner": "Winner A",
                "affinity_withheld_winner_changed": False,
                "popularity_only_winner": "Winner B",
                "popularity_only_winner_changed": True,
                "affinity_decided_pairs": 1,
                "adjacent_pairs_examined": 3,
                "affinity_gate_suppressed_count": 1,
                "affinity_gate_suppressed_labels": ["book · Example"],
                "structurally_admitted_count": 2,
                "admitted_without_structural_support_count": 0,
                "winner_context_domain": "urn:entity:artist",
                "winner_mean_affinity": 0.77,
                "winner_qualifying_members": 2,
                "winner_scored_members": 3,
                "winner_median_popularity": 0.24,
                "winner_explainability_status": "returned",
                "scoring_contexts": [
                    {"domain": "urn:entity:artist", "requested": 5, "returned": 3, "explainability_status": "returned"}
                ],
                "stability_verdict": "fragile",
            }
        ],
    }
    rendered = markdown_report(sample)
    assert "call-a" in rendered
    assert "False" in rendered and "True" in rendered
    assert "No attendance, audience size" in rendered
    assert "Affinity-gate and winner-signal audit" in rendered
    assert "Cohorts suppressed by the affinity gate across all programmes: **1**" in rendered
    assert "book · Example" in rendered
    assert "Scoring-context coverage" in rendered
    print("Counterfactual report renderer self-test passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_DIR / "docs" / "verification",
        help="Directory where JSON and Markdown reports will be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        choices=(1, 2, 3),
        default=3,
        help="Number of default live programmes to run.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Test report formatting without making provider calls.",
    )
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    if not (os.environ.get("QLOO_API_KEY") or "").strip():
        parser.error("QLOO_API_KEY is required; this report must never be produced from fixtures.")

    runs = [summarize_run(scenario) for scenario in PROGRAMMES[: args.limit]]
    report = build_report(runs)
    markdown = markdown_report(report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "live_counterfactual_evaluation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "live_counterfactual_evaluation.md").write_text(markdown, encoding="utf-8")
    print(markdown)

    if report["summary"]["programmes_evaluable"] == 0:
        print(
            "No complete measured run produced a challenge; report saved but cannot be accepted as live evidence.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
