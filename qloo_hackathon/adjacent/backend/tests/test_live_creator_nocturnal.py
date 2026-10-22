"""Live Creator end-to-end regression for the Nocturnal Drifter workflow.

This is a controlled request, not a claim to reproduce the unavailable original
request byte-for-byte. It covers every field in the Creator intake and validates
the shapes and provenance of all generated sections without logging secret data.
"""

from __future__ import annotations

import os
import time

import pytest
from app.config import Settings
from app.main import app
from fastapi.testclient import TestClient

_HAS_KEY = bool((os.environ.get("QLOO_API_KEY") or "").strip())


@pytest.mark.live
@pytest.mark.skipif(
    not _HAS_KEY,
    reason="QLOO_API_KEY not available — live Creator test requires a real key",
)
def test_nocturnal_drifter_creator_all_intake_fields_and_outputs() -> None:
    """POST the whole Creator form, then validate evidence, fingerprint and briefs."""
    assert Settings.from_env().has_api_key
    request = {
        "title": "Nocturnal Drifter",
        "logline": "An independent thriller following a lone night-shift drifter through a city.",
        "genre": "thriller",
        "language": "English",
        "themes": ["Thriller", "Urban"],
        "references": [
            {"title": "Nightcrawler", "year": 2014},
            {"title": "After Hours", "year": 1985},
            {"title": "Taxi Driver", "year": 1976},
        ],
        "release_goal": "Independent film release",
        "city": "Portland, Oregon",
    }

    with TestClient(app) as client:
        created = client.post("/creator/run", json=request)
        assert created.status_code == 200, created.text
        start = created.json()
        run_id = start["run_id"]

        # Theme strings must never be inserted into the list of film references.
        assert [item["title"] for item in start["programme"]] == [
            "Nightcrawler",
            "After Hours",
            "Taxi Driver",
        ]

        deadline = time.monotonic() + 90
        final = start
        while time.monotonic() < deadline:
            response = client.get(f"/run/{run_id}")
            assert response.status_code == 200
            final = response.json()
            if final["status"] in {"completed", "insufficient", "failed"}:
                break
            time.sleep(0.15)

    assert final["status"] in {"completed", "insufficient"}, (
        "Creator run failed in the controlled live scenario; "
        f"phase={final.get('current_phase')}, "
        f"error={final.get('error') or final.get('stop_message')}. "
        "Use sanitized frames for triage; never print provider bodies or credentials."
    )
    result = final["result"]
    assert result is not None
    assert result["mode"] == "creator"
    assert result["data_status"] == "measured"

    # Section 01 — all input blocks are preserved, and only reference films enter
    # the movie-resolution path.
    assert result["film"] == {
        "title": request["title"],
        "logline": request["logline"],
        "genre": request["genre"],
        "language": request["language"],
        "release_goal": request["release_goal"],
        "themes": request["themes"],
    }
    assert result["city"] == request["city"]
    assert [item["title"] for item in result["programme"]["items"]] == [
        "Nightcrawler",
        "After Hours",
    ]
    assert result["programme"]["total_count"] == len(request["references"])
    assert all(theme not in {item["title"] for item in result["programme"]["items"]} for theme in request["themes"])

    theme_evidence = result["theme_inputs"]
    assert [item["input"] for item in theme_evidence] == request["themes"]
    trace_ids = {row["call_id"] for row in final.get("trace", []) if row.get("call_id")}
    for item in theme_evidence:
        assert item["status"] in {"matched", "ambiguous", "unresolved"}
        assert item["call_id"] in trace_ids
        if item["status"] == "matched":
            assert item["qloo_tag_id"] and item["qloo_name"]
        else:
            assert item["qloo_tag_id"] is None

    # Section 02 — investigation summaries must only cite calls in this run.
    investigation = result["investigation"]
    assert investigation["data_status"] == "measured"
    assert investigation["questions"]
    assert investigation["film"]["themes"] == request["themes"]
    q0 = next(question for question in investigation["questions"] if question["id"] == "q0")
    assert "reference works: Nightcrawler, After Hours, Taxi Driver" in q0["summary"]
    assert "themes: Thriller, Urban" in q0["summary"]
    for question in investigation["questions"]:
        assert set(question.get("evidence_refs", [])) <= trace_ids
    for finding in investigation["findings"]:
        assert set(finding.get("evidence_refs", [])) <= trace_ids
    assert set(investigation["provenance"]["call_ids"]) <= trace_ids

    # Section 03 — ranked and rejected worlds are structured and rank ordered.
    cohorts = result["cohorts"]
    assert isinstance(cohorts["ranked"], list)
    assert isinstance(cohorts["rejected"], list)
    ranks = [cohort["rank"] for cohort in cohorts["ranked"]]
    assert ranks == sorted(ranks)
    assert len(ranks) == len(set(ranks))
    for cohort in cohorts["ranked"]:
        assert cohort["cohort_id"]
        assert cohort["members"]
        if cohort.get("score") and cohort["score"].get("mean_affinity") is not None:
            assert 0 <= cohort["score"]["mean_affinity"] <= 1

    # The deterministic decision artifacts must agree with the top ranked cohort;
    # on honest insufficiency they are correctly absent rather than fabricated.
    if final["status"] == "completed":
        assert cohorts["ranked"]
        assert result["programme_bet"] is not None
        assert result["test_card"] is not None
        assert result["programme_bet"]["primary"]["cohort_id"] == cohorts["ranked"][0]["cohort_id"]
        assert result["test_card"]["provenance"]["primary_cohort_id"] == cohorts["ranked"][0]["cohort_id"]
        assert result["programme_bet"]["data_status"] == "measured"
        assert result["test_card"]["data_status"] == "measured"
    else:
        assert result["programme_bet"] is None
        assert result["test_card"] is None

    # Section 04 — synthesis is optional and must state whether it is available.
    with TestClient(app) as client:
        synthesis_status = client.get("/creator/synthesis-status")
        assert synthesis_status.status_code == 200
        synthesis = synthesis_status.json()
    assert isinstance(synthesis.get("available"), bool)
    if not synthesis["available"]:
        assert synthesis.get("blocked_reason")

    # No API key, token, or provider body should enter public run output.
    public_payload = str(final)
    assert "QLOO_API_KEY" not in public_payload
    assert "X-Api-Key" not in public_payload
