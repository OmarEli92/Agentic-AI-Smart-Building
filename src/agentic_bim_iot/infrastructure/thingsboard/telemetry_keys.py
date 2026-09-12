def measurement_to_telemetry_key(measurement: str) -> str:
    """Convert a semantic measurement name into the telemetrykey currently used in ThingsBoard."""
    key = measurement.strip().casefold()
    if not key:
        raise ValueError("Measurement cannot be empty.")
    return key