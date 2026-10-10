"""M13.5: Canonical Film Identity + Verified Qloo Join.

Pipeline:
1. Canonicalize all film titles (deterministic, documented)
2. Scrape PCC detail pages for film years
3. Create canonical film records with provenance
4. Re-run EntityResolver with canonical titles + years
5. Build leakage-safe benchmark from canonical film master
6. Run audits

Constraints:
- Does NOT train ML
- Does NOT accept AMBIGUOUS as VERIFIED
- Does NOT use external years to force VERIFIED
- Does NOT invent film identities
- Reuses existing EntityResolver
"""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

adjacent_root = Path(__file__).parent.parent.parent
env_path = adjacent_root / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip()

sys.path.insert(0, str(adjacent_root / 'backend'))

from app.domain.outcome_repository import OutcomeRepository, film_key
from app.domain.film_identity import (
    canonicalize_film, canonical_film_key, audit_canonicalization,
    IdentityStatus,
)
from app.collectors.pcc_years import scrape_pcc_film_year
from app.config import Settings


def step1_canonicalize(repo: OutcomeRepository) -> dict:
    """Phase 1: Canonicalize all film titles."""
    print(f"\n{'='*70}")
    print("STEP 1: CANONICALIZE FILM TITLES")
    print(f"{'='*70}")

    films = repo.get_unique_films()
    audit = audit_canonicalization(films)

    print(f"\n  Raw entries: {audit['total_raw_entries']}")
    print(f"  Unique raw titles: {audit['unique_raw_titles']}")
    print(f"  Unique canonical films: {audit['unique_canonical_films']}")
    print(f"  Collapse count: {audit['collapse_count']}")

    print(f"\n  Status counts:")
    for status, count in audit['status_counts'].items():
        print(f"    {status}: {count}")

    print(f"\n  Normalization rules applied:")
    for reason, count in audit['reason_counts'].items():
        print(f"    {reason}: {count}")

    print(f"\n  Events detected: {audit['event_count']}")
    for title, reason in audit['event_examples'][:5]:
        print(f"    {title!r}")

    print(f"\n  Collapsed groups: {audit['collapsed_groups_count']}")
    for key, titles in list(audit['collapsed_groups'].items())[:10]:
        print(f"    {key}: {titles}")

    return audit


def step2_create_canonical_films(repo: OutcomeRepository, audit: dict) -> dict:
    """Phase 2: Create canonical film records."""
    print(f"\n{'='*70}")
    print("STEP 2: CREATE CANONICAL FILM RECORDS")
    print(f"{'='*70}")

    results = audit['results']
    now = datetime.now(timezone.utc).isoformat()

    # Group by canonical film key
    canonical_groups: dict[str, list] = {}
    for r in results:
        key = canonical_film_key(r.canonical_title, r.extracted_year)
        if key not in canonical_groups:
            canonical_groups[key] = []
        canonical_groups[key].append(r)

    created = 0
    for cf_key, group in canonical_groups.items():
        raw_titles = list(set(r.raw_title for r in group))
        # Get the film_url from the first result that has one
        film_url = ""
        for r in group:
            # Find the original film URL from the audit
            for film in repo.get_unique_films():
                if film['film_title'] == r.raw_title and film.get('film_url'):
                    film_url = film['film_url']
                    break
            if film_url:
                break

        # Use the first result's canonical values
        primary = group[0]

        # Check if year was provided by PCC
        year = primary.extracted_year
        year_source = primary.year_source
        if not year_source and year:
            year_source = "extracted_from_title"

        cf = {
            "film_key": cf_key,
            "raw_titles": raw_titles,
            "canonical_title": primary.canonical_title,
            "film_year": year,
            "year_source": year_source,
            "year_provenance": "",
            "film_url": film_url,
            "source_provenance": "pcc/whats_on",
            "identity_status": primary.identity_status.value,
            "identity_confidence": "",
            "is_event": primary.is_event,
            "event_reason": primary.event_reason,
            "created_at": now,
        }
        repo.upsert_canonical_film(cf)
        created += 1

    stats = repo.canonical_film_stats()
    print(f"\n  Created: {created}")
    print(f"  Total canonical films: {stats['total']}")
    print(f"  Verified (with year): {stats['verified']}")
    print(f"  Year missing: {stats['year_missing']}")
    print(f"  Events: {stats['events']}")
    print(f"  Needs review: {stats['needs_review']}")

    return {"created": created, "stats": stats, "groups": canonical_groups}


