import logging
from typing import Any
from agentic_bim_iot.application.interfaces.actuator import ActuatorResolver
from agentic_bim_iot.application.interfaces.cache import CacheStore
from agentic_bim_iot.domain.actuator import ActuatorReference
from agentic_bim_iot.infrastructure.cache.base_cache_resolver import BaseCachedReferenceResolver

logger = logging.getLogger("agentic_bim_iot.cache.actuator")


class CachedActuatorResolver(BaseCachedReferenceResolver[ActuatorReference, ActuatorResolver]):
    """Cache decorator for semantic actuator resolution."""

    def __init__(self, delegate: ActuatorResolver, cache: CacheStore, ttl_seconds: int, fail_open: bool = True) -> None:
        super().__init__(delegate=delegate, cache=cache, ttl_seconds=ttl_seconds, fail_open=fail_open, namespace="actuator_reference",
                         model_cls=ActuatorReference, logger=logger, entity_name="actuator")

    def _extract_measurement_name(self, reference: ActuatorReference) -> str:
        return reference.controlled_measurement

    def _extract_trace_output(self, reference: ActuatorReference) -> dict[str, Any]:
        return {"actuator_guid": reference.actuator_guid, "actuator_type": reference.actuator_type}