import json
from typing import Any
from agentic_bim_iot.infrastracture.thingsboard.mcp.client import ThingsBoardMCPError


def normalize_payload(payload: Any) -> Any:
    """Normalize a ThingsBoard MCP response."""
    if isinstance(payload, str):
        value = payload.strip()
        if not value:
            return None
        try:
            return normalize_payload(json.loads(value))

        except json.JSONDecodeError:
            return value

    if isinstance(payload, dict):
        if len(payload) == 1 and "result" in payload:
            return normalize_payload(payload["result"])
        if len(payload) == 1 and "data" in payload:
            return normalize_payload(payload["data"])
    return payload


def extract_device(payload: Any, expected_name: str) -> tuple[str, str]:
    """Extract a ThingsBoard device."""
    device = normalize_payload(payload)
    if not isinstance(device, dict):
        raise ThingsBoardMCPError(f"ThingsBoard MCP did not return device '{expected_name}'.")
    raw_id = device.get("id")
    if isinstance(raw_id, dict):
        device_id = raw_id.get("id")
    else:
        device_id = raw_id
    if not isinstance(device_id, str) or not device_id.strip():
        raise ThingsBoardMCPError("ThingsBoard MCP returned a device without an ID.")
    device_name = device.get("name")
    if not isinstance(device_name, str) or not device_name.strip():
        device_name = expected_name
    return (device_id, device_name)


def extract_latest_telemetry(payload: Any, telemetry_key: str) -> tuple[Any, int]:
    """Extract the latest telemetry value from a ThingsBoard MCP response."""
    telemetry = normalize_payload(payload)
    candidates: list[dict[str, Any]] = []
    # Format 1:
    #
    # {
    #     "temperature": [
    #         {"ts": ..., "value": 18}
    #     ]
    # }
    if isinstance(telemetry, dict):
        values = telemetry.get(telemetry_key)
        if isinstance(values, list):
            candidates = [item for item in value if isinstance(item, dict)]
        elif "ts" in telemetry:
            candidates = [telemetry]
    # Format 2 used by the current ThingsBoard MCP server:
    #
    # [
    #     {
    #         "ts": ...,
    #         "key": "temperature",
    #         "value": 18,
    #         "kv": {...}
    #     }
    # ]
    elif isinstance(telemetry, list):
        candidates = [item for item in telemetry if isinstance(item, dict)]
    else:
        raise ThingsBoardMCPError("ThingsBoard MCP returned an invalid telemetry payload.")
    if not candidates:
        raise ThingsBoardMCPError(f"No telemetry is available for the key '{telemetry_key}'.")
    matching_candidates: list[dict[str, Any]] = []
    for item in candidates:
        item_key = item.get("key")
        if item_key is None:
            kv = item.get("kv")
            if isinstance(kv, dict):
                item_key = kv.get("key")
        if item_key is None or item_key == telemetry_key:
            matching_candidates.append(item)
    if not matching_candidates:
        raise ThingsBoardMCPError(f"No telemetry is available for the key '{telemetry_key}'.")
    try:
        latest = max(matching_candidates, key=lambda item: int(item.get("ts", -1)))
    except (TypeError, ValueError) as exc:
        raise ThingsBoardMCPError("ThingsBoard returned an invalid telemetry timestamp.") from exc
    timestamp = latest.get("ts")
    if timestamp is None:
        raise ThingsBoardMCPError("ThingsBoard returned telemetry without a timestamp.")
    try:
        timestamp_ms = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise ThingsBoardMCPError("ThingsBoard MCP returned an invalid telemetry timestamp.") from exc
    if "value" in latest:
        value = latest["value"]
    else:
        kv = latest.get("kv")
        if isinstance(kv, dict) and "value" in kv:
            value = kv["value"]
        else:
            raise ThingsBoardMCPError("ThingsBoard MCP returned telemetry without a value.")
    return value, timestamp_ms


def ensure_successful_write(payload: Any) -> None:
    """Validate a ThingsBoard MCP write."""
    result = normalize_payload(payload)
    if result is None:
        return
    if not isinstance(result, dict):
        raise ThingsBoardMCPError("ThingsBoard MCP returned an invalid write result.")
    status = str(result.get("status","")).strip()
    if not status:
        return
    normalized_status = status.casefold()
    if "failed" in normalized_status or "error" in normalized_status:
        raise ThingsBoardMCPError(status)