from dataclasses import dataclass, field
from agentic_bim_iot.application.interfaces.semantic import SemanticServiceError
from agentic_bim_iot.domain.semantic import SemanticQueryResult


@dataclass
class FakeSemanticQueryService:
    result: SemanticQueryResult
    received_queries: list[str] = field(default_factory=list)

    def answer_bim_query(self, natural_language_query: str) -> SemanticQueryResult:
        self.received_queries.append(natural_language_query)
        return self.result
    
    

class FailingSemanticQueryService:
    def answer_bim_query(
        self,
        natural_language_query: str,
    ) -> SemanticQueryResult:
        raise SemanticServiceError(
            "GraphDB is unavailable."
        )