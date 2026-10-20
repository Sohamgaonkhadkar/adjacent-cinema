"""Trusted entity resolver — converts programme items into verified Qloo entities.

Resolution strategy (priority order):
    1. /search with the documented movie type filter → verify title + year + type
    2. /entities with external ID → corroborate the echoed ID, title, year, type,
       and entity ID against any verified search result

Key safety rules:
    - NEVER assume returned order matches input order
    - NEVER trust a mapping without verification evidence
    - VERIFIED only with exact title/year agreement and explicit movie-type evidence
    - AMBIGUOUS for multiple exact movie candidates or insufficient title/year evidence
    - MISMATCH when title/year or explicit entity-type evidence conflicts
    - UNRESOLVED when the candidate or its movie type cannot be established

Rate limiting:
    - /search is rate-limited; the resolver adds delays between calls
    - Each item is resolved individually to allow verification
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any

from .contract import MatchMethod, MatchStatus, ResolvedEntity

_MOVIE_ENTITY_TYPE = "urn:entity:movie"


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
    """Extract explicit type evidence from Qloo's type, subtype, and types fields."""
    values: list[str] = []
    raw_types = entity.get("types")
    if isinstance(raw_types, str):
        values.append(raw_types)
    elif isinstance(raw_types, (list, tuple, set)):
        values.extend(str(value) for value in raw_types if value)

    for key in ("type", "subtype"):
        value = entity.get(key)
        if isinstance(value, str) and value:
            values.append(value)

    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _entity_payload(entity: Any) -> dict[str, Any]:
    """Copy an entity's raw response and fill parsed fields from the same payload."""
    raw = entity.raw if isinstance(entity.raw, dict) else {}
    payload = dict(raw)
    if not payload.get("name"):
        payload["name"] = entity.name or ""
    for key in ("type", "subtype", "types"):
        value = getattr(entity, key, None)
        if not payload.get(key) and value:
            payload[key] = value
    return payload


def _movie_type_state(entity: dict[str, Any]) -> str:
    """Return movie, non-movie, conflicting, or missing based on explicit Qloo types."""
    entity_types = {value for value in _extract_types(entity) if value.startswith("urn:entity:")}
    if _MOVIE_ENTITY_TYPE in entity_types:
        return "conflicting" if entity_types - {_MOVIE_ENTITY_TYPE} else "movie"
    return "non_movie" if entity_types else "missing"


def _movie_type_note(state: str, entity: dict[str, Any]) -> str:
    """Describe why explicit Qloo type evidence does or does not establish a movie."""
    entity_types = sorted(value for value in _extract_types(entity) if value.startswith("urn:entity:"))
    if state == "missing":
        return f"Qloo response lacks explicit {_MOVIE_ENTITY_TYPE} type evidence"
    if state == "conflicting":
        return f"conflicting Qloo entity-type evidence: {', '.join(entity_types)}"
    if state == "non_movie":
        return f"Qloo response identifies a non-movie entity type: {', '.join(entity_types)}"
    return f"Qloo response confirms movie type: {_MOVIE_ENTITY_TYPE}"


def _extract_ids_from_family_value(val: Any) -> list[str]:
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    if isinstance(val, (list, tuple, set)):
        return [str(i).strip() for i in val if i and str(i).strip()]
    if isinstance(val, dict):
        extracted: list[str] = []
        val_id = val.get("id")
        if val_id:
            extracted.append(str(val_id).strip())
        ids_field = val.get("ids")
        if isinstance(ids_field, (list, tuple, set)):
            extracted.extend(str(i).strip() for i in ids_field if i and str(i).strip())
        elif isinstance(ids_field, str) and ids_field.strip():
            extracted.append(ids_field.strip())
        return extracted
    return []


def _extract_external_ids(entity: dict[str, Any], family: str) -> list[str]:
    """Extract external IDs of a given family from a Qloo entity."""
    out: list[str] = []
    ext = entity.get("external", {})
    if isinstance(ext, dict) and family in ext:
        out.extend(_extract_ids_from_family_value(ext[family]))

    props = entity.get("properties", {})
    if isinstance(props, dict):
        pext = props.get("external", {})
        if isinstance(pext, dict) and family in pext:
            out.extend(_extract_ids_from_family_value(pext[family]))

    return list(dict.fromkeys(out))


