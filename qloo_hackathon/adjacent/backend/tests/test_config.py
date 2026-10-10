"""Configuration parsing — specifically, the city list.

Reason this file exists: `QLOO_PROBE_CITIES` is the only setting whose *values*
contain the delimiter a naive parser would use. Splitting on commas turned
"London, UK" into "London" and "UK", which would have sent the heatmap probe to
six places that are not cities and produced geography evidence about nothing.
Milestone 3 hit exactly that bug, so it gets pinned here.
"""

from __future__ import annotations

import pytest
from app.config import Settings

CITY_VAR = "QLOO_PROBE_CITIES"


# ---------------------------------------------------------------------------
# The regression: semicolon-separated cities stay intact
# ---------------------------------------------------------------------------


def test_semicolon_separated_cities_parse_to_exactly_three_entries(monkeypatch):
    monkeypatch.setenv(CITY_VAR, "London, UK;New York, NY;Portland, Oregon")
    assert list(Settings.from_env().probe_cities) == [
        "London, UK",
        "New York, NY",
        "Portland, Oregon",
    ]


def test_a_comma_inside_a_city_name_is_never_a_separator(monkeypatch):
    """The bug: a comma split yields ('London', 'UK') — six bogus cities from three."""
    monkeypatch.setenv(CITY_VAR, "London, UK;New York, NY;Portland, Oregon")
    cities = Settings.from_env().probe_cities

    assert "UK" not in cities
    assert "NY" not in cities
    assert "Oregon" not in cities
    assert len(cities) == 3
    for city in cities:
        assert "," in city, "every entry is 'City, Region' format"


def test_whitespace_around_entries_is_trimmed(monkeypatch):
    monkeypatch.setenv(CITY_VAR, "  London, UK ;New York, NY;  Portland, Oregon  ")
    assert list(Settings.from_env().probe_cities) == [
        "London, UK",
        "New York, NY",
        "Portland, Oregon",
    ]


def test_empty_entries_are_dropped(monkeypatch):
    monkeypatch.setenv(CITY_VAR, "London, UK;;New York, NY;")
    assert list(Settings.from_env().probe_cities) == ["London, UK", "New York, NY"]


def test_a_single_city_with_a_comma_is_one_city(monkeypatch):
    monkeypatch.setenv(CITY_VAR, "London, UK")
    assert list(Settings.from_env().probe_cities) == ["London, UK"]


# ---------------------------------------------------------------------------
# Unrelated behaviour: the default and the "unset" cases are unchanged
# ---------------------------------------------------------------------------


def test_unset_cities_fall_back_to_the_documented_default(monkeypatch):
    monkeypatch.delenv(CITY_VAR, raising=False)
    assert list(Settings.from_env().probe_cities) == [
        "London, UK",
        "New York, NY",
        "Portland, Oregon",
    ]


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_blank_cities_keep_the_default(monkeypatch, blank):
    monkeypatch.setenv(CITY_VAR, blank)
    assert list(Settings.from_env().probe_cities) == [
        "London, UK",
        "New York, NY",
        "Portland, Oregon",
    ]


def test_probe_cities_survive_the_redacted_view(monkeypatch):
    """Cities are not secrets, and the redacted settings view is what diagnostics print."""
    monkeypatch.setenv(CITY_VAR, "London, UK;New York, NY;Portland, Oregon")
    redacted = Settings.from_env().redacted()
    assert redacted["probe_cities"] == ["London, UK", "New York, NY", "Portland, Oregon"]


def test_city_parsing_does_not_disturb_other_settings(monkeypatch):
    """One setting changed; nothing else moves."""
    monkeypatch.setenv(CITY_VAR, "Berlin, Germany")
    monkeypatch.setenv("QLOO_RATE_LIMIT_RPS", "2.5")
    monkeypatch.setenv("QLOO_MAX_RETRIES", "1")
    settings = Settings.from_env()

    assert list(settings.probe_cities) == ["Berlin, Germany"]
    assert settings.rate_limit_rps == 2.5
    assert settings.max_retries == 1
    assert settings.qloo_base_url == "https://hackathon.api.qloo.com"


