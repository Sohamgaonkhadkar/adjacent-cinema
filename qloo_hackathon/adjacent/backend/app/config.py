"""Runtime configuration for the Adjacent backend.

Day 1 rule: the process must start and be fully testable with NO Qloo API key.
If `QLOO_API_KEY` is absent, `Settings.mock_mode` is True and only
`MockQlooClient` may be constructed (enforced in `QlooClient.__init__`).

Never log, trace, or persist `qloo_api_key`. Use `Settings.redacted()` for any
diagnostic output.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

# The hackathon API host. Staging (staging.api.qloo.com) and production
# (api.qloo.com) both reject the hackathon key with 401 — do not "fix" this.
DEFAULT_BASE_URL = "https://hackathon.api.qloo.com"

#: The official hackathon harness (@qloo/qloo-harness) reads QLOO_TRUSTED_BASE_URL
#: for its own calls. It is the same host as our client's base URL; we keep both
#: names so one .env configures our probe AND the official harness without either
#: side guessing. See docs/QLOO_SETUP.md.
DEFAULT_TRUSTED_BASE_URL = DEFAULT_BASE_URL

# Repository layout anchors.
APP_DIR = Path(__file__).resolve().parent  # backend/app
BACKEND_DIR = APP_DIR.parent  # backend
PROJECT_DIR = BACKEND_DIR.parent  # adjacent/
FIXTURES_DIR = BACKEND_DIR / "tests" / "fixtures"
DOCS_DIR = PROJECT_DIR / "docs"

_TRUE = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_cities(name: str) -> tuple[str, ...] | None:
    """Parse a city list where each entry may itself contain a comma.

    Cities are written the way a human writes them — "London, UK" — so the comma
    cannot be the separator. Entries are separated by **semicolons**:

        QLOO_PROBE_CITIES=London, UK;New York, NY;Portland, Oregon

    Returns None when the variable is unset or blank, so the caller keeps its
    default. Splitting on a comma here (which this function replaced) silently
    produced six bogus cities from the three above, and every subsequent heatmap
    probe would have queried "UK" and "NY" instead of the intended places.
    """
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return None
    return tuple(part.strip() for part in raw.split(";") if part.strip())


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings, built from the environment."""

    qloo_api_key: str | None = None
    qloo_base_url: str = DEFAULT_BASE_URL
    #: Consumed by the official harness, not by our client (ours uses qloo_base_url).
    qloo_trusted_base_url: str = DEFAULT_TRUSTED_BASE_URL

    # Network behaviour
    connect_timeout_s: float = 1.5
    read_timeout_s: float = 8.0
    max_retries: int = 3
    retry_backoff_base_s: float = 0.5
    rate_limit_rps: float = 3.0

    # Fixtures / docs
    fixtures_dir: Path = field(default_factory=lambda: FIXTURES_DIR)
    docs_dir: Path = field(default_factory=lambda: DOCS_DIR)

    # Optional override for the demo/probe city. Deliberately NOT hard-coded to
    # any single city: the demo city must be chosen from live coverage evidence.
    #: Candidate cities for the coverage probe. Override with QLOO_PROBE_CITIES,
    #: semicolon-separated (a comma belongs to the city name: "London, UK").
    probe_cities: tuple[str, ...] = ("London, UK", "New York, NY", "Portland, Oregon")

    @classmethod
    def from_env(cls, **overrides: object) -> Settings:
        kwargs: dict[str, object] = {
            "qloo_api_key": (os.getenv("QLOO_API_KEY") or "").strip() or None,
            "qloo_base_url": os.getenv("QLOO_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            "qloo_trusted_base_url": os.getenv(
                "QLOO_TRUSTED_BASE_URL", DEFAULT_TRUSTED_BASE_URL
            ).rstrip("/"),
            "connect_timeout_s": _env_float("QLOO_CONNECT_TIMEOUT_S", 1.5),
            "read_timeout_s": _env_float("QLOO_READ_TIMEOUT_S", 8.0),
            "max_retries": _env_int("QLOO_MAX_RETRIES", 3),
            "retry_backoff_base_s": _env_float("QLOO_RETRY_BACKOFF_BASE_S", 0.5),
            "rate_limit_rps": _env_float("QLOO_RATE_LIMIT_RPS", 3.0),
        }
        cities = _env_cities("QLOO_PROBE_CITIES")
        if cities is not None:
            kwargs["probe_cities"] = cities
        kwargs.update(overrides)
        return cls(**kwargs)  # type: ignore[arg-type]

    # --- derived -----------------------------------------------------------
    @property
    def has_api_key(self) -> bool:
        return bool(self.qloo_api_key)

    @property
    def mock_mode(self) -> bool:
        """True when no live key is configured. Mock mode is the default."""
        return not self.has_api_key

    @property
    def mode(self) -> str:
        """The mode, stated in one word wherever it is reported: `live` or `mock`.

        Derived from the key's presence, never from a flag: a flag can be forgotten,
        and the whole point of this property is that a run cannot be ambiguous about
        whether it talked to Qloo.
        """
        return "mock" if self.mock_mode else "live"

    @property
    def base_url_is_hackathon_host(self) -> bool:
        """False when QLOO_BASE_URL points somewhere a hackathon key will 401 on."""
        return self.qloo_base_url.rstrip("/") == DEFAULT_BASE_URL

    def redacted(self) -> dict[str, object]:
        """Safe-to-log view. Never contains the key material."""
        return {
            "mode": self.mode,
            "qloo_base_url": self.qloo_base_url,
            "qloo_trusted_base_url": self.qloo_trusted_base_url,
            "base_url_is_hackathon_host": self.base_url_is_hackathon_host,
            "qloo_api_key": "***set***" if self.has_api_key else None,
            "key_fingerprint": self.key_fingerprint(),
            "mock_mode": self.mock_mode,
            "connect_timeout_s": self.connect_timeout_s,
            "read_timeout_s": self.read_timeout_s,
            "max_retries": self.max_retries,
            "rate_limit_rps": self.rate_limit_rps,
            "probe_cities": list(self.probe_cities),
        }

    def key_fingerprint(self) -> str | None:
        """Stable, non-reversible identifier for logs and docs. Never key material.

        Milestone 3: this previously ended with the key's last two characters, and
        the probe writes the value into a committed file (docs/api_probe_results.json),
        so a fragment of real key material was reaching the repository. It is now a
        truncated SHA-256 digest of the key: two runs using the same key still produce
        the same fingerprint (which is why the field exists), and nothing in the
        value can be used to reconstruct or guess the key. The length is kept because
        a truncated paste is the failure this field is actually used to diagnose.
        """
        if not self.qloo_api_key:
            return None
        digest = hashlib.sha256(self.qloo_api_key.encode("utf-8")).hexdigest()[:12]
        return f"sha256:{digest}·len={len(self.qloo_api_key)}"
