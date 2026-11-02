#!/usr/bin/env python3
"""M14: score a frozen independent film catalog against Qloo on exactly one pool.

Usage (from qloo_hackathon/adjacent):
  python research/scripts/m14_common_universe_live.py --manifest data/benchmarks/common_universe_20261102.json --output /tmp/m14_preflight.json
  QLOO_API_KEY=... python research/scripts/m14_common_universe_live.py --manifest data/benchmarks/common_universe_20261102.json --output /tmp/m14_live.json --live

The first command is offline preflight and NEVER claims a live result.
The second queries Qloo through the production client, strictly verifies film
identity (title, year, type), and refuses partial scoring. Never use fixture
output as live study evidence.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings  # noqa: E402
from app.domain.common_universe import (  # noqa: E402
    InvalidStudy,
    compare_common_universe,
    freeze_manifest,
)
from app.qloo.client import QlooClient  # noqa: E402
from app.resolution.resolver import EntityResolver  # noqa: E402


async def run_live(frozen: dict[str, Any]) -> dict[str, Any]:
    """One scoring context after strict verified resolution of every input."""
    settings = Settings.from_env()
    if not settings.has_api_key:
        result = compare_common_universe(frozen)
        result["reason"] = "QLOO_API_KEY absent: no live experiment executed"
        return result

    async with QlooClient(settings=settings, run_id="m14-common-universe") as client:
        resolver = EntityResolver(client, delay_s=1.1)
        resolution: dict[str, str] = {}
        programme_ids: list[str] = []
        candidate_ids: dict[str, str] = {}

        # Identity mapping happens AFTER the independent catalog is frozen.
        for role, films in (("programme", frozen["programme"]),
                            ("candidate", frozen["candidates"])):
            for film in films:
                entity = await resolver.resolve_item(
                    film["title"], year=film["year"],
                    external_id=film.get("imdb_id"),
                    external_family="imdb" if film.get("imdb_id") else None,
                )
                resolution[film["key"]] = entity.match_status.value
                if entity.usable and entity.qloo_entity_id:
                    if role == "programme":
                        programme_ids.append(entity.qloo_entity_id)
                    else:
                        candidate_ids[film["key"]] = entity.qloo_entity_id

        if len(programme_ids) != len(frozen["programme"]) or len(candidate_ids) != len(frozen["candidates"]):
            result = compare_common_universe(frozen, resolution=resolution)
            result.update(status="not_evaluable",
                          reason="Strict film identity resolution incomplete; no cohort silently removed",
                          qloo_coverage={"resolved_candidates": len(candidate_ids),
                                         "of": len(frozen["candidates"])})
            return result

        if len(set(x.casefold() for x in candidate_ids.values())) != len(candidate_ids):
            raise InvalidStudy("Two catalog films resolved to one provider entity")
        if set(x.casefold() for x in programme_ids) & set(
                x.casefold() for x in candidate_ids.values()):
            raise InvalidStudy("Programme identity overlaps a candidate after resolution")

        response = await client.insights(
            filter_type="urn:entity:movie",
            signal_interests_entities=programme_ids,
            filter_results_entities=list(candidate_ids.values()),
            take=len(candidate_ids),
            tool="m14_score_frozen_universe",
        )
        if response.data_status != "measured" or response.source != "qloo":
            raise InvalidStudy("A live study cannot consume fixture evidence")
        wanted = {v.casefold() for v in candidate_ids.values()}
        returned: dict[str, float | None] = {}
        for entity in response.results:
            entity_id = entity.entity_id.casefold()
            if entity_id not in wanted:
                raise InvalidStudy("Qloo scoring returned a candidate outside the locked set")
            if entity_id in returned:
                raise InvalidStudy("Qloo scoring returned duplicate candidate IDs")
            returned[entity_id] = entity.affinity

        scored = {
            key: (provider_id, returned.get(provider_id.casefold()))
            for key, provider_id in candidate_ids.items()
        }
        return compare_common_universe(
            frozen, scored=scored, call_id=response.call_id, data_status="measured",
            resolution=resolution,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true", help="Use real Qloo calls")
    args = parser.parse_args()

    # Preflight MUST happen before any possible Qloo calls.
    frozen = freeze_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    report = asyncio.run(run_live(frozen)) if args.live else compare_common_universe(frozen)
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["execution"] = "live_qloo" if args.live else "offline_preflight"
    report["live_result_claim"] = args.live and report["status"] == "evaluable"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"M14 {report['status']}: {report['reason']} (frozen={frozen['sha256'][:12]})")
    print(f"Report: {args.output}")
    if args.live and report["status"] != "evaluable":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
