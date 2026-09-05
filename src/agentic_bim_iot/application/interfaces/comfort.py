from typing import Protocol
from agentic_bim_iot.domain.comfort import ComfortAssessment


class ComfortEngineError(RuntimeError):
    pass


class ComfortEngine(Protocol):
    """The contract for the Comfort engine"""
    def assess(self, room_reference: str) -> ComfortAssessment:
        ...