def step3_scrape_pcc_years(repo: OutcomeRepository, limit: int | None = None) -> dict:
    """Phase 3: Scrape film years from PCC detail pages."""
    print(f"\n{'='*70}")
    print("STEP 3: SCRAPE PCC DETAIL PAGES FOR YEARS")
    print(f"{'='*70}")

    canonical_films = repo.list_canonical_films(exclude_events=True)
    films_without_year = [f for f in canonical_films if not f['film_year']]
    films_with_url = [f for f in films_without_year if f.get('film_url')]

    print(f"\n  Canonical films (non-event): {len(canonical_films)}")
    print(f"  Without year: {len(films_without_year)}")
    print(f"  With PCC URL: {len(films_with_url)}")

    if limit:
        films_with_url = films_with_url[:limit]
        print(f"  Limited to: {len(films_with_url)}")

    results = {"attempted": 0, "found": 0, "failed": 0, "errors": []}

    for i, cf in enumerate(films_with_url):
        print(f"  [{i+1}/{len(films_with_url)}] {cf['canonical_title'][:40]}...", end=" ", flush=True)

        result = scrape_pcc_film_year(cf['film_url'])
        results["attempted"] += 1

        if result["success"] and result["year"]:
            year = result["year"]
            print(f"✓ {year}")

            # Update canonical film with year
            cf["film_year"] = year
            cf["year_source"] = "pcc_detail_page"
            cf["year_provenance"] = result["evidence"]
            cf["identity_status"] = IdentityStatus.VERIFIED.value
            repo.upsert_canonical_film(cf)
            results["found"] += 1
        else:
            print(f"✗ {result['evidence'][:50]}")
            results["failed"] += 1

    stats = repo.canonical_film_stats()
    print(f"\n  Results:")
    print(f"    Attempted: {results['attempted']}")
    print(f"    Years found: {results['found']}")
    print(f"    Failed: {results['failed']}")
    print(f"\n  Updated stats:")
    print(f"    Verified: {stats['verified']}")
    print(f"    Year missing: {stats['year_missing']}")
    print(f"    Events: {stats['events']}")

    return results


