from rdflib.contrib.graphdb.client import GraphDBClient

from agentic_bim_iot.infrastracture.observability.tracing import trace_observation
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
    def __init__(self, client: GraphDBClient, repository_id: str) -> None:
        self._repository = client.repositories.get(repository_id)
        self._repository_id = repository_id
        self._schema_cache: str | None = None

    def get_schema(self) -> str:
        """Retrieve the RDF schema."""
        cache_hit = self._schema_cache is not None
        with trace_observation(
            "graphdb.get_schema",
            as_type="tool",
            input_payload={
                "repository": self._repository_id,
            },
            metadata={"cache_hit": cache_hit,}
        ) as observation:
            if self._schema_cache is not None:
                observation.update(
                    output={
                        "cache_hit": True,
                        "schema_characters": len(self._schema_cache),
                    }
                )
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
            observation.update(
                output={
                    "cache_hit": False,
                    "schema_characters": len(schema),
                }
            )

            return schema

    def execute_select(self, sparql_query: str) -> SPARQLResult:
        """The only method accessible for now is to retrieve data with SELECT."""
        with trace_observation(
            "graphdb.execute_select",
            as_type="tool",
            input_payload={
                "repository": self._repository_id,
                "sparql": sparql_query,
            },
        ) as observation:
            result = self._repository.query(sparql_query)
            if result.type != "SELECT":
                raise ValueError("Expected a SPARQL SELECT result.")
            records = [
                {
                    str(variable): value
                    for variable, value in binding.items()
                }
                for binding in result.bindings
            ]
            observation.update(
                output={"record_count": len(records), "records": [
                        {
                            key: str(value)
                            for key, value in record.items()
                        }
                        for record in records
                    ],
                }
            )
            return records