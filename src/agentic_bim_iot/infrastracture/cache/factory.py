from agentic_bim_iot.application.interfaces.cache import CacheStore
from agentic_bim_iot.config.settings import BIMCacheBackend, Settings
from agentic_bim_iot.infrastracture.cache.redis_store import RedisCacheStore


def create_bim_cache_store(settings: Settings) -> CacheStore | None:
    if settings.bim_cache_backend == BIMCacheBackend.NONE:
        return None
    if settings.bim_cache_backend == BIMCacheBackend.REDIS:
        cache = RedisCacheStore(redis_url=settings.bim_cache_redis_url.get_secret_value(), key_prefix=settings.bim_cache_key_prefix, version=settings.bim_cache_version, default_ttl_seconds=settings.bim_cache_ttl_seconds)
        cache.ping()
        return cache
    raise ValueError(f"Unsupported BIM cache backend: {settings.bim_cache_backend}")