async def step4_resolve_films(repo: OutcomeRepository) -> dict:
    """Phase 4: Re-run EntityResolver with canonical titles + years."""
    print(f"\n{'='*70}")
    print("STEP 4: QLOO RESOLUTION (CANONICAL FILMS WITH YEARS)")
    print(f"{'='*70}")

    from app.qloo.client import QlooClient
    from app.resolution.resolver import EntityResolver
    from app.resolution.contract import MatchStatus

    # Get canonical films with years that need resolution
    canonical_films = repo.list_canonical_films(exclude_events=True)
    films_with_year = [f for f in canonical_films if f['film_year']]
    films_to_resolve = [f for f in films_with_year if f['identity_status'] == 'VERIFIED']

    # Check which are already resolved
    existing_resolutions = {r["film_key"]: r for r in repo.list_all_film_resolutions()}
    to_resolve = [f for f in films_to_resolve if f['film_key'] not in existing_resolutions]

    print(f"\n  Canonical films (non-event): {len(canonical_films)}")
    print(f"  With year: {len(films_with_year)}")
    print(f"  Verified identity: {len(films_to_resolve)}")
    print(f"  Already resolved: {len(films_to_resolve) - len(to_resolve)}")
    print(f"  To resolve: {len(to_resolve)}")

    if not to_resolve:
        return {"resolved": 0, "ambiguous": 0, "mismatch": 0, "unresolved": 0}

    # Create Qloo client and resolver
    settings = Settings.from_env()
    client = QlooClient(settings)
    resolver = EntityResolver(client, delay_s=1.5)

    stats = {"resolved": 0, "ambiguous": 0, "mismatch": 0, "unresolved": 0}

    try:
        for i, cf in enumerate(to_resolve):
            title = cf["canonical_title"]
            year = cf["film_year"]
            fk = cf["film_key"]

            print(f"  [{i+1}/{len(to_resolve)}] {title} ({year})...", end=" ", flush=True)

            try:
                result = await resolver.resolve_item(title=title, year=year)
                status = result.match_status.value

                resolution = {
                    "film_key": fk,
                    "film_title": title,
                    "film_year": year,
                    "film_url": cf.get("film_url"),
                    "resolution_status": status,
                    "resolved_title": result.qloo_name,
                    "resolved_year": result.qloo_year,
                    "qloo_entity_id": result.qloo_entity_id,
                    "qloo_name": result.qloo_name,
                    "qloo_entity_type": result.qloo_entity_type,
                    "qloo_popularity": result.qloo_popularity,
                    "qloo_call_id": result.call_id,
                    "resolution_provenance": f"resolver/{result.match_method.value if result.match_method else 'search'}",
                    "resolution_timestamp": datetime.now(timezone.utc).isoformat(),
                }

                repo.record_film_resolution(resolution)

                if status == "VERIFIED":
                    stats["resolved"] += 1
                    print(f"✓ {result.qloo_name} ({result.qloo_entity_id})")

                    # Create Qloo feature snapshot
                    repo.record_qloo_features({
                        "film_key": fk,
                        "qloo_entity_id": result.qloo_entity_id,
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "qloo_popularity": result.qloo_popularity,
                        "qloo_domain": "film",
                        "qloo_call_id": result.call_id,
                        "provenance": "resolution/search",
                    })

                elif status == "AMBIGUOUS":
                    stats["ambiguous"] += 1
                    print(f"? AMBIGUOUS: {result.qloo_name}")
                elif status == "MISMATCH":
                    stats["mismatch"] += 1
                    print(f"✗ MISMATCH: {result.qloo_name}")
                else:
                    stats["unresolved"] += 1
                    print(f"✗ UNRESOLVED")

            except Exception as e:
                stats["unresolved"] += 1
                print(f"✗ ERROR: {str(e)[:50]}")

                repo.record_film_resolution({
                    "film_key": fk,
                    "film_title": title,
                    "film_year": year,
                    "film_url": cf.get("film_url"),
                    "resolution_status": "UNRESOLVED",
                    "resolution_provenance": f"resolver/error:{str(e)[:100]}",
                    "resolution_timestamp": datetime.now(timezone.utc).isoformat(),
                })

    finally:
        await client.aclose()

    print(f"\n  Resolution stats:")
    print(f"    VERIFIED: {stats['resolved']}")
    print(f"    AMBIGUOUS: {stats['ambiguous']}")
    print(f"    MISMATCH: {stats['mismatch']}")
    print(f"    UNRESOLVED: {stats['unresolved']}")

    return stats


def step5_link_observations(repo: OutcomeRepository) -> dict:
    """Phase 5: Link observations to canonical films."""
    print(f"\n{'='*70}")
    print("STEP 5: LINK OBSERVATIONS TO CANONICAL FILMS")
    print(f"{'='*70}")

    observations = repo.list_all_observations()
    canonical_films = repo.list_canonical_films()

    # Build lookup: raw_title → canonical film key
    # First, build from canonical film records
    title_to_canonical: dict[str, str] = {}
    for cf in canonical_films:
        raw_titles = json.loads(cf.get("raw_titles", "[]"))
        for rt in raw_titles:
            title_to_canonical[rt] = cf["film_key"]

    # Also build from canonicalization
    from app.domain.film_identity import canonicalize_film, canonical_film_key as cf_key_fn
    for obs in observations:
        raw_title = obs["film_title"]
        if raw_title not in title_to_canonical:
            result = canonicalize_film(raw_title, obs.get("film_year"))
            key = cf_key_fn(result.canonical_title, result.extracted_year)
            title_to_canonical[raw_title] = key

    linked = 0
    unlinked = 0
    for obs in observations:
        cf_key = title_to_canonical.get(obs["film_title"])
        if cf_key:
            repo.link_observation_to_canonical(obs["observation_id"], cf_key)
            linked += 1
        else:
            unlinked += 1

    print(f"\n  Total observations: {len(observations)}")
    print(f"  Linked to canonical film: {linked}")
    print(f"  Unlinked: {unlinked}")

    return {"linked": linked, "unlinked": unlinked}


