from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.sensor import SensorResolutionError,SensorResolver
from agentic_bim_iot.application.interfaces.telemetry import TelemetryService,TelemetryServiceError


class TelemetryInformationNode:
    """The Node responsible for handling informational telemetry requests."""
    def __init__(self,sensor_resolver: SensorResolver,telemetry_service: TelemetryService) -> None:
        self._sensor_resolver = sensor_resolver
        self._telemetry_service = telemetry_service

    def __call__(self,state: AgentState) -> dict[str, object]:
        decision = state["supervisor_decision"]
        room = decision.room_reference
        measurement = decision.measurement_reference
        if not room or not measurement:
            return {"final_answer": "I need both a room and a measurement to retrieve telemetry."}

        try:
            sensor = self._sensor_resolver.resolve(room_reference=room,measurement=measurement,)
            reading = self._telemetry_service.read_latest(sensor)

        except (SensorResolutionError,TelemetryServiceError) as exc:
            return {
                "telemetry_error": str(exc),
                "final_answer": "I could not retrieve the requested telemetry.",
            }

        return {
            "sensor_reference": sensor,
            "telemetry_reading": reading,
            "final_answer": f"The latest {measurement} in {room} is {reading.value}."
        }