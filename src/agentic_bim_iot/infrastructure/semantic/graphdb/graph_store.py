from typing import Protocol, TypeAlias
from rdflib.term import Identifier

type SPARQLRecord = dict[str, Identifier]
type SPARQLResult = list[SPARQLRecord]


class GraphStoreError(RuntimeError):
    """Runtime error and expected failure when accessing the semantic graph storage"""
    
class SPARQLGraphStore(Protocol):
    """The minimal contract for the semantic adapter
    """
    
    
    def get_schema(self) -> str:
        """Return the schema used for Text to SPARQL"""
        ...
        
    def execute_select(self, sparql_query: str) -> SPARQLResult:
        """Just executee a select query"""
        ...