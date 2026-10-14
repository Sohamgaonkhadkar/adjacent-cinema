"""Trusted entity resolver — converts programme items into verified Qloo entities.

Resolution strategy (priority order):
    1. /search with title → verify name + year match
    2. /entities with external ID → only if external ID is returned in response

Key safety rules:
    - NEVER assume returned order matches input order
    - NEVER trust a mapping without verification evidence
    - VERIFIED only when title + year match (or year is unavailable and title is unique)
    - AMBIGUOUS when title matches but year conflicts or is missing
    - MISMATCH when a clear conflict exists (same title, wrong year)
    - UNRESOLVED when no entity is found

Rate limiting:
    - /search is rate-limited; the resolver adds delays between calls
    - Each item is resolved individually to allow verification
"""

from __future__ import annotations

import asyncio
from typing import Any

from .contract import MatchMethod, MatchStatus, ResolvedEntity


def _normalise_title(title: str) -> str:
    """Normalise a title for comparison.  Strips whitespace and lowercases."""
    return title.strip().lower()


def _extract_year(entity: dict[str, Any]) -> int | None:
    """Extract year from a Qloo entity response."""
    props = entity.get("properties", {})
    if isinstance(props, dict):
        year = props.get("release_year") or props.get("year")
        if isinstance(year, (int, float)) and year > 1800:
            return int(year)
    disamb = entity.get("disambiguation", "")
    if isinstance(disamb, str) and disamb.isdigit() and len(disamb) == 4:
        return int(disamb)
    return None


def _extract_types(entity: dict[str, Any]) -> list[str]:
    """Extract entity types from a Qloo entity response."""
    types = entity.get("types", [])
    if isinstance(types, list):
        return [str(t) for t in types]
    t = entity.get("type")
    return [str(t)] if t else []


def _extract_external_ids(entity: dict[str, Any], family: str) -> list[str]:
    """Extract external IDs of a given family from a Qloo entity."""
    ext = entity.get("external", {})
    if isinstance(ext, dict):
        ids = ext.get(family, [])
        if isinstance(ids, list):
            return [str(i) for i in ids]
    # Also check properties.external
    props = entity.get("properties", {})
    if isinstance(props, dict):
        pext = props.get("external", {})
        if isinstance(pext, dict):
            ids = pext.get(family, [])
            if isinstance(ids, list):
                return [str(i) for i in ids]
    return []


def verify_search_result(
    input_title: str,
    input_year: int | None,
    entity: dict[str, Any],
) -> tuple[MatchStatus, list[str]]:
    """Verify whether a /search result matches the input.

    Returns (status, notes).
    """
    notes: list[str] = []
    result_name = entity.get("name", "")
    result_year = _extract_year(entity)

    # Title comparison
    title_match = _normalise_title(result_name) == _normalise_title(input_title)
    if not title_match:
        # Check if it's a close variant (e.g. "Le Samourai" vs "Le Samouraï")
        # by stripping accents
        import unicodedata

        def strip_accents(s: str) -> str:
            nfkd = unicodedata.normalize("NFKD", s)
            return "".join(c for c in nfkd if not unicodedata.combining(c))

        title_match = strip_accents(_normalise_title(result_name)) == strip_accents(
            _normalise_title(input_title)
        )
        if title_match:
            notes.append(f"title matches after accent normalisation: {result_name!r}")

    if not title_match:
        notes.append(f"title mismatch: input={input_title!r} result={result_name!r}")
        return MatchStatus.MISMATCH, notes

    # Year comparison
    if input_year is not None and result_year is not None:
        if input_year == result_year:
            notes.append(f"year matches: {result_year}")
            return MatchStatus.VERIFIED, notes
        else:
            notes.append(f"year mismatch: input={input_year} result={result_year}")
            return MatchStatus.MISMATCH, notes

    if input_year is not None and result_year is None:
        notes.append(f"input has year {input_year} but Qloo result has no year — ambiguous")
        return MatchStatus.AMBIGUOUS, notes

    if input_year is None and result_year is not None:
        notes.append(f"Qloo result has year {result_year} but input has no year — ambiguous")
        return MatchStatus.AMBIGUOUS, notes

    # Neither has a year — title-only match
    notes.append("title matches, no year available for verification — ambiguous")
    return MatchStatus.AMBIGUOUS, notes


