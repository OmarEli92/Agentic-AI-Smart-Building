import hashlib
from redis import Redis
from redis.exceptions import RedisError
from agentic_bim_iot.application.interfaces.cache import CacheStoreError


class RedisCacheStore:
    """Redis implementation of the cache contract."""
    def __init__(self, redis_url: str, key_prefix: str, version: str, default_ttl_seconds: int) -> None:
        self._key_prefix = key_prefix.strip()
        self._version = version.strip()
        self._default_ttl_seconds = default_ttl_seconds
        
        if not self._key_prefix:
            raise ValueError("Cache key prefix cannot be empty.")
        if not self._version:
            raise ValueError("Cache version cannot be empty.")

        self._client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            health_check_interval=30
        )

    def get(self, namespace: str, key: str) -> str | None:
        try:
            return self._client.get(self._physical_key(namespace, key))
        except RedisError as exc:
            raise CacheStoreError("Redis cache lookup failed.") from exc


    def set(self, namespace: str, key: str, value: str, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        try:
            self._client.set(
                self._physical_key(namespace, key),
                value,
                ex=ttl,
            )
        except RedisError as exc:
            raise CacheStoreError("Redis cache write failed.") from exc


    def delete(self, namespace: str, key: str) -> None:
        try:
            self._client.delete(self._physical_key(namespace, key))
        except RedisError as exc:
            raise CacheStoreError("Redis cache delete failed.") from exc


    def clear(self, namespace: str | None = None) -> int:
        pattern = self._namespace_pattern(namespace)
        deleted = 0
        batch: list[str] = []
        try:
            for key in self._client.scan_iter(match=pattern, count=500):
                batch.append(key)
                if len(batch) >= 500:
                    deleted += int(self._client.delete(*batch))
                    batch.clear()
            if batch:
                deleted += int(self._client.delete(*batch))
            return deleted
        except RedisError as exc:
            raise CacheStoreError("Redis cache clear failed.") from exc


    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError as exc:
            raise CacheStoreError("Redis cache health check failed.") from exc

    def close(self) -> None:
        self._client.close()


    def _physical_key(self, namespace: str, logical_key: str) -> str:
        normalized_namespace = namespace.strip().casefold()
        if not normalized_namespace:
            raise ValueError("Cache namespace cannot be empty.")
        digest = hashlib.sha256(logical_key.encode("utf-8")).hexdigest()
        return f"{self._key_prefix}:{self._version}:{normalized_namespace}:{digest}"


    def _namespace_pattern(self, namespace: str | None) -> str:
        if namespace is None:
            return f"{self._key_prefix}:{self._version}:*"
        normalized_namespace = namespace.strip().casefold()
        if not normalized_namespace:
            raise ValueError("Cache namespace cannot be empty.")
        return f"{self._key_prefix}:{self._version}:{normalized_namespace}:*"