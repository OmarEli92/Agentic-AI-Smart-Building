from typing import Protocol
from agentic_bim_iot.domain.semantic import SemanticQueryResult

class SemanticServiceError(RuntimeError):
    """Expected Failure raised by the semantica subsystem"""
    
class SemanticQueryService(Protocol):
    """Application contract for semantic BIM information retrieval"""
    
    def answer_bim_query(self, natural_language_query: str) -> SemanticQueryResult:
        """This method is responsibile for answering a BIM/Ontology question using
        tge semantic subsystem"""