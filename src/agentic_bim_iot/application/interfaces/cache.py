from typing import Protocol


class CacheStoreError(RuntimeError):
    ...


class CacheStore(Protocol):
    """This is the generic cache contract used by the application infrastructure components."""

    def get(self, namespace: str, key: str) -> str | None:
        ...

    def set(self, namespace: str, key: str, value: str, ttl_seconds: int | None = None) -> None:
        ...

    def delete(self, namespace: str, key: str) -> None:
        ...

    def clear(self, namespace: str | None = None) -> int:
        ...

    def ping(self) -> bool:
        ...

    def close(self) -> None:
        ...