"""Deterministic safeguards for explicit references in Facility Manager requests.
They are only used to retrieve the room information from the question if the LLM fails, without wasting much extra tokens.
Questa è solo una funzionalità deterministica per evitare errori banali.
"""

from __future__ import annotations

import re

from agentic_bim_iot.domain.comfort import COMFORT_MEASUREMENTS


_ROOM_TYPE_PATTERN = re.compile(
    r"\b(?P<room>"
    r"kitchen|bathroom|bedroom|living\s+room|dining\s+room|"
    r"meeting\s+room(?:\s+[A-Za-z0-9_-]+)?|"
    r"conference\s+room(?:\s+[A-Za-z0-9_-]+)?|"
    r"classroom(?:\s+[A-Za-z0-9_-]+)?|"
    r"office(?:\s+[A-Za-z0-9_-]+)?|"
    r"laboratory(?:\s+[A-Za-z0-9_-]+)?|lab(?:\s+[A-Za-z0-9_-]+)?|"
    r"lobby|hallway|corridor|cafeteria|auditorium|"
    r"server\s+room|mechanical\s+room|storage\s+room"
    r")\b",
    flags=re.IGNORECASE,
)

_EXPLICIT_ROOM_PATTERN = re.compile(
    r"\broom\s+(?:number\s+|no\.?\s*)?"
    r"(?P<room>[A-Za-z0-9][A-Za-z0-9_-]*"
    r"(?:\s+(?!(?:to|and|with|at|is|has|should|please)\b)"
    r"[A-Za-z0-9][A-Za-z0-9_-]*){0,2})",
    flags=re.IGNORECASE,
)

_LOCATION_PHRASE_PATTERN = re.compile(
    r"\b(?:in|inside|within|for|of)\s+(?:the\s+)?(?P<room>[^?.,;!]+)",
    flags=re.IGNORECASE,
)

_MEASUREMENT_PHRASE_PATTERN = re.compile(
    r"\b(?:what(?:'s|\s+is)|show|give|get|read|retrieve|check)\s+"
    r"(?:me\s+)?(?:the\s+)?(?:latest\s+|current\s+)?"
    r"(?P<measurement>[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2})\s+"
    r"(?:in|inside|within|for|of)\b",
    flags=re.IGNORECASE,
)

_NON_ROOM_WORDS = {
    "building",
    "floor",
    "sensor",
    "device",
    "thermostat",
    "radiator",
    "actuator",
}

_TRAILING_PHRASES = (
    " right now",
    " at the moment",
    " currently",
    " today",
    " now",
    " please",
)

_CLAUSE_SEPARATORS = (
    " to ",
    " and ",
    " with ",
    " where ",
    " which ",
    " that ",
    " while ",
)


def extract_explicit_room_reference(user_query: str) -> str | None:
    query = user_query.strip()
    if not query:
        return None

    room_type_match = _ROOM_TYPE_PATTERN.search(query)
    if room_type_match:
        candidate = _clean_candidate(room_type_match.group("room"))
        if candidate:
            return _preserve_surface_case(query, candidate)

    explicit_match = _EXPLICIT_ROOM_PATTERN.search(query)
    if explicit_match:
        candidate = _clean_candidate(explicit_match.group("room"))
        if candidate:
            return candidate

    location_match = _LOCATION_PHRASE_PATTERN.search(query)
    if not location_match:
        return None

    candidate = _clean_location_phrase(location_match.group("room"))
    if not candidate:
        return None

    lowered_tokens = {
        token.casefold()
        for token in re.findall(r"[A-Za-z]+", candidate)
    }

    if lowered_tokens & _NON_ROOM_WORDS or len(candidate.split()) > 4:
        return None

    return candidate


def extract_explicit_measurement_reference(user_query: str) -> str | None:
    query = user_query.strip()
    if not query:
        return None

    for measurement in COMFORT_MEASUREMENTS:
        pattern = rf"\b{re.escape(measurement)}\b"
        if re.search(pattern, query, flags=re.IGNORECASE):
            return measurement

    match = _MEASUREMENT_PHRASE_PATTERN.search(query)
    if not match:
        return None

    candidate = _clean_candidate(match.group("measurement"))
    return candidate.casefold() if candidate else None


def _clean_location_phrase(value: str) -> str:
    candidate = value.strip()
    lowered = candidate.casefold()

    for separator in _CLAUSE_SEPARATORS:
        index = lowered.find(separator)
        if index >= 0:
            candidate = candidate[:index].strip()
            lowered = candidate.casefold()

    for suffix in _TRAILING_PHRASES:
        if lowered.endswith(suffix):
            candidate = candidate[:-len(suffix)].strip()
            lowered = candidate.casefold()

    return _clean_candidate(candidate)


def _clean_candidate(value: str) -> str:
    return value.strip(" \t\r\n'\"()[]{}")


def _preserve_surface_case(query: str, matched_value: str) -> str:
    match = re.search(re.escape(matched_value), query, flags=re.IGNORECASE)
    if match:
        return query[match.start():match.end()]
    return matched_value