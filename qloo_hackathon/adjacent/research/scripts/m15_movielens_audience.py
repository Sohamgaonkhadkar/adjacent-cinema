#!/usr/bin/env python3
"""Exploratory OUT-OF-SUBMISSION MovieLens audience preference proxy.

Uses 2023 MovieLens 32M (pre-existing historical audience ratings) to ask
whether the ALREADY FROZEN Qloo and metadata candidate rankings differ in
agreement with ratings given by people who also liked programme seed films.

No live Qloo requests; no learned/optimized weights; no raw per-user output.
These are self-selected ratings, NOT cinema attendance, ticket sales, prospective
A/B tests, independent programmer evaluations, or causal product improvement.
This script is research-only: never silently substitute this result for a
hackathon-submission outcome claim.

Usage:
  python3 research/scripts/m15_movielens_audience.py \
    --zip /tmp/ml-32m.zip --output /tmp/audience-study.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import random
import re
import statistics
import zipfile
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "data/benchmarks/common_universe_20261102.json"
RESULT = ROOT / "data/processed/m14_common_universe_live_20261102.json"
EXPECTED_RECORDS = 32_000_204
SEED_MIN_RATING = 4.0
BOOTSTRAP_SEED = 20261102
BOOTSTRAP_REPS = 1000
DATASET = "MovieLens 32M (GroupLens Research, generated 2023-10-13)"
SOURCE = "https://files.grouplens.org/datasets/movielens/ml-32m.zip"


def movie_key(title: str, year: int) -> str:
    return title.strip().casefold() + "|" + str(year)


def norm_title(title: str) -> str:
    title = title.casefold().strip()
    title = re.sub(r",\s*(the|a|an)$", r"", title)
    title = re.sub(r"^(the|a|an)\s+", "", title)
    return re.sub(r"[^a-z0-9]+", "", title)


def read_member(z: zipfile.ZipFile, name: str):
    matches = [x for x in z.namelist() if x.endswith("/" + name)]
    if len(matches) != 1:
        raise ValueError("Expected exactly one dataset member: " + name)
    return io.TextIOWrapper(z.open(matches[0]), encoding="utf-8", newline="")


def load_locked():
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    if result["status"] != "evaluable" or result["data_status"] != "measured":
        raise ValueError("Not a measured Qloo run")
    if len(frozen["candidates"]) != 12 or len(frozen["programme"]) != 3:
        raise ValueError("Unexpected frozen pool dimensions")
    all_keys = {movie_key(x["title"], x["year"]) for x in frozen["candidates"]}
    if set(result["qloo_order"]) != all_keys or set(result["metadata_order"]) != all_keys:
        raise ValueError("Full shared candidate ranking required")
    if frozen["study_id"] != result["study_id"] or not result["frozen_sha256"]:
        raise ValueError("Study provenance mismatch")
    return frozen, result


def catalogue_mapping(z, frozen):
    # Never use Qloo entity IDs or Qloo-derived selection when matching titles:
    # match independent MovieLens catalogue title and recorded release year.
    targets = {
        movie_key(x["title"], x["year"]): x
        for x in frozen["programme"] + frozen["candidates"]
    }
    possible = {key: [] for key in targets}
    with read_member(z, "movies.csv") as fp:
        for row in csv.DictReader(fp):
            m = re.search(r"\((\d{4})\)\s*$", row["title"])
            if not m:
                continue
            year = int(m.group(1))
            title = row["title"][:m.start()].strip()
            for key, target in targets.items():
                if norm_title(title) == norm_title(target["title"]) and abs(year - target["year"]) <= 1:
                    possible[key].append((abs(year - target["year"]), int(row["movieId"]), row["title"]))
    matched = {}
    anomalies = {}
    for key, entries in possible.items():
        entries.sort()
        if not entries:
            anomalies[key] = "not_found_in_movielens_catalogue"
        elif len(entries) > 1 and entries[0][0] == entries[1][0]:
            anomalies[key] = "ambiguous_multiple_matches"
        else:
            matched[key] = {"movie_id": entries[0][1], "catalog_title": entries[0][2],
                            "year_difference": entries[0][0]}
    reverse = {v["movie_id"]: key for key, v in matched.items()}
    if len(reverse) != len(matched):
        raise ValueError("Same catalogue movie mapped to multiple frozen titles")
    return matched, anomalies, reverse


def single_user(user_ratings, seed_keys, qloo_ranks, metadata_ranks):
    seed_ratings = [user_ratings[k] for k in seed_keys if k in user_ratings]
    liked = [r for r in seed_ratings if r >= SEED_MIN_RATING]
    rated_candidates = {k: r for k, r in user_ratings.items() if k in qloo_ranks}
    if len(rated_candidates) < 2:
        return None, len(liked), len(rated_candidates)
    agreements = {"qloo": 0, "metadata": 0, "pairs": 0}
    for (a, ra), (b, rb) in combinations(rated_candidates.items(), 2):
        if ra == rb:
            continue
        agrees_qloo = (qloo_ranks[a] < qloo_ranks[b]) == (ra > rb)
        agrees_metadata = (metadata_ranks[a] < metadata_ranks[b]) == (ra > rb)
        agreements["qloo"] += int(agrees_qloo)
        agreements["metadata"] += int(agrees_metadata)
        agreements["pairs"] += 1
    if not agreements["pairs"]:
        return None, len(liked), len(rated_candidates)
    return agreements, len(liked), len(rated_candidates)


def summarize(records):
    # Per-user averages and paired per-user bootstrap: users, NOT rating pairs,
    # are the resampling unit. Prevents highly active users dominating.
    n = len(records)
    if not n:
        return {"status": "insufficient", "users": 0, "meaning": "No evaluable audience co-raters"}
    deltas = [((r["qloo"] - r["metadata"]) / r["pairs"]) for r in records]
    qs = [r["qloo"] / r["pairs"] for r in records]
    ms = [r["metadata"] / r["pairs"] for r in records]
    effect = statistics.fmean(deltas)
    rng = random.Random(BOOTSTRAP_SEED)
    boot = []
    # cap repeated sampling workload; benchmark should run on GH standard runner
    for _ in range(BOOTSTRAP_REPS):
        boot.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    boot.sort()
    lo = boot[int(0.025 * BOOTSTRAP_REPS)]
    hi = boot[int(0.975 * BOOTSTRAP_REPS) - 1]
    total_pairs = sum(r["pairs"] for r in records)
    return {
        "status": "evaluable" if n >= 100 else "low_sample",
        "users": n,
        "rated_preference_pairs": total_pairs,
        "user_weighted_qloo_pair_accuracy": round(statistics.fmean(qs), 6),
        "user_weighted_metadata_pair_accuracy": round(statistics.fmean(ms), 6),
        "paired_qloo_minus_metadata": round(effect, 6),
        "paired_bootstrap_95pct_ci": [round(lo, 6), round(hi, 6)],
        "bootstrap_unit": "user",
        "bootstrap_reps": BOOTSTRAP_REPS,
        "interpretation": (
            "Qloo ranked the observed audience preference pairs more consistently"
            if n >= 100 and lo > 0 else
            "Metadata ranked the observed audience preference pairs more consistently"
            if n >= 100 and hi < 0 else
            "Insufficient or inconclusive evidence of a ranking advantage"
        ),
        "caveat": "In-sample retrospective ratings; no randomized exposure, no causal uplift, no attendance metric.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, type=Path, help="Original ml-32m.zip, not redistributable here")
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    frozen, result = load_locked()
    seed_keys = {movie_key(x["title"], x["year"]) for x in frozen["programme"]}
    qloo = {k: i for i, k in enumerate(result["qloo_order"])}
    metadata = {k: i for i, k in enumerate(result["metadata_order"])}
    with zipfile.ZipFile(args.zip, "r") as z:
        mapping, anomalies, id_to_key = catalogue_mapping(z, frozen)
        admitted_seeds = seed_keys.intersection(mapping)
        admitted_candidates = set(qloo).intersection(mapping)
        # If historical catalogue omits an item, don't fill its rating or
        # pretend it was evaluated. Report exact coverage unconditionally.
        qloo_eval = {k: v for k, v in qloo.items() if k in admitted_candidates}
        metadata_eval = {k: v for k, v in metadata.items() if k in admitted_candidates}
        records = {"one_liked_seed": [], "two_liked_seeds": [], "all_co_raters": []}
        n_rows = 0
        n_any_titles = 0
        n_candidate_co_raters = 0
        current_user = None
        current_ratings = {}

        def finish_user():
            nonlocal n_candidate_co_raters
            if not current_ratings:
                return
            scored, liked_count, candidates = single_user(
                current_ratings, admitted_seeds, qloo_eval, metadata_eval
            )
            if scored is None:
                return
            n_candidate_co_raters += 1
            records["all_co_raters"].append(scored)
            if liked_count >= 1:
                records["one_liked_seed"].append(scored)
            if liked_count >= 2:
                records["two_liked_seeds"].append(scored)

        with read_member(z, "ratings.csv") as fp:
            for row in csv.DictReader(fp):
                n_rows += 1
                user = int(row["userId"])
                if current_user is None:
                    current_user = user
                elif user != current_user:
                    finish_user()
                    current_ratings = {}
                    current_user = user
                key = id_to_key.get(int(row["movieId"]))
                if key is None:
                    continue
                n_any_titles += 1
                current_ratings[key] = float(row["rating"])
            finish_user()
        if n_rows != EXPECTED_RECORDS:
            raise ValueError("Unexpected MovieLens ratings row count: " + str(n_rows))
    report = {
        "schema": "adjacent.audience-preference-proxy/1",
        "study_id": "m15-postsubmission-movielens-20261102",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "usage": "post-submission exploratory research; never claim this was in the October 30 hackathon submission",
        "dataset": DATASET, "dataset_url": SOURCE,
        "dataset_acknowledgement": "F. Maxwell Harper and Joseph A. Konstan (2015), The MovieLens Datasets: History and Context, ACM TiiS 5(4):19, DOI:10.1145/2827872",
        "license_notice": "MovieLens research-use conditions apply; no GroupLens endorsement; commercial use requires prior permission.",
        "qloo_source_study": result["study_id"],
        "qloo_source_frozen_sha256": result["frozen_sha256"],
        "evaluation_method": (
            "For a user who rated 2+ of the 12 candidates differently, compute fraction of "
            "unequal-rating candidate pairs whose historical ratings agree with the fixed "
            "Qloo or metadata rank. Compare paired user-level accuracy. Primary cohort: "
            "users who also rated at least one frozen programme seed >=4.0; secondary "
            "cohort: 2+ liked seeds; contextual cohort: all 2+ candidate co-raters."
        ),
        "selection_guardrails": {
            "ranks_frozen_before_evaluation": True,
            "post_hoc_weight_tuning": False,
            "title_matching": "casefold, remove punctuation and leading/trailing articles; year within +/- 1; ambiguous equal-distance matches excluded",
            "benchmark_not_blindly_preregistered": True,
            "outcome_verdict": "not_established",
            "limitations": [
                "Nonrandom self-selected ratings and observed-only pairs; severe missing-not-at-random bias.",
                "Ratings are retrospective liking signals, not viewing attendance, cinema visits, sales or actual A/B lifts.",
                "Horror-only author-curated candidate set, not representative of all app workflows.",
                "MovieLens cannot be guaranteed independent from Qloo's training or knowledge sources.",
                "A user preferring one seed does not imply they are an independent cinema audience in this location.",
                "Historical ratings timestamps do not prove exposure to Qloo recommendations.",
            ],
        },
        "candidate_coverage": {"found": len(admitted_candidates), "of": 12},
        "seed_coverage": {"found": len(admitted_seeds), "of": 3},
        "film_catalogue_mapping": mapping,
        "missing_or_ambiguous": anomalies,
        "dataset_rating_rows": n_rows,
        "matched_title_rating_rows": n_any_titles,
        "users_with_2_rated_candidates_and_unequal_ratings": n_candidate_co_raters,
        "cohorts": {name: summarize(rows) for name, rows in records.items()},
    }
    if len(admitted_candidates) < 8 or len(admitted_seeds) < 2:
        report["evaluation_gate"] = "blocked_catalogue_coverage"
        for item in report["cohorts"].values():
            item["status"] = "blocked_catalogue_coverage"
            item["interpretation"] = "Do not use comparisons; too few films verified in external catalogue"
    else:
        report["evaluation_gate"] = "computed_with_missingness_caveats"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "evaluation_gate": report["evaluation_gate"],
        "candidate_coverage": report["candidate_coverage"],
        "seed_coverage": report["seed_coverage"],
        "cohorts": {k: v for k, v in report["cohorts"].items()},
        "report": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
