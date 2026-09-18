import time
from agentic_bim_iot.application.interfaces.comfort import ComfortEngineError
from agentic_bim_iot.application.interfaces.sensor import SensorResolutionError, SensorResolver
from agentic_bim_iot.application.interfaces.telemetry import TelemetryService, TelemetryServiceError
from agentic_bim_iot.domain.comfort import  COMFORT_MEASUREMENTS,COMFORT_RANGES,MEASUREMENT_UNITS,ComfortAssessment,ParameterComfortAssessment,compute_comfort_index,score_parameter
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.infrastructure.observability.tracing import trace_observation


class RoomComfortEngine:
    """Evaluate the environmental comfort of a room."""
    def __init__(self, sensor_resolver: SensorResolver, telemetry_service: TelemetryService) -> None:
        self._sensor_resolver = sensor_resolver
        self._telemetry_service = telemetry_service

    def assess(self, room_reference: str) -> ComfortAssessment:
        """Generate the comfort assessment for a room."""
        normalized_room = room_reference.strip()
        if not normalized_room:
            raise ComfortEngineError("Room reference cannot be empty.")
        with trace_observation(
            "comfort.assess",
            as_type="span",
            input_payload={
                "room_reference": normalized_room,
                "measurements": list(COMFORT_MEASUREMENTS),
            },
        ) as observation:
            try:
                sensors = self._sensor_resolver.resolve_many(room_reference=normalized_room, measurements=COMFORT_MEASUREMENTS,)
            except SensorResolutionError as exc:
                raise ComfortEngineError(f"Could not resolve sensors for room '{normalized_room}'.") from exc
            sensors_by_measurement = {
                sensor.measurement.strip().casefold(): sensor
                for sensor in sensors
            }
            parameters = {
                measurement: self._read_parameter(
                    measurement=measurement,
                    sensor=sensors_by_measurement.get(measurement.casefold()),
                )
                for measurement in COMFORT_MEASUREMENTS
            }
            total_score, label, _ = compute_comfort_index(
                temperature=parameters["temperature"].value,
                humidity=parameters["humidity"].value,
                brightness=parameters["brightness"].value,
            )
            missing_measurements = tuple(
                measurement
                for measurement, assessment in parameters.items()
                if assessment.value is None
            )
            assessment = ComfortAssessment(
                room_reference=normalized_room,
                total_score=total_score,
                label=label,
                parameters=parameters,
                data_complete=not missing_measurements,
                missing_measurements=missing_measurements,
                evaluated_at_ms=int(time.time() * 1000),
            )
            observation.update(
                output={
                    "total_score": assessment.total_score,
                    "label": assessment.label.value,
                    "data_complete": assessment.data_complete,
                    "missing_measurements": list(assessment.missing_measurements),
                    "parameters": {
                        m: p.model_dump(mode="json")
                        for m, p in assessment.parameters.items()
                    },
                }
            )
            return assessment

    def _read_parameter(self, measurement: str, sensor: SensorReference | None) -> ParameterComfortAssessment:
        """Read telemetry for an already resolved sensor reference."""
        low, high = COMFORT_RANGES[measurement]
        if sensor is None:
            return self._missing_parameter(measurement=measurement)
        try:
            reading = self._telemetry_service.read_latest(sensor)
            value = float(reading.value)
        except TelemetryServiceError as exc:
            raise ComfortEngineError(
                "Telemetry retrieval failed for "
                f"room='{sensor.room_reference}', "
                f"measurement='{measurement}', "
                f"sensor_guid='{sensor.sensor_guid}': {exc}"
            ) from exc
        except (TypeError, ValueError) as exc:
            raise ComfortEngineError(
                "Invalid telemetry value for "
                f"room='{sensor.room_reference}', "
                f"measurement='{measurement}', "
                f"sensor_guid='{sensor.sensor_guid}': {exc}"
            ) from exc

        return ParameterComfortAssessment(
            measurement=measurement,
            value=value,
            unit=MEASUREMENT_UNITS[measurement],
            minimum=low,
            maximum=high,
            score=score_parameter(measurement, value),
            within_range=low <= value <= high,
            sensor_guid=sensor.sensor_guid,
            timestamp_ms=reading.timestamp_ms,
        )

    @staticmethod
    def _missing_parameter(measurement: str, sensor_guid: str | None = None) -> ParameterComfortAssessment:
        """Build an assessment for unavailable telemetry."""
        low, high = COMFORT_RANGES[measurement]
        return ParameterComfortAssessment(
            measurement=measurement,
            value=None,
            unit=MEASUREMENT_UNITS[measurement],
            minimum=low,
            maximum=high,
            score=0,
            within_range=None,
            sensor_guid=sensor_guid,
            timestamp_ms=None
        )