from typing import Protocol
from agentic_bim_iot.domain.proposal import ActionProposal


class ProposalRepositoryError(RuntimeError):
    pass


class ProposalRepository(Protocol):
    """The repository that stores the proposals"""
    def save(self, proposal: ActionProposal):
        ...

    def get(self, proposal_id: str) -> ActionProposal | None:
        ...

    def get_latest(self, room_reference: str) -> ActionProposal | None:
        ...
        
    def get_latest_pending(self, room_reference: str | None = None) -> ActionProposal | None:
        ...

    def list_pending(self, room_reference: str | None = None) -> list[ActionProposal]:
        ...

    def update(self, proposal: ActionProposal):
        ...
        
    def supersede(self, proposal: ActionProposal, replacement: ActionProposal) -> None:
        ...