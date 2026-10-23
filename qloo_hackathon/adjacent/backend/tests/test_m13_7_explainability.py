"""M13.7 explainability regressions.

Covers the decision-explainability contract added in M13.7:

* the Programme Bet links back to the exact ranked cohort it was built from;
* the Test Card follows from that same bet (cohort link in provenance) and
  carries observable success criteria + an observation window without
  fabricating attendance numbers;
* cohort exclusion annotations are surfaced in the API payload — exclusions
  are rendered, never hidden (reasons.py);
* single-member cohorts are described grammatically ("0 similar entities"
  must never appear).

Offline and deterministic: unit tests use hand-built evidence objects; the
API test uses the labelled fixture demo path.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

from app.domain.programme_bet import build_programme_bet
from app.domain.test_card import build_test_card
from app.main import app
from fastapi.testclient import TestClient


def _member(name: str, affinity: float) -> SimpleNamespace:
    return SimpleNamespace(entity_id=f"urn:{name.lower().replace(' ', '_')}", name=name, affinity=affinity)


def _cohort(cohort_id: str, domain: str, members: list[SimpleNamespace], call_id: str) -> SimpleNamespace:
    affinities = [m.affinity for m in members]
    return SimpleNamespace(
        cohort_id=cohort_id,
        domain=f"urn:entity:{domain}",
        members=members,
        qualifying_members=members,
        score=SimpleNamespace(
            mean_affinity=sum(affinities) / len(affinities),
            max_affinity=max(affinities),
            novelty_proxy=0.5,
            call_id=call_id,
        ),
    )


def _bet(member_count: int = 3):
    members = [_member(f"Artist {i}", 0.7 + i * 0.01) for i in range(member_count)]
    cohorts = [
        _cohort("music_artists", "music_artist", members, "call-a"),
        _cohort("books", "book", [_member("Book One", 0.55)], "call-b"),
    ]
    return build_programme_bet(
        ranked_cohorts=cohorts,
        taste_tags=[SimpleNamespace(name="art house"), SimpleNamespace(name="neo noir")],
        geography=None,
        resolved_names=["Chungking Express"],
    )


class TestBetToCohortLink:
    def test_bet_primary_exposes_source_cohort_id(self) -> None:
        bet = _bet()
        payload = bet.to_dict()
        assert payload["primary"]["cohort_id"] == "music_artists"

    def test_test_card_provenance_carries_the_same_cohort_id(self) -> None:
        bet = _bet()
        card = build_test_card(bet=bet, resolved_names=["Chungking Express"], city="London")
        assert card.to_dict()["provenance"]["primary_cohort_id"] == "music_artists"


class TestTestCardActionability:
    def test_success_criteria_and_window_present_and_deterministic(self) -> None:
        card_a = build_test_card(bet=_bet(), resolved_names=["Chungking Express"], city="London")
        card_b = build_test_card(bet=_bet(), resolved_names=["Chungking Express"], city="London")
        assert card_a.success_criteria and card_a.observation_window
        # Deterministic: same evidence in, same card out.
        assert card_a.to_dict() == card_b.to_dict()

    def test_success_criteria_predicts_no_numbers(self) -> None:
        card = build_test_card(bet=_bet(), resolved_names=["Chungking Express"], city="London")
        text = card.success_criteria.lower()
        for forbidden in ("will increase", "expected attendance", "conversion", "revenue", "%"):
            assert forbidden not in text


class TestHypothesisPhrasing:
    def test_multi_member_cohort_phrasing(self) -> None:
        card = build_test_card(bet=_bet(member_count=3), resolved_names=["X"], city="London")
        assert "3 scored entities" in card.audience_hypothesis
        assert "does not establish that these entities are a local audience" in card.audience_hypothesis
        assert "audience exists" not in card.audience_hypothesis

    def test_single_member_cohort_never_says_zero_similar(self) -> None:
        card = build_test_card(bet=_bet(member_count=1), resolved_names=["X"], city="London")
        assert "0 similar" not in card.audience_hypothesis
        assert "1 scored entity contributed" in card.audience_hypothesis
        assert "does not establish that these entities are a local audience" in card.audience_hypothesis


class TestExclusionsSurfaced:
    """Exclusions are annotations, never deletions (reasons.py) — the API must
    surface them so the reader can disagree."""

    def _demo_result(self) -> dict:
        client = TestClient(app)
        run_id = client.post("/run/demo").json()["run_id"]
        deadline = time.time() + 30
        while time.time() < deadline:
            payload = client.get(f"/run/{run_id}").json()
            if payload["status"] in {"completed", "failed", "insufficient"}:
                break
            time.sleep(0.05)
        assert payload["status"] == "completed"
        return payload["result"]

    def test_ranked_cohorts_expose_exclusions_and_qualifying_count(self) -> None:
        result = self._demo_result()
        ranked = result["cohorts"]["ranked"]
        assert ranked, "fixture demo must produce ranked cohorts"
        for cohort in ranked:
            assert "qualifying_count" in cohort
            assert isinstance(cohort["excluded_members"], list)
            assert cohort["qualifying_count"] <= cohort["member_count"]
            for excluded in cohort["excluded_members"]:
                assert excluded["reason_code"]  # every exclusion carries a reason

    def test_fixture_demo_surfaces_the_link_and_actionability_fields(self) -> None:
        result = self._demo_result()
        bet = result["programme_bet"]
        card = result["test_card"]
        assert bet["primary"]["cohort_id"]
        assert bet["primary"]["cohort_id"] == result["cohorts"]["ranked"][0]["cohort_id"]
        assert card["provenance"]["primary_cohort_id"] == bet["primary"]["cohort_id"]
        assert card["success_criteria"] and card["observation_window"]
        # Fixture labelling must survive the additions.
        assert result["data_status"] == "fixture"
        assert bet["data_status"] == "fixture"
        assert card["data_status"] == "fixture"
