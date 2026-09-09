import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ValidationError
from agentic_bim_iot.application.interfaces.cache import CacheStore, CacheStoreError
from agentic_bim_iot.infrastracture.cache.keys import build_reference_cache_key
from agentic_bim_iot.infrastracture.observability.tracing import trace_observation

T = TypeVar("T", bound=BaseModel)
D = TypeVar("D")


class BaseCachedReferenceResolver(ABC, Generic[T, D]):
    """The abstract class for resolving the references of sensors and actuators"""
    def __init__(self, *, delegate: D, cache: CacheStore, ttl_seconds: int, fail_open: bool = True, namespace: str, model_cls: type[T], logger: logging.Logger, entity_name: str) -> None:
        self._delegate = delegate
        self._cache = cache
        self._ttl_seconds = ttl_seconds
        self._fail_open = fail_open
        self._namespace = namespace
        self._model_cls = model_cls
        self._logger = logger
        self._entity_name = entity_name


    @abstractmethod
    def _extract_measurement_name(self, reference: T) -> str:
        ...


    @abstractmethod
    def _extract_trace_output(self, reference: T) -> dict[str, Any]:
        ...


    def resolve(self, room_reference: str, measurement: str) -> T:
        room = room_reference.strip()
        normalized_measurement = measurement.strip().casefold()
        key = build_reference_cache_key(room_reference=room, measurement=normalized_measurement)
        cached_reference = self._get_cached_reference(key=key, room_reference=room, measurement=normalized_measurement)
        if cached_reference is not None:
            return cached_reference
        reference = self._delegate.resolve(room, normalized_measurement)
        self._store_reference(reference)
        return reference


    def resolve_many(self, room_reference: str, measurements: Sequence[str]) -> list[T]:
        room = room_reference.strip()
        requested_measurements = self._normalize_measurements(measurements)
        if not requested_measurements:
            return []
        cached_references: dict[str, T] = {}
        for measurement in requested_measurements:
            key = build_reference_cache_key(room_reference=room, measurement=measurement)
            reference = self._get_cached_reference(key=key, room_reference=room, measurement=measurement)
            if reference is not None:
                cached_references[measurement] = reference
        if len(cached_references) == len(requested_measurements):
            return [cached_references[m] for m in requested_measurements]
        resolved_references = self._delegate.resolve_many(room, requested_measurements)
        for reference in resolved_references:
            self._store_reference(reference)
        return resolved_references


    def _get_cached_reference(self, *, key: str, room_reference: str, measurement: str) -> T | None:
        trace_name = f"bim_cache.{self._namespace}.lookup"
        with trace_observation(trace_name, as_type="span", input_payload={"room_reference": room_reference, "measurement": measurement}, metadata={"cache_namespace": self._namespace}) as observation:
            try:
                cached_value = self._cache.get(self._namespace, key)
            except CacheStoreError:
                if not self._fail_open:
                    raise
                self._logger.warning("%s cache lookup failed. Falling back to semantic resolution.", self._entity_name.capitalize())
                observation.update(output={"cache_hit": False, "cache_error": True})
                return None
            if cached_value is None:
                observation.update(output={"cache_hit": False})
                return None
            try:
                reference = self._model_cls.model_validate_json(cached_value)
            except ValidationError:
                self._logger.warning("Invalid %s found in cache. Removing the entry.", self._model_cls.__name__)
                self._delete_invalid_entry(key)
                observation.update(output={"cache_hit": False, "corrupt_entry": True})
                return None
            output = {"cache_hit": True, **self._extract_trace_output(reference)}
            observation.update(output=output)
            return reference


    def _store_reference(self, reference: T) -> None:
        key = build_reference_cache_key(room_reference=reference.room_reference, measurement=self._extract_measurement_name(reference))
        try:
            self._cache.set(self._namespace, key, reference.model_dump_json(), ttl_seconds=self._ttl_seconds)
        except CacheStoreError:
            if not self._fail_open:
                raise
            self._logger.warning("%s cache write failed. Continuing without caching.", self._entity_name.capitalize())


    def _delete_invalid_entry(self, key: str) -> None:
        try:
            self._cache.delete(self._namespace, key)
        except CacheStoreError:
            if not self._fail_open:
                raise


    @staticmethod
    def _normalize_measurements(measurements: Sequence[str]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for measurement in measurements:
            value = measurement.strip().casefold()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return tuple(normalized)