# ---------------------------------------------------------------------------
# The key fingerprint: useful for diagnosis, never a fragment of the key
# ---------------------------------------------------------------------------


def test_key_fingerprint_is_absent_without_a_key(monkeypatch):
    monkeypatch.delenv("QLOO_API_KEY", raising=False)
    assert Settings.from_env().key_fingerprint() is None


def test_key_fingerprint_contains_no_key_material(monkeypatch):
    """It is written into a committed file, so it must not contain the key.

    The previous implementation appended the key's last two characters, which put a
    real fragment of the secret into docs/api_probe_results.json.
    """
    fake = "FAKE-key-0123456789-abcdef"
    monkeypatch.setenv("QLOO_API_KEY", fake)
    settings = Settings.from_env()

    fingerprint = settings.key_fingerprint()
    assert fingerprint is not None
    assert fake not in fingerprint
    assert fake[-2:] not in fingerprint
    # ...and neither does the diagnostic view that `/health` prints.
    assert fake not in repr(settings.redacted())
    assert fake[-2:] not in repr(settings.redacted())


def test_key_fingerprint_is_stable_and_discriminating(monkeypatch):
    """Two runs with the same key compare equal; two different keys do not."""
    monkeypatch.setenv("QLOO_API_KEY", "FAKE-key-aaaa")
    first = Settings.from_env().key_fingerprint()
    second = Settings.from_env().key_fingerprint()
    assert first == second

    monkeypatch.setenv("QLOO_API_KEY", "FAKE-key-bbbb")
    assert Settings.from_env().key_fingerprint() != first


def test_key_fingerprint_shows_only_a_digest_and_a_length(monkeypatch):
    import re

    fake = "FAKE-key-0123456789"
    monkeypatch.setenv("QLOO_API_KEY", fake)
    fingerprint = Settings.from_env().key_fingerprint()
    assert re.fullmatch(rf"sha256:[0-9a-f]{{12}}·len={len(fake)}", fingerprint or "")


# ---------------------------------------------------------------------------
# Mode reporting and the two base URLs (harness + client)
# ---------------------------------------------------------------------------

TRUSTED_VAR = "QLOO_TRUSTED_BASE_URL"
BASE_VAR = "QLOO_BASE_URL"


def test_mode_is_mock_without_a_key_and_live_with_one(monkeypatch):
    monkeypatch.delenv("QLOO_API_KEY", raising=False)
    assert Settings.from_env().mode == "mock"
    assert Settings.from_env().mock_mode is True

    monkeypatch.setenv("QLOO_API_KEY", "FAKE-key-for-mode-reporting")
    assert Settings.from_env().mode == "live"
    assert Settings.from_env().mock_mode is False


def test_mode_appears_in_the_redacted_view(monkeypatch):
    monkeypatch.setenv("QLOO_API_KEY", "FAKE-key-for-mode-reporting")
    redacted = Settings.from_env().redacted()
    assert redacted["mode"] == "live"
    assert redacted["qloo_api_key"] == "***set***"
    assert "FAKE-key-for-mode-reporting" not in repr(redacted)


def test_both_base_urls_default_to_the_hackathon_host(monkeypatch):
    monkeypatch.delenv(BASE_VAR, raising=False)
    monkeypatch.delenv(TRUSTED_VAR, raising=False)
    settings = Settings.from_env()
    assert settings.qloo_base_url == "https://hackathon.api.qloo.com"
    assert settings.qloo_trusted_base_url == "https://hackathon.api.qloo.com"
    assert settings.base_url_is_hackathon_host is True


def test_trusted_base_url_is_configurable_for_the_harness(monkeypatch):
    monkeypatch.setenv(TRUSTED_VAR, "https://hackathon.api.qloo.com/")
    monkeypatch.setenv(BASE_VAR, "https://staging.api.qloo.com")
    settings = Settings.from_env()
    assert settings.qloo_trusted_base_url == "https://hackathon.api.qloo.com"  # trailing / trimmed
    assert settings.qloo_base_url == "https://staging.api.qloo.com"
    # A wrong client host is detectable, so the probe can warn instead of 401-ing blindly.
    assert settings.base_url_is_hackathon_host is False
