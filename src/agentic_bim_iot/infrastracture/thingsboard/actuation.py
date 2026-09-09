import json
import time
from uuid import uuid4
from tb_ce_client import ThingsboardClient
from tb_ce_client.exceptions import ApiException
from agentic_bim_iot.application.interfaces.actuation import ActuationService
from agentic_bim_iot.application.interfaces.actuator_device_registry import ActuatorDeviceRegistry
from agentic_bim_iot.application.interfaces.device_registry import DeviceRegistryError
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.domain.command import ActuationCommand
from agentic_bim_iot.domain.execution import ExecutionResult, ExecutionStatus
from agentic_bim_iot.infrastracture.observability.tracing import trace_observation


class ThingsBoardActuationService(ActuationService):
    """The Thingsboard actuation service responsible for excuting the physical commands on the actuators"""
    def __init__(self, client: ThingsboardClient, actuator_device_registry: ActuatorDeviceRegistry) -> None:
        self._client = client
        self._actuator_device_registry = actuator_device_registry

    def execute(self, command: ActuationCommand) -> ExecutionResult:
        started_at_ms = time.time_ns() // 1_000_000
        execution_id = str(uuid4())
        thingsboard_device_id = None
        with trace_observation("thingsboard.actuation", as_type="tool",input_payload={"command": command.model_dump(mode="json")}) as observation:
            actuator = ActuatorReference(
                room_reference=command.room_reference,
                controlled_measurement=command.measurement,
                actuator_guid=command.actuator_guid,
                actuator_type=command.actuator_type,
            )
            try:
                device = self._actuator_device_registry.resolve(actuator)
                thingsboard_device_id = device.platform_device_id
                telemetry_key = self._target_telemetry_key(command.measurement)
                payload = {
                    telemetry_key: command.target_value,
                    "actuatorState": "commanded",
                    "lastCommandId": command.command_id,
                    "lastExecutionId": execution_id,
                    "lastCommandTimestamp": started_at_ms,
                }
                self._client.save_entity_telemetry(
                    entity_type="DEVICE",
                    entity_id=device.platform_device_id,
                    scope="ANY",
                    body=json.dumps(payload),
                )
                result = ExecutionResult(
                    execution_id=execution_id,
                    command_id=command.command_id,
                    proposal_id=command.proposal_id,
                    room_reference=command.room_reference,
                    measurement=command.measurement,
                    actuator_guid=command.actuator_guid,
                    thingsboard_device_id=device.platform_device_id,
                    target_value=command.target_value,
                    unit=command.unit,
                    status=ExecutionStatus.SUCCEEDED,
                    started_at_ms=started_at_ms,
                    completed_at_ms=time.time_ns() // 1_000_000,
                    error=None,
                )

            except (DeviceRegistryError, ApiException) as exc:
                result = ExecutionResult(
                    execution_id=execution_id,
                    command_id=command.command_id,
                    proposal_id=command.proposal_id,
                    room_reference=command.room_reference,
                    measurement=command.measurement,
                    actuator_guid=command.actuator_guid,
                    thingsboard_device_id=thingsboard_device_id,
                    target_value=command.target_value,
                    unit=command.unit,
                    status=ExecutionStatus.FAILED,
                    started_at_ms=started_at_ms,
                    completed_at_ms=time.time_ns() // 1_000_000,
                    error=str(exc),
                )
            observation.update(output=result.model_dump(mode="json"))
            return result

    @staticmethod
    def _target_telemetry_key(measurement: str) -> str:
        normalized = measurement.strip().casefold()
        if not normalized:
            raise ValueError("Measurement is required to build an actuator telemetry key.")
        return f"target{normalized[0].upper()}{normalized[1:]}"