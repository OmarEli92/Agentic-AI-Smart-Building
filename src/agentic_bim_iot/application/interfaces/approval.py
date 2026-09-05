from typing import Protocol
from agentic_bim_iot.domain.approval import ApprovalResult
from agentic_bim_iot.domain.enums import Intent


class ApprovalHandlerError(RuntimeError):
    pass


class ApprovalHandler(Protocol):
    def handle(self, intent: Intent, user_query: str, room_reference: str | None = None) -> ApprovalResult:
        ...