import json


def build_reference_cache_key(*, room_reference: str, measurement: str) -> str:
    payload = {
        "room_reference": _normalize(room_reference),
        "measurement": _normalize(measurement),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())