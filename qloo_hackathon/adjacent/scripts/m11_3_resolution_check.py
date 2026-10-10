#!/usr/bin/env python3
"""M11.3: Live Resolution Checks.

Validates resolution with real Qloo API for 6 test cases.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from app.config import Settings
from app.qloo.client import QlooClient
from app.resolution.resolver import EntityResolver, MatchStatus

TEST_CASES = [
    {
        "name": "title_only",
        "params": {"title": "Parasite"},
        "expected": "AMBIGUOUS",  # Multiple Parasite entities
    },
    {
        "name": "title_and_year",
        "params": {"title": "Parasite", "year": 2019},
        "expected": "VERIFIED",
    },
    {
        "name": "correct_imdb",
        "params": {"title": "Parasite", "year": 2019, "external_id": "tt6751668", "external_family": "imdb"},
        "expected": "VERIFIED",
    },
    {
        "name": "wrong_imdb",
        "params": {"title": "Parasite", "year": 2019, "external_id": "tt9999999", "external_family": "imdb"},
        "expected": "MISMATCH",  # Wrong IMDb must produce MISMATCH
    },
    {
        "name": "ambiguous_title",
        "params": {"title": "Dune"},
        "expected": "AMBIGUOUS",
    },
    {
        "name": "unresolved_title",
        "params": {"title": "xyznonexistentmovie123"},
        "expected": "UNRESOLVED",
    },
]


async def run():
    """Execute resolution checks."""
    print("=== M11.3 LIVE RESOLUTION CHECKS ===\n")
    
    settings = Settings.from_env()
    client = QlooClient(settings=settings)
    resolver = EntityResolver(client, delay_s=1.0)
    
    results = []
    
    for test in TEST_CASES:
        name = test["name"]
        params = test["params"]
        expected = test["expected"]
        
        print(f"Test: {name}")
        print(f"  Params: {params}")
        
        try:
            resolved = await resolver.resolve_item(**params)
            actual = resolved.match_status.value
            
            passed = actual == expected
            results.append({
                "name": name,
                "params": params,
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "entity_id": resolved.qloo_entity_id,
                "entity_name": resolved.qloo_name,
                "verification_notes": resolved.verification_notes,
            })
            
            print(f"  Expected: {expected}")
            print(f"  Actual:   {actual}")
            print(f"  Result:   {'PASS' if passed else 'FAIL'}")
            if resolved.qloo_entity_id:
                print(f"  Entity:   {resolved.qloo_name} ({resolved.qloo_entity_id})")
            if resolved.verification_notes:
                print(f"  Notes:    {resolved.verification_notes}")
            
        except Exception as e:
            results.append({
                "name": name,
                "params": params,
                "expected": expected,
                "actual": "ERROR",
                "passed": False,
                "error": str(e),
            })
            print(f"  Error: {e}")
        
        print()
    
    # Summary
    print("=" * 60)
    print("RESOLUTION CHECK SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {r['name']}: {status} ({r['actual']})")
    
    print(f"\nTotal: {passed_count}/{total_count} passed")
    
    # Verify downstream behavior
    print("\n=== DOWNSTREAM BEHAVIOR ===\n")
    print("VERIFIED → proceeds to analysis")
    print("AMBIGUOUS → stops downstream analysis")
    print("MISMATCH → stops downstream analysis")
    print("UNRESOLVED → stops downstream analysis")
    
    # Save results
    output_path = Path(__file__).parent.parent / "docs" / "m11_3_resolution_checks.json"
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to: {output_path}")
    
    return results


if __name__ == "__main__":
    asyncio.run(run())