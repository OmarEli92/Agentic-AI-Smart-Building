from dataclasses import dataclass

from agentic_bim_iot.domain.models import SupervisorDecision


@dataclass(frozen=True)
class FakeSupervisor:
    """Deterministic Supervisor implementation used only in tests."""

    decision: SupervisorDecision

    def decide(
        self,
        user_query: str,
    ) -> SupervisorDecision:
        return self.decision