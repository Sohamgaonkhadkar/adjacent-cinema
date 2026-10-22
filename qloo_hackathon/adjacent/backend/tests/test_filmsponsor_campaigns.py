"""FilmSponsor campaign lifecycle tests (offline; transport doubles only).

Covers: campaign intake idempotency, honest unavailable-service discovery
(no fixture substitution), evidence-backed discovery semantics (typed brands
only, zero ≠ missing, ambiguous films preserved and never promoted), safe
error projection, versioned drafts, source-review-before-approval, approval-
gated export, outreach outcome recording with corrections, and the public-
demo 403 boundary. No test performs network I/O.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.api import filmsponsor_routes
from app.domain.brand_discovery import (
    INTERPRETATION_LIMITS,
    DiscoveryOutcome,
    FilmInput,
    discover_brand_evidence,
)
from app.main import app
from app.resolution.contract import MatchStatus
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Doubles
# ---------------------------------------------------------------------------


def _entity(
    entity_id: str,
    *,
    name: str,
    entity_types: tuple[str, ...] = ("urn:entity:brand",),
    affinity: float | None = 0.31,
    popularity: float | None = 0.5,
) -> SimpleNamespace:
    raw = {"name": name, "types": list(entity_types)}
    return SimpleNamespace(
        entity_id=entity_id,
        name=name,
        type=entity_types[0] if entity_types else None,
        subtype=None,
        affinity=affinity,
        band="Medium",
        popularity=popularity,
        raw=raw,
    )


def _resolved(
    title: str,
    *,
    status: MatchStatus = MatchStatus.VERIFIED,
    entity_id: str | None = "urn:entity:movie:batman",
    year: int | None = 2008,
) -> SimpleNamespace:
    return SimpleNamespace(
        input_title=title,
        input_year=year,
        input_external_id=None,
        input_external_family=None,
        qloo_entity_id=entity_id if status == MatchStatus.VERIFIED else None,
        qloo_name=title if status == MatchStatus.VERIFIED else None,
        qloo_entity_type="urn:entity:movie" if status == MatchStatus.VERIFIED else None,
        qloo_year=year if status == MatchStatus.VERIFIED else None,
        match_status=status,
        match_method="search",
        verification_notes=["title/year verified"] if status == MatchStatus.VERIFIED else ["not verified"],
        resolved=status == MatchStatus.VERIFIED,
        call_id="call-resolve-1",
        related_call_ids=["call-resolve-2"],
    )


class _FakeClient:
    """In-memory transport double; records calls, returns canned responses."""

    def __init__(self, *, tags=None, insights=None, raise_kind: str | None = None):
        self._tags = tags or []
        self._insights = insights or []
        self._raise_kind = raise_kind
        self.calls: list[tuple[str, dict]] = []

    async def tags(self, **kwargs):
        self.calls.append(("tags", kwargs))
        if self._raise_kind == "tags":
            raise RuntimeError("raw upstream secret body must never surface")
        return SimpleNamespace(results=self._tags, call_id=f"call-tags-{len(self.calls)}")

    async def insights(self, **kwargs):
        self.calls.append(("insights", kwargs))
        if self._raise_kind == "insights":
            raise RuntimeError("raw upstream secret body must never surface")
        return SimpleNamespace(results=self._insights, call_id=f"call-insights-{len(self.calls)}")


class _FakeResolver:
    def __init__(self, results: list[SimpleNamespace]):
        self._results = results
        self.calls: list[tuple] = []

    async def resolve_item(self, title, year=None, external_id=None, external_family=None):
        self.calls.append((title, year, external_id, external_family))
        return self._results[0]


# ---------------------------------------------------------------------------
# Domain semantics
# ---------------------------------------------------------------------------


class TestBrandDiscoverySemantics:
    def test_verified_films_yield_typed_brands_with_limits_and_call_ids(self):
        client = _FakeClient(
            tags=[SimpleNamespace(tag_id="urn:tag:superhero", name="superhero")],
            insights=[
                _entity("urn:entity:brand:1", name="Brand One", affinity=0.42),
                _entity("urn:entity:brand:2", name="Brand Two", affinity=0.0),  # valid zero
                _entity("urn:entity:movie:9", name="Not A Brand", entity_types=("urn:entity:movie",)),
            ],
        )
        resolver = _FakeResolver([_resolved("The Dark Knight")])
        outcome = asyncio.run(
            discover_brand_evidence(
                client=client,
                resolver=resolver,
                films=[FilmInput(title="The Dark Knight", year=2008)],
                themes=["superhero"],
            )
        )
        report = outcome.report
        assert outcome.data_status == "measured"
        names = {b["name"] for b in report["brands"]}
        assert names == {"Brand One", "Brand Two"}
        # Each candidate carries per-query observations with their own provenance.
        zero = next(b for b in report["brands"] if b["name"] == "Brand Two")
        assert all(o["affinity"] == 0.0 for o in zero["observations"])  # valid zero preserved
        assert all(o["call_id"] for o in zero["observations"])
        one = next(b for b in report["brands"] if b["name"] == "Brand One")
        assert {o["source"] for o in one["observations"]} == {
            "brand_from_films",
            "brand_from_tags",
        }
        # Non-brand-typed results are reported separately, never presented as brands.
        assert [o["name"] for o in report["non_brand_results"]] == ["Not A Brand"]
        assert report["non_brand_results"][0]["reason_code"] == "not_brand_typed"
        assert report["interpretation_limits"] == INTERPRETATION_LIMITS
        assert report["call_ids"]  # provenance retained
        assert report["empty"] is False

    def test_missing_affinity_stays_missing(self):
        client = _FakeClient(
            insights=[_entity("urn:entity:brand:1", name="No Score", affinity=None)]
        )
        resolver = _FakeResolver([_resolved("The Dark Knight")])
        outcome = asyncio.run(
            discover_brand_evidence(
                client=client,
                resolver=resolver,
                films=[FilmInput(title="The Dark Knight", year=2008)],
                themes=[],
            )
        )
        row = outcome.report["brands"][0]
        assert row["observations"][0]["affinity"] is None  # missing ≠ zero

    def test_ambiguous_film_is_preserved_but_never_promoted(self):
        client = _FakeClient(insights=[_entity("urn:entity:brand:1", name="Brand One")])
        resolver = _FakeResolver([_resolved("Taipei Story", status=MatchStatus.AMBIGUOUS)])
        outcome = asyncio.run(
            discover_brand_evidence(
                client=client,
                resolver=resolver,
                films=[FilmInput(title="Taipei Story", year=1985)],
                themes=[],
            )
        )
        report = outcome.report
        film = report["films"][0]
        assert film["match_status"] == "AMBIGUOUS"
        assert film["usable"] is False
        assert film["candidate"] is None
        # No brand signal may be seeded from an unusable film.
        stage = report["stages"]["brand_from_verified_films"]
        assert stage["status"] == "EMPTY"
        insights_calls = [c for c in client.calls if c[0] == "insights"]
        assert insights_calls == []

    def test_malformed_optional_tag_fields_are_ignored_safely(self):
        client = _FakeClient(tags=[
            SimpleNamespace(tag_id="urn:tag:bad", name=17),
            SimpleNamespace(tag_id=None, name="superhero"),
        ])
        resolver = _FakeResolver([_resolved("The Dark Knight")])
        outcome = asyncio.run(discover_brand_evidence(
            client=client,
            resolver=resolver,
            films=[FilmInput(title="The Dark Knight", year=2008)],
            themes=["superhero"],
        ))
        assert outcome.report["theme_canonicalization"][0]["canonical_tag"] is None
        assert outcome.report["stages"]["theme_canonicalization"]["exact_unique_tags"] == 0

    def test_empty_results_are_an_empty_state_not_an_error(self):
        client = _FakeClient(tags=[], insights=[])
        resolver = _FakeResolver([_resolved("The Dark Knight")])
        outcome = asyncio.run(
            discover_brand_evidence(
                client=client,
                resolver=resolver,
                films=[FilmInput(title="The Dark Knight", year=2008)],
                themes=["nothing-matches"],
            )
        )
        report = outcome.report
        assert report["empty"] is True
        assert report["brands"] == []
        assert "error" not in report or not report.get("halt_reason")

    def test_provider_failure_is_sanitized_and_halts(self):
        client = _FakeClient(insights=[], raise_kind="insights")
        resolver = _FakeResolver([_resolved("The Dark Knight")])
        outcome = asyncio.run(
            discover_brand_evidence(
                client=client,
                resolver=resolver,
                films=[FilmInput(title="The Dark Knight", year=2008)],
                themes=[],
            )
        )
        report = outcome.report
        halt = report.get("halt_reason") or {}
        assert halt.get("error_type") == "RuntimeError"
        blob = str(report)
        assert "raw upstream secret" not in blob  # message text never surfaces
        stage = report["stages"]["brand_from_verified_films"]
        assert stage["error"]["error_type"] == "RuntimeError"

    def test_combined_stage_skipped_when_sets_overlap(self):
        brand = _entity("urn:entity:brand:1", name="Same Brand")
        client = _FakeClient(
            tags=[SimpleNamespace(tag_id="urn:tag:superhero", name="superhero")],
            insights=[brand],
        )
        resolver = _FakeResolver([_resolved("The Dark Knight")])
        outcome = asyncio.run(
            discover_brand_evidence(
                client=client,
                resolver=resolver,
                films=[FilmInput(title="The Dark Knight", year=2008)],
                themes=["superhero"],
            )
        )
        assert outcome.report["stages"]["combined_brand_query"]["status"] == "SKIPPED"
        # Only tags + two seeded insights; no third combined call.
        assert [c[0] for c in client.calls] == ["tags", "insights", "insights"]


# ---------------------------------------------------------------------------
# Repository lifecycle through the API
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("QLOO_API_KEY", raising=False)
    monkeypatch.delenv("ADJACENT_PUBLIC_DEMO", raising=False)
    filmsponsor_routes.reset_filmsponsor_for_tests(tmp_path / "experiments.db")
    with TestClient(app) as test_client:
        yield test_client
    filmsponsor_routes.reset_filmsponsor_for_tests()


def _create_campaign(test_client: TestClient, request_id: str = "campaign-req-0001") -> dict:
    response = test_client.post(
        "/filmsponsor/campaigns",
        json={
            "request_id": request_id,
            "film_title": "Neon Harbour",
            "film_year": 2026,
            "themes": ["isolation", "night workers"],
            "goals": "Find brand partners for the festival premiere.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["campaign"]


class TestCampaignLifecycle:
    def test_campaign_create_and_idempotent_replay(self, client: TestClient):
        campaign = _create_campaign(client)
        replay = client.post(
            "/filmsponsor/campaigns",
            json={"request_id": "campaign-req-0001", "film_title": "Neon Harbour"},
        )
        # Replays follow the existing experiment-route convention: the original
        # record is returned with `duplicate: true`.
        assert replay.status_code == 201
        assert replay.json()["duplicate"] is True
        assert replay.json()["campaign"]["campaign_id"] == campaign["campaign_id"]
        listing = client.get("/filmsponsor/campaigns").json()["campaigns"]
        assert [c["campaign_id"] for c in listing] == [campaign["campaign_id"]]

    def test_discover_without_key_is_unavailable_and_stores_nothing(self, client: TestClient):
        campaign = _create_campaign(client)
        response = client.post(
            f"/filmsponsor/campaigns/{campaign['campaign_id']}/discover",
            json={"request_id": "discover-req-0001"},
        )
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()
        assert "substituted" in response.json()["detail"].lower()
        detail = client.get(f"/filmsponsor/campaigns/{campaign['campaign_id']}").json()
        assert detail["discoveries"] == []  # nothing fabricated, nothing stored

    def test_unexpected_discovery_typeerror_maps_to_sanitized_502(self, client: TestClient, monkeypatch):
        from app.config import Settings
        from app.qloo import client as qloo_client_module

        campaign = _create_campaign(client)
        monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: SimpleNamespace(has_api_key=True)))

        class FakeQlooClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

        monkeypatch.setattr(qloo_client_module, "QlooClient", FakeQlooClient)

        async def _malformed(**_kwargs):
            raise TypeError("provider payload private canary")

        monkeypatch.setattr(filmsponsor_routes, "discover_brand_evidence", _malformed)
        response = client.post(
            f"/filmsponsor/campaigns/{campaign['campaign_id']}/discover",
            json={"request_id": "discover-malformed-0001"},
        )
        assert response.status_code == 502
        assert "could not complete" in response.json()["detail"]
        assert "private canary" not in response.text
        detail = client.get(f"/filmsponsor/campaigns/{campaign['campaign_id']}").json()
        assert detail["discoveries"] == []

    def test_discover_provider_failure_returns_502_and_stores_nothing(
        self, client: TestClient, monkeypatch
    ):
        campaign = _create_campaign(client)
        monkeypatch.setenv("QLOO_API_KEY", "test-key-not-a-real-secret")

        async def _failed(**_kwargs):
            return DiscoveryOutcome(
                report={
                    "call_ids": [],
                    "halt_reason": {"error_type": "QlooError", "status": 503},
                }
            )

        monkeypatch.setattr(filmsponsor_routes, "discover_brand_evidence", _failed)
        response = client.post(
            f"/filmsponsor/campaigns/{campaign['campaign_id']}/discover",
            json={"request_id": "discover-req-0002"},
        )
        assert response.status_code == 502
        detail = client.get(f"/filmsponsor/campaigns/{campaign['campaign_id']}").json()
        assert detail["discoveries"] == []

    def test_discover_success_stores_measured_report_and_is_idempotent(
        self, client: TestClient, monkeypatch
    ):
        campaign = _create_campaign(client)
        monkeypatch.setenv("QLOO_API_KEY", "test-key-not-a-real-secret")

        async def _ok(**_kwargs):
            return DiscoveryOutcome(
                report={
                    "data_status": "measured",
                    "source": "qloo",
                    "films": [],
                    "theme_canonicalization": [],
                    "stages": {},
                    "brands": [{"entity_id": "urn:entity:brand:1", "name": "Brand One"}],
                    "non_brand_results": [],
                    "interpretation_limits": list(INTERPRETATION_LIMITS),
                    "call_ids": ["call-1"],
                    "empty": False,
                }
            )

        monkeypatch.setattr(filmsponsor_routes, "discover_brand_evidence", _ok)
        first = client.post(
            f"/filmsponsor/campaigns/{campaign['campaign_id']}/discover",
            json={"request_id": "discover-req-0003"},
        )
        assert first.status_code == 200
        discovery = first.json()["discovery"]
        assert discovery["data_status"] == "measured"
        assert discovery["report"]["interpretation_limits"] == INTERPRETATION_LIMITS
        replay = client.post(
            f"/filmsponsor/campaigns/{campaign['campaign_id']}/discover",
            json={"request_id": "discover-req-0003"},
        )
        assert replay.json()["duplicate"] is True
        assert replay.json()["discovery"]["discovery_id"] == discovery["discovery_id"]

    def test_drafts_require_source_review_before_approval(self, client: TestClient):
        campaign = _create_campaign(client)
        cid = campaign["campaign_id"]
        draft = client.post(
            f"/filmsponsor/campaigns/{cid}/drafts",
            json={"request_id": "draft-req-0001", "brand_name": "Brand One", "pitch": "Premiere partnership."},
        ).json()["draft"]
        assert draft["status"] == "DRAFT"

        blocked = client.post(f"/filmsponsor/campaigns/{cid}/drafts/{draft['draft_id']}/approve")
        assert blocked.status_code == 409
        assert "source review" in blocked.json()["detail"].lower()

        review = client.post(
            f"/filmsponsor/campaigns/{cid}/drafts/{draft['draft_id']}/source-reviews",
            json={
                "request_id": "review-req-0001",
                "source_url": "https://official.example/programme",
                "claim_checked": "Brand runs an open filmmaker sponsorship programme.",
                "verification_status": "SUPPORTED_BY_OFFICIAL_SOURCE",
            },
        )
        assert review.status_code == 201, review.text

        approved = client.post(f"/filmsponsor/campaigns/{cid}/drafts/{draft['draft_id']}/approve")
        assert approved.status_code == 200
        assert approved.json()["draft"]["status"] == "APPROVED"
        assert approved.json()["draft"]["approved_at"] is not None

        # Approval is idempotent for the same immutable draft version.
        again = client.post(f"/filmsponsor/campaigns/{cid}/drafts/{draft['draft_id']}/approve")
        assert again.json()["draft"]["status"] == "APPROVED"

    def test_draft_editing_creates_a_new_version(self, client: TestClient):
        campaign = _create_campaign(client)
        cid = campaign["campaign_id"]
        first = client.post(
            f"/filmsponsor/campaigns/{cid}/drafts",
            json={"request_id": "draft-req-0010", "brand_name": "Brand One", "pitch": "v1"},
        ).json()["draft"]
        second = client.post(
            f"/filmsponsor/campaigns/{cid}/drafts",
            json={
                "request_id": "draft-req-0011",
                "brand_name": "Brand One",
                "pitch": "v2",
                "supersedes_id": first["draft_id"],
            },
        ).json()["draft"]
        assert second["version"] == 2
        assert second["supersedes_id"] == first["draft_id"]
        # A record can be superseded only once.
        third = client.post(
            f"/filmsponsor/campaigns/{cid}/drafts",
            json={
                "request_id": "draft-req-0012",
                "brand_name": "Brand One",
                "pitch": "v3",
                "supersedes_id": first["draft_id"],
            },
        )
        assert third.status_code == 409

    def test_export_includes_approved_only(self, client: TestClient):
        campaign = _create_campaign(client)
        cid = campaign["campaign_id"]
        approved_draft = client.post(
            f"/filmsponsor/campaigns/{cid}/drafts",
            json={"request_id": "draft-req-0020", "brand_name": "Brand One", "pitch": "Ready."},
        ).json()["draft"]
        client.post(
            f"/filmsponsor/campaigns/{cid}/drafts/{approved_draft['draft_id']}/source-reviews",
            json={
                "request_id": "review-req-0020",
                "source_url": "https://official.example/programme",
                "claim_checked": "Open programme page exists.",
                "verification_status": "SUPPORTED_BY_OFFICIAL_SOURCE",
            },
        )
        assert (
            client.post(
                f"/filmsponsor/campaigns/{cid}/drafts/{approved_draft['draft_id']}/approve"
            ).status_code
            == 200
        )
        unapproved = client.post(
            f"/filmsponsor/campaigns/{cid}/drafts",
            json={"request_id": "draft-req-0021", "brand_name": "Brand Two", "pitch": "Not ready."},
        ).json()["draft"]

        package = client.get(f"/filmsponsor/campaigns/{cid}/export").json()
        assert package["export_ready"] is True
        assert [d["draft_id"] for d in package["approved_drafts"]] == [approved_draft["draft_id"]]
        assert package["approved_drafts"][0]["source_reviews"][0]["verification_status"] == (
            "SUPPORTED_BY_OFFICIAL_SOURCE"
        )
        excluded = package["excluded_drafts"]
        assert [e["draft_id"] for e in excluded] == [unapproved["draft_id"]]
        assert excluded[0]["reason"] == "not_approved"
        assert package["interpretation_limits"]

    def test_campaigns_for_same_film_with_distinct_request_ids_remain_separate(self, client: TestClient):
        first = client.post("/filmsponsor/campaigns", json={
            "request_id": "campaign-inception-01",
            "film_title": "Inception",
            "film_year": 2010,
            "imdb_id": "tt1375666",
            "goals": "Festival outreach",
        }).json()["campaign"]
        second = client.post("/filmsponsor/campaigns", json={
            "request_id": "campaign-inception-02",
            "film_title": "Inception",
            "film_year": 2010,
            "imdb_id": "tt1375666",
            "goals": "Streaming launch",
        }).json()["campaign"]
        assert second["campaign_id"] != first["campaign_id"]
        assert len(client.get("/filmsponsor/campaigns").json()["campaigns"]) == 2

    def test_outreach_requires_explicit_statuses(self, client: TestClient):
        campaign = _create_campaign(client)
        response = client.post(
            f"/filmsponsor/campaigns/{campaign['campaign_id']}/outreach",
            json={
                "request_id": "outreach-empty-status",
                "contact_status": "",
                "measurement_status": "",
            },
        )
        assert response.status_code == 422
        assert client.get(f"/filmsponsor/campaigns/{campaign['campaign_id']}").json()["outreach"] == []

    def test_outreach_records_zero_not_missing_and_supports_corrections(self, client: TestClient):
        campaign = _create_campaign(client)
        cid = campaign["campaign_id"]
        created = client.post(
            f"/filmsponsor/campaigns/{cid}/outreach",
            json={
                "request_id": "outreach-req-0001",
                "contact_status": "CONTACTED",
                "measurement_status": "OBSERVED",
                "metrics": {"replies": 0},
                "outcome": "No reply within the observation window.",
            },
        )
        assert created.status_code == 201, created.text
        record = created.json()["outreach"]
        assert record["metrics"]["replies"] == 0  # observed zero, not null

        correction = client.post(
            f"/filmsponsor/campaigns/{cid}/outreach",
            json={
                "request_id": "outreach-req-0002",
                "contact_status": "RESPONDED",
                "measurement_status": "OBSERVED",
                "outcome": "Replied after all.",
                "supersedes_id": record["outreach_id"],
            },
        )
        assert correction.status_code == 201
        assert correction.json()["outreach"]["supersedes_id"] == record["outreach_id"]

        invalid = client.post(
            f"/filmsponsor/campaigns/{cid}/outreach",
            json={
                "request_id": "outreach-req-0003",
                "contact_status": "TELEPATHY",
                "measurement_status": "OBSERVED",
            },
        )
        assert invalid.status_code == 422

    def test_unknown_campaign_is_404(self, client: TestClient):
        assert client.get("/filmsponsor/campaigns/does-not-exist").status_code == 404
        assert (
            client.get("/filmsponsor/campaigns/does-not-exist/export").status_code == 404
        )


class TestPublicDemoBoundary:
    def test_public_mode_blocks_filmsponsor_routes(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("QLOO_API_KEY", raising=False)
        monkeypatch.setenv("ADJACENT_PUBLIC_DEMO", "1")
        # Deterministic under test ordering: clear the shared request limiter.
        from app import public_demo

        public_demo._PUBLIC_REQUEST_LIMITER.reset()
        filmsponsor_routes.reset_filmsponsor_for_tests(tmp_path / "experiments.db")
        with TestClient(app) as public_client:
            blocked = public_client.post(
                "/filmsponsor/campaigns",
                json={"request_id": "public-req-0001", "film_title": "X"},
            )
            assert blocked.status_code == 403
            assert "sponsorship campaigns" in blocked.json()["detail"]
            assert public_client.get("/filmsponsor/campaigns").status_code == 403
        filmsponsor_routes.reset_filmsponsor_for_tests()
