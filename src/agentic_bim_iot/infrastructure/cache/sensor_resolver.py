import logging
from typing import Any
from agentic_bim_iot.application.interfaces.cache import CacheStore
from agentic_bim_iot.application.interfaces.sensor import SensorResolver
from agentic_bim_iot.domain.sensor import SensorReference
from agentic_bim_iot.infrastructure.cache.base_cache_resolver import BaseCachedReferenceResolver

logger = logging.getLogger("agentic_bim_iot.cache.sensor")


class CachedSensorResolver(BaseCachedReferenceResolver[SensorReference, SensorResolver]):
    """Cache decorator for semantic sensor resolution, 
    that implements the BaseCachedReferenceResolver abstract class"""

    def __init__(self, delegate: SensorResolver, cache: CacheStore, ttl_seconds: int, fail_open: bool = True) -> None:
        super().__init__(delegate=delegate, cache=cache, ttl_seconds=ttl_seconds, fail_open=fail_open, namespace="sensor_reference", model_cls=SensorReference, logger=logger, entity_name="sensor")

    def _extract_measurement_name(self, reference: SensorReference) -> str:
        return reference.measurement

    def _extract_trace_output(self, reference: SensorReference) -> dict[str, Any]:
        return {"sensor_guid": reference.sensor_guid}