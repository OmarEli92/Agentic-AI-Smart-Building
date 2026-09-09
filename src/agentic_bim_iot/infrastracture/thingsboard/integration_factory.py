from contextlib import ExitStack
from dataclasses import dataclass
from agentic_bim_iot.application.interfaces.actuation import ActuationService
from agentic_bim_iot.application.interfaces.telemetry import TelemetryService
from agentic_bim_iot.config.settings import Settings, ThingsBoardIntegration
from agentic_bim_iot.infrastracture.thingsboard.actuation import ThingsBoardActuationService
from agentic_bim_iot.infrastracture.thingsboard.actuator_device_registry import ThingsBoardActuatorDeviceRegistry
from agentic_bim_iot.infrastracture.thingsboard.device_registry import ThingsBoardDeviceRegistry
from agentic_bim_iot.infrastracture.thingsboard.factory import create_thingsboard_client
from agentic_bim_iot.infrastracture.thingsboard.mcp.actuation import ThingsBoardMCPActuationService
from agentic_bim_iot.infrastracture.thingsboard.mcp.actuator_device_registry import ThingsBoardMCPActuatorDeviceRegistry
from agentic_bim_iot.infrastracture.thingsboard.mcp.client import ThingsBoardMCPClient
from agentic_bim_iot.infrastracture.thingsboard.mcp.device_registry import ThingsBoardMCPDeviceRegistry
from agentic_bim_iot.infrastracture.thingsboard.mcp.telemetry import ThingsBoardMCPTelemetryService
from agentic_bim_iot.infrastracture.thingsboard.telemetry import ThingsBoardTelemetryService


@dataclass(slots=True, frozen=True)
class ThingsBoardServices:
    """ThingsBoard application services."""
    telemetry_service: TelemetryService
    actuation_service: ActuationService


def create_thingsboard_services(settings: Settings, resources: ExitStack,) -> ThingsBoardServices:
    """Create the configured ThingsBoard services."""
    if settings.thingsboard_integration == ThingsBoardIntegration.REST:
        client = create_thingsboard_client(settings=settings, resources=resources)
        device_registry = ThingsBoardDeviceRegistry(client=client)
        actuator_device_registry = ThingsBoardActuatorDeviceRegistry(client=client)
        telemetry_service = ThingsBoardTelemetryService(client=client, device_registry=device_registry)
        actuation_service = ThingsBoardActuationService(client=client, actuator_device_registry=actuator_device_registry)
        return ThingsBoardServices(telemetry_service=telemetry_service, actuation_service=actuation_service)

    if settings.thingsboard_integration == ThingsBoardIntegration.MCP:
        client = ThingsBoardMCPClient(sse_url=settings.thingsboard_mcp_sse_url, timeout_seconds=settings.thingsboard_mcp_timeout_seconds,)
        resources.callback(client.close)
        device_registry = ThingsBoardMCPDeviceRegistry(client=client)
        actuator_device_registry = ThingsBoardMCPActuatorDeviceRegistry(client=client)
        telemetry_service = ThingsBoardMCPTelemetryService(client=client, device_registry=device_registry)
        actuation_service = ThingsBoardMCPActuationService(client=client, actuator_device_registry=actuator_device_registry)
        return ThingsBoardServices(telemetry_service=telemetry_service, actuation_service=actuation_service)
    raise ValueError(f"Unsupported ThingsBoard integration: {settings.thingsboard_integration}")