def _include_related_call_ids(
    primary: ResolvedEntity, *related: ResolvedEntity
) -> ResolvedEntity:
    """Keep every Qloo call used for a resolution in the typed result."""
    call_ids: list[str] = []
    for entity in (primary, *related):
        if entity.call_id and entity.call_id not in call_ids:
            call_ids.append(entity.call_id)
        for call_id in entity.related_call_ids:
            if call_id and call_id not in call_ids:
                call_ids.append(call_id)
    primary_call_id = primary.call_id or (call_ids[0] if call_ids else None)
    related_call_ids = [call_id for call_id in call_ids if call_id != primary_call_id]
    return replace(
        primary,
        call_id=primary_call_id,
        related_call_ids=related_call_ids,
    )


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
        1. /search with the documented movie type filter → verify exact title + year + type
        2. If external ID supplied, verify its echoed value, Qloo entity ID, title/year, and type
        3. A verified result cannot override a title/year or type MISMATCH from the other lookup
        """
        # Method 1: typed /search with title
        result = await self._resolve_by_search(title, year)

        if not (external_id and external_family):
            return result

        # If an external ID is supplied, verify it via /entities as well. Both
        # calls remain addressable, including when one source finds a mismatch.
        ext_result = await self._resolve_by_external_id(
            title, year, external_id, external_family
        )

        if result.match_status == MatchStatus.VERIFIED:
            if ext_result.match_status == MatchStatus.VERIFIED:
                if result.qloo_entity_id == ext_result.qloo_entity_id:
                    combined = ResolvedEntity(
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
                        verification_notes=[
                            *result.verification_notes,
                            f"external ID {external_id} confirmed — same entity",
                        ],
                        call_id=result.call_id,
                        search_query=result.search_query,
                        raw_result=result.raw_result,
                    )
                    return _include_related_call_ids(combined, ext_result)

                combined = ResolvedEntity(
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
                    verification_notes=[
                        *result.verification_notes,
                        f"external ID conflict: search found {result.qloo_entity_id} "
                        f"but external ID {external_id} maps to {ext_result.qloo_entity_id}",
                    ],
                    call_id=result.call_id,
                    search_query=result.search_query,
                    raw_result=result.raw_result,
                )
                return _include_related_call_ids(combined, ext_result)

            if ext_result.match_status == MatchStatus.UNRESOLVED:
                # Keep the existing conservative rule: a supplied external ID
                # that Qloo cannot resolve cannot corroborate a search match.
                combined = ResolvedEntity(
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
                    verification_notes=[
                        *result.verification_notes,
                        f"external ID {external_id} not found in Qloo — supplied ID does not match any Qloo entity",
                    ],
                    call_id=result.call_id,
                    search_query=result.search_query,
                    raw_result=result.raw_result,
                )
                return _include_related_call_ids(combined, ext_result)

            if ext_result.match_status == MatchStatus.MISMATCH:
                return _include_related_call_ids(ext_result, result)

            if (
                ext_result.qloo_entity_id
                and result.qloo_entity_id
                and ext_result.qloo_entity_id != result.qloo_entity_id
            ):
                conflict = replace(
                    ext_result,
                    match_status=MatchStatus.MISMATCH,
                    verification_notes=[
                        *ext_result.verification_notes,
                        "external-ID result conflicts with the title-and-year verified search entity",
                    ],
                )
                return _include_related_call_ids(conflict, result)
            return _include_related_call_ids(result, ext_result)

        if result.match_status == MatchStatus.AMBIGUOUS:
            if ext_result.match_status in {MatchStatus.VERIFIED, MatchStatus.MISMATCH}:
                return _include_related_call_ids(ext_result, result)
            return _include_related_call_ids(result, ext_result)

        if result.match_status == MatchStatus.UNRESOLVED:
            if ext_result.match_status != MatchStatus.UNRESOLVED:
                return _include_related_call_ids(ext_result, result)
            return _include_related_call_ids(result, ext_result)

        if result.match_status == MatchStatus.MISMATCH:
            if ext_result.match_status == MatchStatus.VERIFIED:
                # A positive ID lookup cannot erase contradictory title/year
                # evidence from search. Keep the mismatch and both call IDs so
                # a reviewer can inspect the cross-endpoint disagreement.
                mismatch = replace(
                    result,
                    input_external_id=external_id,
                    input_external_family=external_family,
                    verification_notes=[
                        *result.verification_notes,
                        "external-ID lookup verified a candidate, but cannot override the title-search mismatch",
                    ],
                )
                return _include_related_call_ids(mismatch, ext_result)
            if ext_result.match_status == MatchStatus.MISMATCH:
                return _include_related_call_ids(ext_result, result)
            return _include_related_call_ids(result, ext_result)

        return _include_related_call_ids(result, ext_result)

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

    async def _resolve_by_search(self, title: str, year: int | None) -> ResolvedEntity:
        """Resolve by searching only for movies, then verify every candidate."""
        try:
            response = await self.client.search(
                query=title,
                types=[_MOVIE_ENTITY_TYPE],
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

        search_method = MatchMethod.SEARCH_WITH_YEAR if year is not None else MatchMethod.SEARCH

        def candidate_result(
            entity: Any,
            payload: dict[str, Any],
            status: MatchStatus,
            notes: list[str],
        ) -> ResolvedEntity:
            type_state = _movie_type_state(payload)
            return ResolvedEntity(
                input_title=title,
                input_year=year,
                qloo_entity_id=entity.entity_id or None,
                qloo_name=entity.name or payload.get("name"),
                qloo_entity_type=(
                    _MOVIE_ENTITY_TYPE if type_state == "movie" else entity.type or entity.subtype
                ),
                qloo_year=_extract_year(payload),
                qloo_disambiguation=payload.get("disambiguation"),
                qloo_popularity=entity.popularity,
                match_status=status,
                match_method=search_method,
                verification_notes=notes,
                call_id=response.call_id,
                search_query=title,
                raw_result=payload,
            )

        # Keep all exact typed-movie matches before choosing. Qloo's relevance
        # order cannot safely distinguish duplicate title/year identities.
        movie_candidates: list[tuple[Any, dict[str, Any], list[str]]] = []
        movie_entity_ids: set[str] = set()
        missing_type_candidate: tuple[Any, dict[str, Any], list[str]] | None = None
        non_movie_candidate: tuple[Any, dict[str, Any], list[str]] | None = None
        conflicting_type_candidate: tuple[Any, dict[str, Any], list[str]] | None = None
        ambiguous_movie_candidate: tuple[Any, dict[str, Any], list[str]] | None = None
        identity_mismatch_candidate: tuple[Any, dict[str, Any], list[str]] | None = None

        for entity in results:
            payload = _entity_payload(entity)
            identity_status, identity_notes = verify_search_result(title, year, payload)
            type_state = _movie_type_state(payload)

            if identity_status == MatchStatus.MISMATCH:
                if identity_mismatch_candidate is None:
                    identity_mismatch_candidate = (entity, payload, identity_notes)
                continue

            if type_state == "non_movie":
                if non_movie_candidate is None:
                    non_movie_candidate = (
                        entity,
                        payload,
                        [*identity_notes, _movie_type_note(type_state, payload)],
                    )
                continue

            if type_state == "conflicting":
                if conflicting_type_candidate is None:
                    conflicting_type_candidate = (
                        entity,
                        payload,
                        [*identity_notes, _movie_type_note(type_state, payload)],
                    )
                continue

            if type_state == "missing":
                if missing_type_candidate is None:
                    missing_type_candidate = (
                        entity,
                        payload,
                        [*identity_notes, _movie_type_note(type_state, payload)],
                    )
                continue

            if identity_status == MatchStatus.VERIFIED:
                entity_id = entity.entity_id or ""
                if not entity_id or entity_id not in movie_entity_ids:
                    movie_candidates.append(
                        (entity, payload, [*identity_notes, _movie_type_note(type_state, payload)])
                    )
                    if entity_id:
                        movie_entity_ids.add(entity_id)
            elif ambiguous_movie_candidate is None:
                ambiguous_movie_candidate = (
                    entity,
                    payload,
                    [*identity_notes, _movie_type_note(type_state, payload)],
                )

        if len(movie_candidates) > 1:
            return ResolvedEntity(
                input_title=title,
                input_year=year,
                match_status=MatchStatus.AMBIGUOUS,
                match_method=search_method,
                verification_notes=[
                    f"{len(movie_candidates)} exact typed movie candidates match title and year; "
                    "no entity selected",
                ],
                call_id=response.call_id,
                search_query=title,
            )

        if len(movie_candidates) == 1:
            entity, payload, notes = movie_candidates[0]
            if not entity.entity_id:
                return candidate_result(
                    entity,
                    payload,
                    MatchStatus.UNRESOLVED,
                    [*notes, "typed movie candidate has no Qloo entity ID"],
                )
            return candidate_result(entity, payload, MatchStatus.VERIFIED, notes)

        if conflicting_type_candidate is not None:
            entity, payload, notes = conflicting_type_candidate
            return candidate_result(entity, payload, MatchStatus.MISMATCH, notes)

        if non_movie_candidate is not None:
            entity, payload, notes = non_movie_candidate
            return candidate_result(entity, payload, MatchStatus.MISMATCH, notes)

        if missing_type_candidate is not None:
            entity, payload, notes = missing_type_candidate
            return candidate_result(entity, payload, MatchStatus.UNRESOLVED, notes)

        if ambiguous_movie_candidate is not None:
            entity, payload, notes = ambiguous_movie_candidate
            return candidate_result(entity, payload, MatchStatus.AMBIGUOUS, notes)

        if identity_mismatch_candidate is not None:
            entity, payload, notes = identity_mismatch_candidate
            return candidate_result(entity, payload, MatchStatus.MISMATCH, notes)

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

        # Check each returned entity for the external ID. An explicitly
        # different ID in the requested family is a contradiction; a response
        # that omits that family remains merely unverified/ambiguous.
        conflicting_entity = None
        conflicting_ids: list[str] = []
        for entity in response.results:
            raw = entity.raw if entity.raw else {}
            ext_ids = _extract_external_ids(raw, external_family)

            if external_id in ext_ids:
                # The echoed external ID is necessary but not sufficient:
                # the entity ID, title/year, and explicit movie type must agree.
                identity_payload = _entity_payload(entity)
                identity_status, identity_notes = verify_search_result(title, year, identity_payload)
                type_state = _movie_type_state(identity_payload)
                status = identity_status
                notes = [
                    f"external ID {external_id} confirmed in response",
                    *identity_notes,
                ]

                if identity_status != MatchStatus.MISMATCH:
                    if type_state == "missing":
                        status = MatchStatus.UNRESOLVED
                        notes.append(_movie_type_note(type_state, identity_payload))
                    elif type_state in {"non_movie", "conflicting"}:
                        status = MatchStatus.MISMATCH
                        notes.append(_movie_type_note(type_state, identity_payload))
                    elif not entity.entity_id:
                        status = MatchStatus.UNRESOLVED
                        notes.append("external-ID response has no Qloo entity ID to corroborate")
                    else:
                        notes.append(_movie_type_note(type_state, identity_payload))

                return ResolvedEntity(
                    input_title=title,
                    input_year=year,
                    input_external_id=external_id,
                    input_external_family=external_family,
                    qloo_entity_id=entity.entity_id or None,
                    qloo_name=entity.name or identity_payload.get("name"),
                    qloo_entity_type=(
                        _MOVIE_ENTITY_TYPE if type_state == "movie" else entity.type or entity.subtype
                    ),
                    qloo_year=_extract_year(identity_payload),
                    qloo_disambiguation=identity_payload.get("disambiguation"),
                    qloo_popularity=entity.popularity,
                    match_status=status,
                    match_method=MatchMethod.EXTERNAL_ID,
                    verification_notes=notes,
                    call_id=response.call_id,
                    raw_result=identity_payload,
                )

            if ext_ids:
                conflicting_entity = conflicting_entity or entity
                conflicting_ids.extend(value for value in ext_ids if value not in conflicting_ids)

        if conflicting_entity is not None:
            raw = conflicting_entity.raw if conflicting_entity.raw else {}
            identity_payload = {
                **raw,
                "name": raw.get("name") or conflicting_entity.name or "",
            }
            _identity_status, identity_notes = verify_search_result(
                title, year, identity_payload
            )
            return ResolvedEntity(
                input_title=title,
                input_year=year,
                input_external_id=external_id,
                input_external_family=external_family,
                qloo_entity_id=conflicting_entity.entity_id,
                qloo_name=conflicting_entity.name,
                qloo_entity_type=conflicting_entity.type,
                qloo_year=_extract_year(raw),
                qloo_disambiguation=raw.get("disambiguation"),
                qloo_popularity=conflicting_entity.popularity,
                match_status=MatchStatus.MISMATCH,
                match_method=MatchMethod.EXTERNAL_ID,
                verification_notes=[
                    f"/entities did not return supplied {external_family} ID {external_id}; "
                    f"candidate listed conflicting ID(s): {', '.join(conflicting_ids)}",
                    *identity_notes,
                ],
                call_id=response.call_id,
                raw_result=raw,
            )

        # No candidate echoed this ID family, so the lookup cannot verify or
        # contradict the supplied ID. Keep it ambiguous rather than guessing.
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