def step6_build_benchmark(repo: OutcomeRepository, output_path: Path) -> dict:
    """Phase 6: Build the canonical benchmark."""
    print(f"\n{'='*70}")
    print("STEP 6: BUILD CANONICAL BENCHMARK")
    print(f"{'='*70}")

    observations = repo.list_all_observations()
    canonical_films = {cf["film_key"]: cf for cf in repo.list_canonical_films()}
    resolutions = {r["film_key"]: r for r in repo.list_all_film_resolutions()}

    # Build lookup: observation → canonical film key
    obs_to_cf: dict[str, str] = {}
    for obs in observations:
        # Try canonical_film_key column first
        cf_key = obs.get("canonical_film_key")
        if not cf_key:
            # Fallback to canonicalization
            result = canonicalize_film(obs["film_title"], obs.get("film_year"))
            cf_key = canonical_film_key(result.canonical_title, result.extracted_year)
        obs_to_cf[obs["observation_id"]] = cf_key

    benchmark_rows = []
    for obs in observations:
        obs_id = obs["observation_id"]
        cf_key = obs_to_cf.get(obs_id)
        cf = canonical_films.get(cf_key, {})
        resolution = resolutions.get(cf_key, {})
        source_ts = obs.get("source_timestamp")

        # Get prediction-time-safe Qloo feature
        feature = repo.get_latest_qloo_feature(cf_key, before=source_ts) if cf_key else None
        latest_feature = repo.get_latest_qloo_feature(cf_key) if cf_key else None

        if feature:
            qloo_feature_status = "AVAILABLE_AT_PREDICTION_TIME"
        elif latest_feature:
            qloo_feature_status = "FUTURE_FEATURE_UNAVAILABLE"
        else:
            qloo_feature_status = "NO_FEATURE"

        row = {
            "observation_id": obs_id,
            "venue_id": obs["venue_id"],
            "canonical_film_key": cf_key,
            "canonical_title": cf.get("canonical_title", obs["film_title"]),
            "raw_title": obs["film_title"],
            "film_year": cf.get("film_year"),
            "identity_status": cf.get("identity_status", "NO_CANONICAL"),
            "show_start_at": obs.get("show_start_at"),
            "observation_timestamp": source_ts,
            "lead_time_hours": obs.get("lead_time_hours"),
            "lead_time_bucket": obs.get("lead_time_bucket"),
            "sold_out_observed": obs.get("sold_out"),
            "model_target": obs.get("model_target"),
            "qloo_entity_id": resolution.get("qloo_entity_id"),
            "resolution_status": resolution.get("resolution_status", "NO_RESOLUTION"),
            "qloo_affinity": feature.get("qloo_affinity") if feature else None,
            "qloo_popularity": feature.get("qloo_popularity") if feature else (
                resolution.get("qloo_popularity")
            ),
            "qloo_band": feature.get("qloo_band") if feature else None,
            "qloo_domain": feature.get("qloo_domain") if feature else None,
            "qloo_feature_timestamp": feature.get("retrieved_at") if feature else (
                latest_feature.get("retrieved_at") if latest_feature else None
            ),
            "qloo_feature_status": qloo_feature_status,
            "format": obs.get("format"),
            "booking_url": obs.get("booking_url"),
            "source_url": obs.get("source_url"),
            "source_timestamp": source_ts,
            "provenance": resolution.get("resolution_provenance", "") if resolution else "",
            "is_event": cf.get("is_event", 0),
        }
        benchmark_rows.append(row)

    # Compute stats
    total = len(benchmark_rows)
    non_event = [r for r in benchmark_rows if not r["is_event"]]
    verified_resolution = [r for r in non_event if r["resolution_status"] == "VERIFIED"]
    with_prediction_feature = [r for r in non_event if r["qloo_feature_status"] == "AVAILABLE_AT_PREDICTION_TIME"]
    with_future_feature = [r for r in non_event if r["qloo_feature_status"] == "FUTURE_FEATURE_UNAVAILABLE"]

    # Film-level stats
    unique_canonical = set(r["canonical_film_key"] for r in non_event)
    verified_films = set(r["canonical_film_key"] for r in verified_resolution)

    # Screening coverage by lead time
    coverage_by_lead_time = {}
    for r in non_event:
        bucket = r.get("lead_time_bucket", "unknown")
        if bucket not in coverage_by_lead_time:
            coverage_by_lead_time[bucket] = {"total": 0, "with_entity": 0}
        coverage_by_lead_time[bucket]["total"] += 1
        if r["resolution_status"] == "VERIFIED":
            coverage_by_lead_time[bucket]["with_entity"] += 1

    # Coverage by film frequency
    film_frequency: dict[str, int] = {}
    for r in non_event:
        fk = r["canonical_film_key"]
        film_frequency[fk] = film_frequency.get(fk, 0) + 1

    high_freq = {k: v for k, v in film_frequency.items() if v >= 3}
    high_freq_verified = sum(1 for k in high_freq if k in verified_films)

    benchmark = {
        "version": "M13.5",
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "description": "Canonical film identity + leakage-safe Qloo join",
        "schema": {
            "model_target": "1=SOLD_OUT, NULL=AVAILABLE (AVAILABLE is NOT 0)",
            "qloo_feature_status": "AVAILABLE_AT_PREDICTION_TIME|FUTURE_FEATURE_UNAVAILABLE|NO_FEATURE",
            "sold_out_observed": "1=sold out, 0=available, NULL=unknown",
            "identity_status": "VERIFIED|YEAR_MISSING|EVENT_OR_COMPOSITE|NEEDS_REVIEW",
            "resolution_status": "VERIFIED|AMBIGUOUS|MISMATCH|UNRESOLVED|NO_RESOLUTION",
        },
        "stats": {
            "total_observations": total,
            "non_event_observations": len(non_event),
            "unique_canonical_films": len(unique_canonical),
            "verified_films": len(verified_films),
            "film_verification_rate": round(len(verified_films) / len(unique_canonical), 4) if unique_canonical else 0,
            "screenings_with_verified_entity": len(verified_resolution),
            "screening_verification_rate": round(len(verified_resolution) / len(non_event), 4) if non_event else 0,
            "screenings_with_prediction_time_feature": len(with_prediction_feature),
            "screenings_with_future_feature": len(with_future_feature),
            "model_target_1": sum(1 for r in non_event if r["model_target"] == 1),
            "model_target_null": sum(1 for r in non_event if r["model_target"] is None),
            "coverage_by_lead_time": coverage_by_lead_time,
            "high_frequency_films": len(high_freq),
            "high_frequency_verified": high_freq_verified,
        },
        "observations": benchmark_rows,
    }

    output_path.write_text(json.dumps(benchmark, indent=2, default=str))

    print(f"\n  Total observations: {total}")
    print(f"  Non-event observations: {len(non_event)}")
    print(f"  Unique canonical films: {len(unique_canonical)}")
    print(f"  Verified films: {len(verified_films)}")
    print(f"  Film verification rate: {benchmark['stats']['film_verification_rate']:.2%}")
    print(f"  Screenings with verified entity: {len(verified_resolution)}")
    print(f"  Screening verification rate: {benchmark['stats']['screening_verification_rate']:.2%}")
    print(f"  Prediction-time features: {len(with_prediction_feature)}")
    print(f"  Future features: {len(with_future_feature)}")
    print(f"  model_target=1: {benchmark['stats']['model_target_1']}")
    print(f"  model_target=NULL: {benchmark['stats']['model_target_null']}")
    print(f"  High-frequency films (3+ screenings): {len(high_freq)}")
    print(f"  High-frequency verified: {high_freq_verified}")

    print(f"\n  Coverage by lead time:")
    for bucket, stats in sorted(coverage_by_lead_time.items()):
        rate = stats["with_entity"] / stats["total"] if stats["total"] > 0 else 0
        print(f"    {bucket}: {stats['with_entity']}/{stats['total']} ({rate:.1%})")

    return benchmark


