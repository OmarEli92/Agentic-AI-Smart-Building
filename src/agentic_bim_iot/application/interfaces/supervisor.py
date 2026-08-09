from typing import Protocol
from agentic_bim_iot.domain.models import SupervisorDecision


class SuperVisor(Protocol):
    """The SuperVisor class represents the contract for components
    that are capable of interpreting the Facility Manager requests and producing
    a routing decision as we defined the Supervisor Decision it's made of Intentions and Routes
    check the SuperVisorDecision class for more details"""
    
    def decide(self, user_query: str) -> SupervisorDecision:
        """Interpret the Facility manager request and produce a structured decision"""