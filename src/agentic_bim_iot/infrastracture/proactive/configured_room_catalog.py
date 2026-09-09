class ConfiguredRoomCatalog:
    """Room catalog backed by the configured proactive monitoring scope."""

    def __init__(self,rooms: tuple[str, ...]) -> None:
        normalized_rooms: list[str] = []
        seen: set[str] = set()
        for room in rooms:
            normalized = " ".join(room.strip().split())
            key = normalized.casefold()
            if not normalized or key in seen:
                continue
            seen.add(key)
            normalized_rooms.append(normalized)
        self._rooms = tuple(normalized_rooms)

    def list_rooms(self) -> tuple[str, ...]:
        return self._rooms