class EntityResolver:
    """Resolves programme items to verified Qloo entities.

    Uses /search as the primary method.  Each item is resolved individually
    with explicit verification.
    """

    def __init__(self, client: Any, *, delay_s: float = 1.5) -> None:
        """Initialise with a Qloo client (live or mock).

        Args:
            client: A QlooClient or MockQlooClient with .search() method.
            delay_s: Delay between /search calls to respect rate limits.
        """
        self.client = client
        self.delay_s = delay_s

    async def resolve_item(
        self,
        title: str,
        year: int | None = None,
        external_id: str | None = None,
        external_family: str | None = None,
    ) -> ResolvedEntity:
        """Resolve a single programme item.

        Resolution priority:
        1. /search with title → verify name + year match
        2. If external ID supplied, also verify via /entities:
           - If /entities returns same entity → VERIFIED
           - If /entities returns different entity → MISMATCH
           - If /entities returns nothing → AMBIGUOUS (search match but ID unverified)
        3. If search fails, try /entities with external ID
        """
        # Method 1: /search with title
        result = await self._resolve_by_search(title, year)

        # If external ID is supplied, verify it via /entities endpoint
        if external_id and external_family:
            ext_result = await self._resolve_by_external_id(
                title, year, external_id, external_family
            )

            if result.match_status == MatchStatus.VERIFIED:
                # Search found a match — now verify external ID
                if ext_result.match_status == MatchStatus.VERIFIED:
                    # Both search and external ID verified
                    # Check if they agree on the entity
                    if result.qloo_entity_id == ext_result.qloo_entity_id:
                        # Same entity — confirmed VERIFIED
                        return ResolvedEntity(
                            input_title=result.input_title,
                            input_year=result.input_year,
                            input_external_id=external_id,
                            input_external_family=external_family,
                            qloo_entity_id=result.qloo_entity_id,
                            qloo_name=result.qloo_name,
                            qloo_entity_type=result.qloo_entity_type,
                            qloo_year=result.qloo_year,
                            qloo_disambiguation=result.qloo_disambiguation,
                            qloo_popularity=result.qloo_popularity,
                            match_status=MatchStatus.VERIFIED,
                            match_method=MatchMethod.EXTERNAL_ID,
                            verification_notes=[*result.verification_notes, f"external ID {external_id} confirmed — same entity"],
                            call_id=result.call_id,
                            search_query=result.search_query,
                            raw_result=result.raw_result,
                        )
                    else:
                        # Different entities — MISMATCH
                        return ResolvedEntity(
                            input_title=result.input_title,
                            input_year=result.input_year,
                            input_external_id=external_id,
                            input_external_family=external_family,
                            qloo_entity_id=result.qloo_entity_id,
                            qloo_name=result.qloo_name,
                            qloo_entity_type=result.qloo_entity_type,
                            qloo_year=result.qloo_year,
                            qloo_disambiguation=result.qloo_disambiguation,
                            qloo_popularity=result.qloo_popularity,
                            match_status=MatchStatus.MISMATCH,
                            match_method=MatchMethod.EXTERNAL_ID,
                            verification_notes=[*result.verification_notes, f"external ID conflict: search found {result.qloo_entity_id} " f"but external ID {external_id} maps to {ext_result.qloo_entity_id}"],
                            call_id=result.call_id,
                            search_query=result.search_query,
                            raw_result=result.raw_result,
                        )
                elif ext_result.match_status == MatchStatus.UNRESOLVED:
                    # External ID not found in Qloo — this is a MISMATCH
                    # The supplied ID doesn't correspond to any Qloo entity
                    return ResolvedEntity(
                        input_title=result.input_title,
                        input_year=result.input_year,
                        input_external_id=external_id,
                        input_external_family=external_family,
                        qloo_entity_id=result.qloo_entity_id,
                        qloo_name=result.qloo_name,
                        qloo_entity_type=result.qloo_entity_type,
                        qloo_year=result.qloo_year,
                        qloo_disambiguation=result.qloo_disambiguation,
                        qloo_popularity=result.qloo_popularity,
                        match_status=MatchStatus.MISMATCH,
                        match_method=MatchMethod.EXTERNAL_ID,
                        verification_notes=[*result.verification_notes, f"external ID {external_id} not found in Qloo — " f"supplied ID does not match any Qloo entity"],
                        call_id=result.call_id,
                        search_query=result.search_query,
                        raw_result=result.raw_result,
                    )
                else:
                    # External ID returned different status — use search result
                    return result

            elif result.match_status == MatchStatus.AMBIGUOUS:
                # Search was ambiguous — use external ID result if available
                if ext_result.match_status == MatchStatus.VERIFIED:
                    return ext_result
                return result

            elif result.match_status == MatchStatus.UNRESOLVED:
                # Search found nothing — use external ID result
                if ext_result.match_status != MatchStatus.UNRESOLVED:
                    return ext_result
                return result

        return result

    async def resolve_programme(
        self,
        items: list[dict[str, Any]],
    ) -> list[ResolvedEntity]:
        """Resolve a full programme of items.

        Each item should have at least 'title'.  Optional: 'year', 'imdb_id'.
        """
        results = []
        for i, item in enumerate(items):
            title = item.get("title", "")
            year = item.get("year")
            imdb_id = item.get("imdb_id")

            result = await self.resolve_item(
                title=title,
                year=year,
                external_id=imdb_id,
                external_family="imdb" if imdb_id else None,
            )
            results.append(result)

            # Rate limit delay (except after last item)
            if i < len(items) - 1 and self.delay_s > 0:
                await asyncio.sleep(self.delay_s)

        return results

    async def _resolve_by_search(
        self, title: str, year: int | None
    ) -> ResolvedEntity:
        """Resolve by searching Qloo's /search endpoint."""
        try:
            response = await self.client.search(
                query=title,
                take=5,
                tool="resolve:search",
            )
        except Exception as exc:
            return ResolvedEntity(
                input_title=title,
                input_year=year,
                match_status=MatchStatus.UNRESOLVED,
                verification_notes=[f"/search failed: {exc}"],
            )

        results = response.results
        if not results:
            return ResolvedEntity(
                input_title=title,
                input_year=year,
                match_status=MatchStatus.UNRESOLVED,
                call_id=response.call_id,
                search_query=title,
                verification_notes=["/search returned no results"],
            )

        # Try each result in order (Qloo ranks by relevance)
        best_status = MatchStatus.UNRESOLVED
        best_notes: list[str] = []
        best_entity = None

        for entity_raw in results:
            raw_dict = entity_raw.raw if entity_raw.raw else {}
            status, notes = verify_search_result(title, year, raw_dict)

            if status == MatchStatus.VERIFIED:
                # Perfect match — use it
                return ResolvedEntity(
                    input_title=title,
                    input_year=year,
                    qloo_entity_id=entity_raw.entity_id,
                    qloo_name=entity_raw.name,
                    qloo_entity_type=entity_raw.type,
                    qloo_year=_extract_year(raw_dict),
                    qloo_disambiguation=raw_dict.get("disambiguation"),
                    qloo_popularity=entity_raw.popularity,
                    match_status=MatchStatus.VERIFIED,
                    match_method=(
                        MatchMethod.SEARCH_WITH_YEAR if year else MatchMethod.SEARCH
                    ),
                    verification_notes=notes,
                    call_id=response.call_id,
                    search_query=title,
                    raw_result=raw_dict,
                )

            if status == MatchStatus.AMBIGUOUS and best_status == MatchStatus.UNRESOLVED:
                best_status = status
                best_notes = notes
                best_entity = entity_raw

            if status == MatchStatus.MISMATCH and best_status == MatchStatus.UNRESOLVED:
                # First result mismatches — this is still useful info
                best_status = status
                best_notes = notes
                best_entity = entity_raw

        # No VERIFIED match found — return the best candidate
        if best_entity:
            raw_dict = best_entity.raw if best_entity.raw else {}
            return ResolvedEntity(
                input_title=title,
                input_year=year,
                qloo_entity_id=best_entity.entity_id,
                qloo_name=best_entity.name,
                qloo_entity_type=best_entity.type,
                qloo_year=_extract_year(raw_dict),
                qloo_disambiguation=raw_dict.get("disambiguation"),
                qloo_popularity=best_entity.popularity,
                match_status=best_status,
                match_method=MatchMethod.SEARCH,
                verification_notes=best_notes,
                call_id=response.call_id,
                search_query=title,
                raw_result=raw_dict,
            )

        return ResolvedEntity(
            input_title=title,
            input_year=year,
            match_status=MatchStatus.UNRESOLVED,
            call_id=response.call_id,
            search_query=title,
            verification_notes=["no candidate matched"],
        )

    async def _resolve_by_external_id(
        self,
        title: str,
        year: int | None,
        external_id: str,
        external_family: str,
    ) -> ResolvedEntity:
        """Resolve by external ID lookup via /entities.

        Only marks VERIFIED if the returned entity actually includes
        the external ID in its response.
        """
        try:
            response = await self.client.entities(
                external_ids={external_family: [external_id]},
                tool=f"resolve:external_{external_family}",
            )
        except Exception as exc:
            return ResolvedEntity(
                input_title=title,
                input_year=year,
                input_external_id=external_id,
                input_external_family=external_family,
                match_status=MatchStatus.UNRESOLVED,
                verification_notes=[f"/entities failed: {exc}"],
            )

        if not response.results:
            return ResolvedEntity(
                input_title=title,
                input_year=year,
                input_external_id=external_id,
                input_external_family=external_family,
                match_status=MatchStatus.UNRESOLVED,
                call_id=response.call_id,
                verification_notes=["/entities returned no results for external ID"],
            )

        # Check each returned entity for the external ID
        for entity in response.results:
            raw = entity.raw if entity.raw else {}
            ext_ids = _extract_external_ids(raw, external_family)

            if external_id in ext_ids:
                # External ID confirmed in response — VERIFIED
                notes = [
                    f"external ID {external_id} confirmed in response",
                    f"entity name: {entity.name!r}",
                ]
                return ResolvedEntity(
                    input_title=title,
                    input_year=year,
                    input_external_id=external_id,
                    input_external_family=external_family,
                    qloo_entity_id=entity.entity_id,
                    qloo_name=entity.name,
                    qloo_entity_type=entity.type,
                    qloo_year=_extract_year(raw),
                    qloo_disambiguation=raw.get("disambiguation"),
                    qloo_popularity=entity.popularity,
                    match_status=MatchStatus.VERIFIED,
                    match_method=MatchMethod.EXTERNAL_ID,
                    verification_notes=notes,
                    call_id=response.call_id,
                    raw_result=raw,
                )

        # External IDs not returned in response — cannot verify
        return ResolvedEntity(
            input_title=title,
            input_year=year,
            input_external_id=external_id,
            input_external_family=external_family,
            match_status=MatchStatus.AMBIGUOUS,
            call_id=response.call_id,
            verification_notes=[
                f"/entities returned {len(response.results)} result(s) but "
                f"none included {external_id} in external.{external_family} — "
                "cannot verify mapping"
            ],
        )
