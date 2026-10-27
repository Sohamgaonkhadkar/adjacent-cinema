"""Audience Pulse — creation, ballot, dedupe, freeze, aggregation, evaluation.

The properties pinned here are the ones a poll feature gets wrong:

* a definition validated as a whole (window, rule, options) before anything is
  stored;
* the rule and hypothesis frozen when the first response arrives, enforced by
  the database rather than by convention;
* one stored response per browsing session, and an unguessable token as the
  only credential a participant holds;
* counts that are real counts, with an empty poll reported as zero responses
  rather than as missing data;
* INCONCLUSIVE below the creator's own minimum sample — never SUPPORTED from a
  handful of votes;
* the participant payload never carrying owner data (experiment id, hypothesis,
  decision rule, or live totals while collection is open).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from app.api import creator_routes, pulse_routes
from app.domain.experiment_repository import ExperimentRepository
from app.domain.pulse import (
    MAX_RESPONSES_PER_POLL,
    PulseValidationError,
    evaluate,
    normalise_definition,
    public_poll,
)
from app.main import app
from fastapi.testclient import TestClient

SHARE_FLAG = "ADJACENT_PULSE_SHARE_ENABLED"


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def _window(days: int = 14, *, started_minutes_ago: int = 5) -> tuple[str, str]:
    now = datetime.now(UTC)
    opens = now - timedelta(minutes=started_minutes_ago)
    return _iso(opens), _iso(opens + timedelta(days=days))


def _definition(**overrides: Any) -> dict[str, Any]:
    opens_at, closes_at = overrides.pop("window", _window())
    payload = {
        "question": "Would you watch this at a Friday late show?",
        "options": [{"label": "Yes"}, {"label": "No"}, {"label": "Not sure"}],
        "opens_at": opens_at,
        "closes_at": closes_at,
        "decision_rule": {
            "kind": "option_share_at_least",
            "option_id": "opt-1",
            "threshold": 0.6,
            "min_responses": 10,
        },
    }
    payload.update(overrides)
    return payload


def _poll_row(db_path: Path, poll_id: str) -> sqlite3.Row:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            "SELECT * FROM pulse_polls WHERE poll_id = ?", (poll_id,)
        ).fetchone()
    finally:
        connection.close()


@pytest.fixture()
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "experiments.db"
    creator_routes.reset_repo_for_tests(path)
    pulse_routes.reset_pulse_limits_for_tests()
    monkeypatch.setenv(SHARE_FLAG, "1")
    monkeypatch.setenv("ADJACENT_PULSE_COOKIE_SECURE", "0")
    monkeypatch.delenv("ADJACENT_PUBLIC_DEMO", raising=False)
    yield path
    creator_routes.reset_repo_for_tests(None)
    pulse_routes.reset_pulse_limits_for_tests()


@pytest.fixture()
def client(db_path: Path) -> TestClient:
    return TestClient(app)


def _experiment(client: TestClient, request_id: str = "exp-req-0001") -> dict[str, Any]:
    response = client.post(
        "/experiments",
        json={
            "request_id": request_id,
            "film_title": "Night Harbour",
            "hypothesis": "Artist-led framing reaches a late-show audience.",
            "success_criteria": "Most respondents say yes.",
            "observation_window": "Two weeks after the first screening.",
            "action_plan": "Book one late show and ask the room.",
            "data_status": "fixture",
            "source_run_id": f"run-{request_id}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["experiment"]


def _create_poll(
    client: TestClient, experiment_id: str, request_id: str = "poll-req-0001", **overrides: Any
) -> dict[str, Any]:
    body = {"request_id": request_id, **_definition(**overrides)}
    response = client.post(f"/experiments/{experiment_id}/pulse", json=body)
    return response


# ---------------------------------------------------------------------------
# Creation and validation
# ---------------------------------------------------------------------------


class TestCreation:
    def test_creates_a_poll_with_a_share_token_and_frozen_snapshot(
        self, client: TestClient
    ) -> None:
        experiment = _experiment(client)
        response = _create_poll(client, experiment["experiment_id"])
        assert response.status_code == 201, response.text
        payload = response.json()
        poll = payload["poll"]

        assert payload["duplicate"] is False
        assert poll["question"].startswith("Would you watch this")
        assert [option["option_id"] for option in poll["options"]] == ["opt-1", "opt-2", "opt-3"]
        assert poll["hypothesis"] == experiment["hypothesis"]
        assert poll["experiment_snapshot"]["source_run_id"] == experiment["source_run_id"]
        assert poll["definition_frozen"] is False
        assert poll["collection"]["status"] == "OPEN"
        assert poll["response_count"] == 0
        assert poll["decision_rule"]["statement"].startswith("SUPPORTED when 60%")
        assert len(poll["share_token"]) >= 32
        assert payload["share_path"] == f"/pulse/{poll['share_token']}"

    def test_replaying_the_creation_request_returns_the_same_poll(
        self, client: TestClient
    ) -> None:
        experiment = _experiment(client)
        first = _create_poll(client, experiment["experiment_id"]).json()
        second = _create_poll(client, experiment["experiment_id"]).json()
        assert second["duplicate"] is True
        assert second["poll"]["poll_id"] == first["poll"]["poll_id"]

    @pytest.mark.parametrize(
        ("overrides", "expected"),
        [
            ({"question": "   "}, "question must not be empty"),
            ({"question": "x" * 241}, "at most 240 characters"),
            (
                {"options": [{"label": "Yes"}, {"label": "yes"}]},
                "listed twice",
            ),
            ({"options": [{"label": "Only one"}, {"label": ""}]}, "at least 1 character"),
            (
                {"options": [{"label": f"Option {i}"} for i in range(6)]},
                "at most 5 items",
            ),
            (
                {"decision_rule": {"option_id": "opt-9", "threshold": 0.5, "min_responses": 10}},
                "must name one of this poll's options",
            ),
            (
                {"decision_rule": {"option_id": "opt-1", "threshold": 0.0, "min_responses": 10}},
                "greater than 0",
            ),
            (
                {"decision_rule": {"option_id": "opt-1", "threshold": 0.6, "min_responses": 3}},
                "greater than or equal to 5",
            ),
            ({"window": (_iso(datetime.now(UTC)), _iso(datetime.now(UTC)))}, "at least 1 hour"),
            (
                {"closed_window": True},
                "still be in the future",
            ),
        ],
    )
    def test_rejects_invalid_definitions(
        self, client: TestClient, overrides: dict[str, Any], expected: str
    ) -> None:
        experiment = _experiment(client)
        if overrides.pop("closed_window", False):
            now = datetime.now(UTC)
            overrides["window"] = (_iso(now - timedelta(days=2)), _iso(now - timedelta(days=1)))
        response = _create_poll(client, experiment["experiment_id"], **overrides)
        assert response.status_code == 422, response.text
        # FastAPI reports model-level rejections as a list and domain-level ones
        # as a string; both must name the reason a creator can act on.
        assert expected.lower() in str(response.json()["detail"]).lower()

    def test_window_shorter_than_an_hour_is_rejected(self) -> None:
        opens = datetime.now(UTC) - timedelta(minutes=1)
        with pytest.raises(PulseValidationError, match="at least 1 hour"):
            normalise_definition(
                question="Q",
                options=["A", "B"],
                opens_at=_iso(opens),
                closes_at=_iso(opens + timedelta(minutes=30)),
                decision_rule={"option_id": "opt-1", "threshold": 0.5},
            )

    def test_naive_timestamps_are_rejected(self) -> None:
        with pytest.raises(PulseValidationError, match="timezone offset"):
            normalise_definition(
                question="Q",
                options=["A", "B"],
                opens_at="2026-01-01T00:00:00",
                closes_at="2026-01-02T00:00:00",
                decision_rule={"option_id": "opt-1", "threshold": 0.5},
            )

    def test_a_second_open_poll_for_the_same_experiment_is_rejected(
        self, client: TestClient
    ) -> None:
        experiment = _experiment(client)
        assert _create_poll(client, experiment["experiment_id"]).status_code == 201
        second = _create_poll(client, experiment["experiment_id"], request_id="poll-req-0002")
        assert second.status_code == 422
        assert "already has a poll accepting responses" in second.json()["detail"]

    def test_polls_are_bounded_per_experiment(self, client: TestClient) -> None:
        experiment = _experiment(client)
        experiment_id = experiment["experiment_id"]
        repo = creator_routes.get_repo()
        for index in range(3):
            body = _definition(**{"window": _window(days=3)})
            poll = repo.create_poll(
                experiment_id,
                request_id=f"poll-bound-{index}",
                question=f"Question {index}?",
                options=body["options"],
                opens_at=body["opens_at"],
                closes_at=body["closes_at"],
                decision_rule=body["decision_rule"],
            )
            repo.close_poll(poll["poll_id"])
        with pytest.raises(PulseValidationError, match="bound for one saved decision"):
            repo.create_poll(
                experiment_id,
                request_id="poll-bound-4",
                question="One too many?",
                options=body["options"],
                opens_at=body["opens_at"],
                closes_at=body["closes_at"],
                decision_rule=body["decision_rule"],
            )

    def test_unknown_experiment_is_a_404(self, client: TestClient) -> None:
        response = _create_poll(client, "does-not-exist")
        assert response.status_code == 404

    def test_creation_refuses_when_share_links_are_disabled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        experiment = _experiment(client)
        monkeypatch.delenv(SHARE_FLAG)
        response = _create_poll(client, experiment["experiment_id"])
        assert response.status_code == 503
        assert "ADJACENT_PULSE_SHARE_ENABLED" in response.json()["detail"]
        # Nothing was stored behind the refusal.
        listed = client.get(f"/experiments/{experiment['experiment_id']}/pulse").json()
        assert listed["polls"] == []


# ---------------------------------------------------------------------------
# The participant ballot
# ---------------------------------------------------------------------------


class TestParticipantBallot:
    def test_share_page_shows_the_ballot_and_hides_owner_data(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]

        page = client.get(f"/pulse/share/{token}")
        assert page.status_code == 200
        payload = page.json()
        assert payload["question"] == created["poll"]["question"]
        assert [option["label"] for option in payload["options"]] == ["Yes", "No", "Not sure"]
        assert payload["collection"]["status"] == "OPEN"
        assert payload["already_responded"] is False

        serialised = str(payload)
        assert experiment["experiment_id"] not in serialised
        assert "Artist-led framing" not in serialised
        assert "decision_rule" not in payload
        # Totals stay hidden while collection is open: early counts bias votes.
        assert "counts" not in payload
        assert "Set-Cookie" in page.headers or page.cookies.get(pulse_routes.PULSE_COOKIE)

    def test_session_cookie_is_httponly_and_lax(self, client: TestClient) -> None:
        experiment = _experiment(client)
        token = _create_poll(client, experiment["experiment_id"]).json()["poll"]["share_token"]
        page = client.get(f"/pulse/share/{token}")
        raw_cookie = page.headers["set-cookie"]
        assert pulse_routes.PULSE_COOKIE in raw_cookie
        assert "HttpOnly" in raw_cookie
        assert "SameSite=lax" in raw_cookie.lower().replace("samesite=lax", "SameSite=lax")

    def test_unknown_token_is_a_404(self, client: TestClient) -> None:
        assert client.get("/pulse/share/not-a-real-token").status_code == 404

    def test_share_routes_are_absent_when_disabled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        experiment = _experiment(client)
        token = _create_poll(client, experiment["experiment_id"]).json()["poll"]["share_token"]
        monkeypatch.delenv(SHARE_FLAG)
        assert client.get(f"/pulse/share/{token}").status_code == 404
        assert (
            client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"}).status_code
            == 404
        )

    def test_valid_response_is_stored_with_a_timestamp(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]
        client.get(f"/pulse/share/{token}")

        submitted = client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-2"})
        assert submitted.status_code == 201, submitted.text
        assert submitted.json()["recorded"] is True
        assert submitted.json()["submitted_at"]

        owner = client.get(
            f"/experiments/{experiment['experiment_id']}/pulse/{created['poll']['poll_id']}"
        ).json()
        assert owner["poll"]["response_count"] == 1
        assert owner["responses"][0]["option_id"] == "opt-2"
        # No respondent identity is ever returned.
        assert "respondent_key" not in owner["responses"][0]

    def test_response_without_the_session_cookie_is_refused(self, client: TestClient) -> None:
        experiment = _experiment(client)
        token = _create_poll(client, experiment["experiment_id"]).json()["poll"]["share_token"]
        # A fresh client has never opened the share page, so it holds no session:
        # this is also what a cross-site POST looks like (SameSite=Lax).
        fresh = TestClient(app)
        response = fresh.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"})
        assert response.status_code == 400
        assert "Open the poll link" in response.json()["detail"]

    def test_unknown_option_is_refused_and_nothing_is_stored(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]
        client.get(f"/pulse/share/{token}")

        bad = client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-9"})
        assert bad.status_code == 422
        owner = client.get(
            f"/experiments/{experiment['experiment_id']}/pulse/{created['poll']['poll_id']}"
        ).json()
        assert owner["poll"]["response_count"] == 0

    def test_a_second_response_from_the_same_session_is_refused(
        self, client: TestClient
    ) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]
        client.get(f"/pulse/share/{token}")

        first = client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"})
        second = client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-3"})
        assert first.status_code == 201
        assert second.status_code == 409
        assert second.json()["detail"]["already_responded"] is True

        owner = client.get(
            f"/experiments/{experiment['experiment_id']}/pulse/{created['poll']['poll_id']}"
        ).json()
        assert owner["poll"]["response_count"] == 1
        assert owner["poll"]["counts"]["options"][0]["count"] == 1

    def test_a_different_session_is_a_different_response(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]

        first = TestClient(app)
        second = TestClient(app)
        for browser, option in ((first, "opt-1"), (second, "opt-2")):
            browser.get(f"/pulse/share/{token}")
            assert (
                browser.post(
                    f"/pulse/share/{token}/responses", json={"option_id": option}
                ).status_code
                == 201
            )

        owner = client.get(
            f"/experiments/{experiment['experiment_id']}/pulse/{created['poll']['poll_id']}"
        ).json()
        assert owner["poll"]["response_count"] == 2
        assert {option["option_id"]: option["count"] for option in owner["poll"]["counts"]["options"]}[
            "opt-1"
        ] == 1

    def test_closed_poll_refuses_responses_and_says_so(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]
        client.get(f"/pulse/share/{token}")
        closed = client.post(
            f"/experiments/{experiment['experiment_id']}/pulse/{created['poll']['poll_id']}/close"
        )
        assert closed.status_code == 200
        assert closed.json()["poll"]["collection"]["status"] == "CLOSED"

        refused = client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"})
        assert refused.status_code == 409
        assert refused.json()["detail"]["collection"]["status"] == "CLOSED"
        # Closed polls may show their totals to participants.
        assert client.get(f"/pulse/share/{token}").json()["counts"]["total"] == 0

    def test_expired_poll_refuses_responses(self, client: TestClient, db_path: Path) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]
        client.get(f"/pulse/share/{token}")

        # Move the window into the past, exactly as time would.
        past = _iso(datetime.now(UTC) - timedelta(days=1))
        connection = sqlite3.connect(str(db_path))
        try:
            connection.execute(
                "UPDATE pulse_polls SET closes_at = ? WHERE poll_id = ?",
                (past, created["poll"]["poll_id"]),
            )
            connection.commit()
        finally:
            connection.close()

        page = client.get(f"/pulse/share/{token}")
        assert page.json()["collection"]["status"] == "EXPIRED"
        refused = client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"})
        assert refused.status_code == 409

    def test_scheduled_poll_accepts_nothing_yet(self, client: TestClient) -> None:
        experiment = _experiment(client)
        opens = datetime.now(UTC) + timedelta(days=1)
        created = _create_poll(
            client,
            experiment["experiment_id"],
            window=(_iso(opens), _iso(opens + timedelta(days=7))),
        ).json()
        token = created["poll"]["share_token"]
        client.get(f"/pulse/share/{token}")
        refused = client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"})
        assert refused.status_code == 409
        assert refused.json()["detail"]["collection"]["status"] == "SCHEDULED"

    def test_response_ceiling_is_enforced(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.domain.pulse_repository.MAX_RESPONSES_PER_POLL", 1, raising=True
        )
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]

        first = TestClient(app)
        first.get(f"/pulse/share/{token}")
        assert (
            first.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"}).status_code
            == 201
        )
        second = TestClient(app)
        second.get(f"/pulse/share/{token}")
        assert (
            second.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-2"}).status_code
            == 429
        )

    def test_response_rate_limit_returns_retry_after(self, client: TestClient) -> None:
        experiment = _experiment(client)
        token = _create_poll(client, experiment["experiment_id"]).json()["poll"]["share_token"]
        limiter = pulse_routes.PublicDemoLimiter(
            client_limit=0, global_limit=0, max_active=0, window_seconds=60.0
        )
        original = pulse_routes._RESPONSE_LIMITER
        pulse_routes._RESPONSE_LIMITER = limiter
        try:
            response = client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"})
        finally:
            pulse_routes._RESPONSE_LIMITER = original
        assert response.status_code == 429
        assert response.headers["retry-after"]


# ---------------------------------------------------------------------------
# Immutability of the pre-registered definition
# ---------------------------------------------------------------------------


class TestDefinitionFreeze:
    def test_first_response_freezes_the_definition(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        poll_id = created["poll"]["poll_id"]
        token = created["poll"]["share_token"]
        assert created["poll"]["definition_frozen"] is False

        client.get(f"/pulse/share/{token}")
        client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"})

        owner = client.get(
            f"/experiments/{experiment['experiment_id']}/pulse/{poll_id}"
        ).json()
        assert owner["poll"]["definition_frozen"] is True
        assert owner["poll"]["frozen_at"]

    def test_the_database_refuses_to_rewrite_a_frozen_rule(
        self, client: TestClient, db_path: Path
    ) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]
        client.get(f"/pulse/share/{token}")
        client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"})

        connection = sqlite3.connect(str(db_path))
        try:
            with pytest.raises(sqlite3.IntegrityError, match="frozen"):
                connection.execute(
                    "UPDATE pulse_polls SET decision_rule = ? WHERE poll_id = ?",
                    ('{"threshold": 0.01}', created["poll"]["poll_id"]),
                )
            with pytest.raises(sqlite3.IntegrityError, match="frozen"):
                connection.execute(
                    "UPDATE pulse_polls SET hypothesis = 'something easier to pass' "
                    "WHERE poll_id = ?",
                    (created["poll"]["poll_id"],),
                )
        finally:
            connection.close()

        row = _poll_row(db_path, created["poll"]["poll_id"])
        # The stored rule is byte-identical to the one that was registered.
        assert '"threshold": 0.6' in row["decision_rule"]
        assert '"min_responses": 10' in row["decision_rule"]
        assert row["hypothesis"] == experiment["hypothesis"]

    def test_closing_a_poll_does_not_touch_the_definition(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]
        client.get(f"/pulse/share/{token}")
        client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-3"})
        closed = client.post(
            f"/experiments/{experiment['experiment_id']}/pulse/{created['poll']['poll_id']}/close"
        ).json()
        assert closed["poll"]["decision_rule"] == created["poll"]["decision_rule"]
        assert closed["poll"]["question"] == created["poll"]["question"]
        assert closed["poll"]["counts"]["total"] == 1


# ---------------------------------------------------------------------------
# Aggregation and evaluation
# ---------------------------------------------------------------------------


class TestEvaluation:
    def _answer(
        self, client: TestClient, token: str, option_id: str, count: int
    ) -> None:
        for _ in range(count):
            browser = TestClient(app)
            browser.get(f"/pulse/share/{token}")
            submitted = browser.post(
                f"/pulse/share/{token}/responses", json={"option_id": option_id}
            )
            assert submitted.status_code == 201, submitted.text

    def test_zero_responses_is_inconclusive_not_a_failure(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        evaluation = client.post(
            f"/experiments/{experiment['experiment_id']}/pulse/"
            f"{created['poll']['poll_id']}/evaluate",
            json={"request_id": "eval-req-0001"},
        )
        body = evaluation.json()["evaluation"]
        assert evaluation.status_code == 201
        assert body["outcome"] == "INCONCLUSIVE"
        assert "No responses were recorded" in body["rationale"]
        assert body["sample_size"] == 0

    def test_below_the_minimum_is_inconclusive_even_with_a_landslide(
        self, client: TestClient
    ) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        self._answer(client, created["poll"]["share_token"], "opt-1", 4)

        body = client.post(
            f"/experiments/{experiment['experiment_id']}/pulse/"
            f"{created['poll']['poll_id']}/evaluate",
            json={"request_id": "eval-req-0002"},
        ).json()["evaluation"]
        assert body["outcome"] == "INCONCLUSIVE"
        assert "requires at least 10" in body["rationale"]
        assert body["sample_size"] == 4

    def test_meeting_the_rule_is_supported(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        self._answer(client, created["poll"]["share_token"], "opt-1", 7)
        self._answer(client, created["poll"]["share_token"], "opt-2", 3)

        body = client.post(
            f"/experiments/{experiment['experiment_id']}/pulse/"
            f"{created['poll']['poll_id']}/evaluate",
            json={"request_id": "eval-req-0003"},
        ).json()["evaluation"]
        assert body["outcome"] == "SUPPORTED"
        assert body["sample_size"] == 10
        assert body["counts"]["total"] == 10
        assert body["rule_applied"]["threshold"] == 0.6
        assert "70%" in body["rationale"]
        assert "not a population estimate" not in body["rationale"]

    def test_missing_the_rule_is_contradicted(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        self._answer(client, created["poll"]["share_token"], "opt-1", 4)
        self._answer(client, created["poll"]["share_token"], "opt-2", 6)

        body = client.post(
            f"/experiments/{experiment['experiment_id']}/pulse/"
            f"{created['poll']['poll_id']}/evaluate",
            json={"request_id": "eval-req-0004"},
        ).json()["evaluation"]
        assert body["outcome"] == "CONTRADICTED"
        assert "below the 60% bar" in body["rationale"]

    def test_evaluations_are_append_only_with_a_supersedes_chain(
        self, client: TestClient
    ) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        poll_id = created["poll"]["poll_id"]
        self._answer(client, created["poll"]["share_token"], "opt-1", 2)

        first = client.post(
            f"/experiments/{experiment['experiment_id']}/pulse/{poll_id}/evaluate",
            json={"request_id": "eval-req-0005"},
        ).json()["evaluation"]
        self._answer(client, created["poll"]["share_token"], "opt-1", 9)
        second = client.post(
            f"/experiments/{experiment['experiment_id']}/pulse/{poll_id}/evaluate",
            json={"request_id": "eval-req-0006"},
        ).json()["evaluation"]

        assert first["outcome"] == "INCONCLUSIVE"
        assert second["outcome"] == "SUPPORTED"
        assert second["supersedes_id"] == first["evaluation_id"]

        detail = client.get(
            f"/experiments/{experiment['experiment_id']}/pulse/{poll_id}"
        ).json()
        assert [item["outcome"] for item in detail["evaluations"]] == [
            "INCONCLUSIVE",
            "SUPPORTED",
        ]
        assert detail["poll"]["latest_evaluation"]["evaluation_id"] == second["evaluation_id"]

    def test_replaying_an_evaluation_returns_the_same_record(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        url = (
            f"/experiments/{experiment['experiment_id']}/pulse/"
            f"{created['poll']['poll_id']}/evaluate"
        )
        first = client.post(url, json={"request_id": "eval-req-0007"}).json()
        replay = client.post(url, json={"request_id": "eval-req-0007"}).json()
        assert replay["duplicate"] is True
        assert replay["evaluation"]["evaluation_id"] == first["evaluation"]["evaluation_id"]

        detail = client.get(
            f"/experiments/{experiment['experiment_id']}/pulse/"
            f"{created['poll']['poll_id']}"
        ).json()
        assert len(detail["evaluations"]) == 1

    def test_preview_tracks_the_stored_responses_without_persisting(
        self, client: TestClient
    ) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        self._answer(client, created["poll"]["share_token"], "opt-1", 3)
        detail = client.get(
            f"/experiments/{experiment['experiment_id']}/pulse/"
            f"{created['poll']['poll_id']}"
        ).json()
        assert detail["poll"]["evaluation_preview"]["outcome"] == "INCONCLUSIVE"
        assert detail["poll"]["evaluation_preview"]["sample_size"] == 3
        assert detail["evaluations"] == []

    def test_evaluation_states_the_sample_limits(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        body = client.post(
            f"/experiments/{experiment['experiment_id']}/pulse/"
            f"{created['poll']['poll_id']}/evaluate",
            json={"request_id": "eval-req-0008"},
        ).json()["evaluation"]
        text = str(body).lower()
        assert "self-selected" in text
        for forbidden in ("probability", "confidence interval", "statistically significant"):
            assert forbidden not in text

    def test_pure_evaluate_reports_share_and_minimum(self) -> None:
        poll = {
            "poll_id": "p",
            "experiment_id": "e",
            "options": [
                {"option_id": "opt-1", "label": "Yes"},
                {"option_id": "opt-2", "label": "No"},
            ],
            "decision_rule": {
                "option_id": "opt-1",
                "option_label": "Yes",
                "threshold": 0.5,
                "min_responses": 5,
            },
            "opens_at": _iso(datetime.now(UTC) - timedelta(days=1)),
            "closes_at": _iso(datetime.now(UTC) + timedelta(days=1)),
        }
        responses = [{"option_id": "opt-1"}] * 3 + [{"option_id": "opt-2"}] * 2
        result = evaluate(poll, responses)
        assert result["outcome"] == "SUPPORTED"
        assert result["share"] == pytest.approx(0.6)
        assert result["counts"]["by_option"] == {"opt-1": 3, "opt-2": 2}

        fewer = evaluate(poll, responses[:4])
        assert fewer["outcome"] == "INCONCLUSIVE"
        assert fewer["remaining_evidence"][0].startswith("1 more valid response")

    def test_ids_cannot_be_mixed_across_experiments(self, client: TestClient) -> None:
        first = _experiment(client, request_id="exp-req-0010")
        second = _experiment(client, request_id="exp-req-0011")
        poll = _create_poll(client, first["experiment_id"]).json()["poll"]

        wrong = client.get(f"/experiments/{second['experiment_id']}/pulse/{poll['poll_id']}")
        assert wrong.status_code == 404
        assert (
            client.post(
                f"/experiments/{second['experiment_id']}/pulse/{poll['poll_id']}/evaluate",
                json={"request_id": "eval-req-0010"},
            ).status_code
            == 404
        )


# ---------------------------------------------------------------------------
# Persistence and public-demo boundaries
# ---------------------------------------------------------------------------


class TestPersistenceAndBoundaries:
    def test_polls_and_responses_survive_a_repository_reopen(
        self, client: TestClient, db_path: Path
    ) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]
        client.get(f"/pulse/share/{token}")
        client.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-2"})

        creator_routes.reset_repo_for_tests(None)
        reopened = ExperimentRepository(db_path)
        try:
            poll = reopened.get_poll_by_token(token)
            assert poll is not None
            assert poll["response_count"] == 1
            assert poll["counts"]["options"][1]["count"] == 1
            assert poll["definition_frozen"] is True
        finally:
            reopened.close()

    def test_public_demo_blocks_owner_polls_and_the_disabled_share_surface(
        self, db_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.delenv(SHARE_FLAG, raising=False)
        guarded = TestClient(app)
        # Owner routes stay outside the public allowlist.
        assert guarded.post("/experiments/anything/pulse", json={}).status_code in {403, 404, 405}
        assert guarded.get("/experiments").status_code in {403, 404}
        # And the participant routes are not served while sharing is off.
        assert guarded.get("/pulse/share/anything").status_code in {403, 404}

    def test_public_demo_serves_the_ballot_when_the_operator_opt_in(
        self, db_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Create the poll as the owner first (public demo is off for this call).
        owner = TestClient(app)
        experiment = _experiment(owner)
        created = _create_poll(owner, experiment["experiment_id"]).json()
        token = created["poll"]["share_token"]

        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        monkeypatch.setenv(SHARE_FLAG, "1")
        public = TestClient(app)
        page = public.get(f"/pulse/share/{token}")
        assert page.status_code == 200
        assert page.json()["question"] == created["poll"]["question"]

        submitted = public.post(f"/pulse/share/{token}/responses", json={"option_id": "opt-1"})
        assert submitted.status_code == 201
        # The owner surface is still blocked in public demo mode.
        assert public.get("/experiments").status_code in {403, 404}

    def test_public_poll_never_names_the_experiment(self, client: TestClient) -> None:
        experiment = _experiment(client)
        created = _create_poll(client, experiment["experiment_id"]).json()
        poll = creator_routes.get_repo().get_poll(created["poll"]["poll_id"])
        payload = public_poll(poll)
        assert set(payload) == {
            "schema",
            "question",
            "options",
            "opens_at",
            "closes_at",
            "collection",
            "limitations",
        }
        assert experiment["experiment_id"] not in str(payload)
        assert "hypothesis" not in payload

    def test_response_ceiling_matches_the_documented_bound(self) -> None:
        assert MAX_RESPONSES_PER_POLL == 5000


def test_an_older_database_gains_the_limitations_column(tmp_path: Path) -> None:
    """Schema additions must reach databases created by an earlier build.

    The repository only issues ``CREATE TABLE IF NOT EXISTS``, so a column added
    later has to be migrated explicitly — otherwise reading an old evaluation
    would raise instead of returning its stored result.
    """
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(str(path))
    try:
        connection.executescript(
            """
            CREATE TABLE pulse_evaluations (
                evaluation_id     TEXT PRIMARY KEY,
                poll_id           TEXT NOT NULL,
                request_id        TEXT NOT NULL UNIQUE,
                created_at        TEXT NOT NULL,
                outcome           TEXT NOT NULL,
                rationale         TEXT NOT NULL,
                rule_applied      TEXT NOT NULL,
                counts            TEXT NOT NULL,
                sample_size       INTEGER NOT NULL,
                collection_status TEXT NOT NULL,
                supersedes_id     TEXT
            );
            """
        )
        connection.execute(
            """INSERT INTO pulse_evaluations (evaluation_id, poll_id, request_id, created_at,
               outcome, rationale, rule_applied, counts, sample_size, collection_status,
               supersedes_id) VALUES ('e1','p1','r1','2026-01-01T00:00:00+00:00','INCONCLUSIVE',
               'no responses','{}','{"total": 0, "options": [], "unrecognised": 0}',0,'OPEN',NULL)"""
        )
        connection.commit()
    finally:
        connection.close()

    repo = ExperimentRepository(path)
    try:
        columns = {row[1] for row in repo._conn.execute("PRAGMA table_info(pulse_evaluations)")}
        assert "limitations" in columns
        stored = repo._poll_evaluation_dict("e1")
        assert stored["outcome"] == "INCONCLUSIVE"
        assert stored["limitations"] == []
    finally:
        repo.close()
