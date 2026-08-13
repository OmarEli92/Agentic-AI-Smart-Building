from typing import Protocol
from agentic_bim_iot.domain.semantic import SemanticQueryResult

class BIMQueryServiceError(RuntimeError):
    """Expected Failure raised by the semantica subsystem"""
    
class BIMQueryService(Protocol):
    """Application contract for semantic BIM information retrieval"""
    
    def answer(self, natural_language_query: str) -> SemanticQueryResult:
        """This method is responsibile for answering a BIM/Ontology question using
        tge semantic subsystem"""