from rdflib.contrib.graphdb.client import GraphDBClient
from rdflib.term import Identifier
from agentic_bim_iot.infrastracture.semantic.graphdb.graph_store import GraphStoreError, SPARQLResult



GRAPHDB_SCHEMA_QUERY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

CONSTRUCT {
    ?class a rdfs:Class .
    ?class ?objectProperty ?relatedClass .
    ?class ?dataProperty "".
}
WHERE {
    {
        SELECT DISTINCT ?class
        WHERE {
            ?instance a ?class .
        }
    }

    {
        SELECT DISTINCT ?class ?objectProperty ?relatedClass
        WHERE {
            ?instance1 a ?class .
            ?instance2 a ?relatedClass .
            ?instance1 ?objectProperty ?instance2 .
        }
    }

    {
        SELECT DISTINCT ?class ?dataProperty
        WHERE {
            ?instance a ?class .
            ?instance ?dataProperty ?dataValue .

            FILTER NOT EXISTS {
                ?dataValue a ?moreClass .
            }
        }
    }
}
""".strip()

class GraphDBRepository:
    """The Graphdb repository."""

    def __init__(self,client: GraphDBClient,repository_id: str,) -> None:
        self._repository = client.repositories.get(repository_id)
        self._schema_cache: str | None = None
    def get_schema(self) -> str:
        """Retrieve the RDF schema """

        if self._schema_cache is not None:
            return self._schema_cache
        try:
            result = self._repository.query(GRAPHDB_SCHEMA_QUERY)
        except Exception as exc:
            raise GraphStoreError("Could not retrieve the GraphDB schema.") from exc

        if result.type != "CONSTRUCT" or result.graph is None:
            raise GraphStoreError("Expected a SPARQL CONSTRUCT result for the schema")

        schema = result.graph.serialize(format="turtle").strip()
        if not schema:
            raise GraphStoreError("GraphDB returned an empty schema")
        self._schema_cache = schema
        return schema
    
    
    def execute_select(self, sparql_query: str,) -> SPARQLResult:
        """The only method accessible fro now is to retrieve data(SELECT)"""
        result = self._repository.query(sparql_query)
        if result.type != "SELECT":
            raise ValueError("Expected a SPARQL SELECT result.")
        return [
            {
                str(variable): value
                for variable, value in binding.items()
            }
            for binding in result.bindings
        ]