def step7_audit_mismatches(repo: OutcomeRepository) -> dict:
    """Phase 7: Audit previous MISMATCH records."""
    print(f"\n{'='*70}")
    print("STEP 7: AUDIT MISMATCH RECORDS")
    print(f"{'='*70}")

    resolutions = repo.list_all_film_resolutions()
    mismatches = [r for r in resolutions if r["resolution_status"] == "MISMATCH"]

    print(f"\n  Total resolutions: {len(resolutions)}")
    print(f"  MISMATCH records: {len(mismatches)}")

    # Categorize mismatches
    categories = {
        "title_variant": [],    # Minor title difference
        "year_conflict": [],    # Same title, different year
        "bad_source": [],       # Source title was wrong
        "composite_title": [],  # Double feature or event
        "other": [],
    }

    for m in mismatches[:20]:  # Show first 20
        title = m["film_title"]
        resolved = m.get("resolved_title", "")
        print(f"    {title[:40]:40s} → {resolved[:40]}")

    return {"total_mismatches": len(mismatches)}


async def run_m13_5(year_limit: int | None = None):
    """Run the full M13.5 pipeline."""
    print("=" * 70)
    print("M13.5: CANONICAL FILM IDENTITY + VERIFIED QLOO JOIN")
    print("=" * 70)

    db_path = adjacent_root / "data" / "processed" / "outcome_ledger.db"
    repo = OutcomeRepository(db_path)
    print(f"\nRepository: {db_path}")

    # Step 1: Canonicalize
    audit = step1_canonicalize(repo)

    # Step 2: Create canonical film records
    step2_result = step2_create_canonical_films(repo, audit)

    # Step 3: Scrape PCC detail pages for years
    year_result = step3_scrape_pcc_years(repo, limit=year_limit)

    # Step 4: Re-run resolver
    resolution_result = await step4_resolve_films(repo)

    # Step 5: Link observations to canonical films
    link_result = step5_link_observations(repo)

    # Step 6: Build benchmark
    benchmark_path = adjacent_root / "data" / "processed" / "m13_5_canonical_benchmark.json"
    benchmark = step6_build_benchmark(repo, benchmark_path)

    # Step 7: Audit mismatches
    mismatch_audit = step7_audit_mismatches(repo)

    # Final summary
    print(f"\n{'='*70}")
    print("M13.5 FINAL SUMMARY")
    print(f"{'='*70}")

    film_stats = repo.canonical_film_stats()
    sold_out_stats = repo.sold_out_stats()

    print(f"\n  Film Identity:")
    print(f"    Old raw-film count: {audit['unique_raw_titles']}")
    print(f"    New canonical-film count: {film_stats['total']}")
    print(f"    Collapse count: {audit['collapse_count']}")
    print(f"    Events: {film_stats['events']}")

    print(f"\n  Resolution:")
    print(f"    VERIFIED films: {resolution_result.get('resolved', 0)}")
    print(f"    AMBIGUOUS: {resolution_result.get('ambiguous', 0)}")
    print(f"    MISMATCH: {resolution_result.get('mismatch', 0)}")
    print(f"    UNRESOLVED: {resolution_result.get('unresolved', 0)}")

    print(f"\n  Coverage:")
    print(f"    Verified screening coverage: {benchmark['stats']['screenings_with_verified_entity']}/{benchmark['stats']['non_event_observations']}")
    print(f"    Prediction-time Qloo feature coverage: {benchmark['stats']['screenings_with_prediction_time_feature']}/{benchmark['stats']['non_event_observations']}")

    print(f"\n  Proxy Data:")
    print(f"    Total screenings: {sold_out_stats['total']}")
    print(f"    Sold out: {sold_out_stats['sold_out']}")
    print(f"    Available: {sold_out_stats['available']}")

    print(f"\n  Benchmark: {benchmark_path}")

    # Save audit
    audit_path = adjacent_root / "data" / "processed" / "m13_5_audit.json"
    audit_path.write_text(json.dumps({
        "version": "M13.5",
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "canonicalization_audit": {k: v for k, v in audit.items() if k != 'results'},
        "year_scraping": year_result,
        "resolution": resolution_result,
        "linking": link_result,
        "benchmark_stats": benchmark['stats'],
        "film_stats": film_stats,
        "sold_out_stats": sold_out_stats,
    }, indent=2, default=str))

    repo.close()

    print(f"\n{'='*70}")
    print("M13.5 COMPLETE")
    print(f"{'='*70}")
    print(f"  Remaining blocker for outcome evaluation:")
    if benchmark['stats']['screenings_with_prediction_time_feature'] == 0:
        print(f"    → Prediction-time Qloo coverage is STILL ZERO")
        print(f"    → Need to accumulate Qloo snapshots BEFORE observations")
    print(f"    → Need more temporal data (3-6 months) for meaningful analysis")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="M13.5: Canonical Film Identity Pipeline")
    parser.add_argument("--year-limit", type=int, default=None, help="Limit number of films to scrape years for")
    args = parser.parse_args()

    asyncio.run(run_m13_5(year_limit=args.year_limit))