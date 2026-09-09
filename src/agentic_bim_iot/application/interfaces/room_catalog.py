from typing import Protocol


class RoomCatalog(Protocol):
    """Contract for retrieving the rooms monitored by the proactive system."""

    def list_rooms(self) -> tuple[str, ...]:
        ...