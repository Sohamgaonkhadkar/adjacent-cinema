#!/usr/bin/env python3
"""Post-submission EXPLORATORY diversity analysis of already-frozen Qloo rankings.

Compares country/director breadth and mean pairwise genre Jaccard in the
top-five movie candidates. This is a different objective from predicting
historical ratings, and is NOT proof of recommendation quality or user impact.
These exploratory dimensions were examined after the ratings evaluation.
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / "data/benchmarks/common_universe_20261102.json").read_text())
live = json.loads((ROOT / "data/processed/m14_common_universe_live_20261102.json").read_text())
key = lambda film: film["title"].casefold() + "|" + str(film["year"])
candidates = {key(m): m for m in manifest["candidates"]}
assert len(candidates) == 12
assert set(live["qloo_order"]) == set(live["metadata_order"]) == set(candidates)
assert live["status"] == "evaluable" and live["data_status"] == "measured"


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1


def metrics(order, k=5):
    selected = [candidates[mid] for mid in order[:k]]
    similarities = [jaccard(x["genres"], y["genres"]) for x, y in combinations(selected, 2)]
    return {
        "top_five": [m["title"] for m in selected],
        "distinct_countries": len({m["country"] for m in selected}),
        "countries": sorted({m["country"] for m in selected}),
        "distinct_directors": len({m["director"] for m in selected}),
        "mean_pairwise_genre_jaccard": round(sum(similarities) / len(similarities), 6),
        "genre_similarity_scale": "0=all genre sets disjoint; 1=identical",
    }


result = {
    "schema": "adjacent.postsubmission.diversity-proxy/1",
    "status": "exploratory_post_hoc",
    "study_id": live["study_id"],
    "frozen_sha256": live["frozen_sha256"],
    "scope": "one pre-existing 12-candidate horror programme, top five; not a new Qloo call",
    "qloo": metrics(live["qloo_order"]),
    "metadata": metrics(live["metadata_order"]),
    "limitations": [
        "The diversity metrics were examined after seeing the historical rating results; not preregistered.",
        "Movie metadata were author curated, not validated by a separate independent film catalogue.",
        "Country breadth is not geographic audience reach; genre diversity is not novel user enjoyment.",
        "Diversity alone does not establish recommendation accuracy, artist benefit, ticket sales, or any causal outcome.",
    ],
}
assert result["qloo"]["distinct_countries"] == 3
assert result["metadata"]["distinct_countries"] == 1
print(json.dumps(result, indent=2))
