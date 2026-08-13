from pathlib import Path
from neo4j import GraphDatabase
from rdflib import Graph, Namespace
from rdflib_neo4j import HANDLE_VOCAB_URI_STRATEGY,Neo4jStore,Neo4jStoreConfig
from agentic_bim_iot.config.settings import get_settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_PATH = (PROJECT_ROOT/ "resources"/ "ontology"/ "openSmartHome_Donkers_v2.ttl")
PREFIXES = {
    "neo4ind": Namespace("http://neo4j.org/ind#"),
    "neo4voc": Namespace("http://neo4j.org/vocab/sw#"),
    "nsmntx": Namespace("http://neo4j.org/vocab/NSMNTX#"),
    "apoc": Namespace("http://neo4j.org/vocab/APOC#"),
    "graphql": Namespace("http://neo4j.org/vocab/GraphQL#")
}


def load_ontology() -> None:
    settings = get_settings()
    if not ONTOLOGY_PATH.is_file():
        raise FileNotFoundError(f"Ontology file not found: {ONTOLOGY_PATH}")
    if (settings.neo4j_username is None or settings.neo4j_password is None):
        raise RuntimeError("Neo4j credentials are required for ontology import.")

    username = settings.neo4j_username.strip()
    password = (settings.neo4j_password.get_secret_value().strip())
    auth_data = {
        "uri": settings.neo4j_uri,
        "database": settings.neo4j_database,
        "user": username,
        "pwd": password,
    }
    _ensure_resource_constraint(uri=settings.neo4j_uri,username=username,password=password,database=settings.neo4j_database)
    config = Neo4jStoreConfig(auth_data=auth_data,custom_prefixes=PREFIXES,handle_vocab_uri_strategy=(HANDLE_VOCAB_URI_STRATEGY.IGNORE),batching=True,)
    print(f"Neo4j database: {settings.neo4j_database}")
    print(f"Ontology path: {ONTOLOGY_PATH}")
    graph = Graph(store=Neo4jStore(config=config))
    try:
        graph.parse(ONTOLOGY_PATH,format="ttl",)
    finally:
        graph.close(commit_pending_transaction=True)
    print("Neo4j ontology import completed.")


def _ensure_resource_constraint(*,uri: str,username: str,password: str,database: str,) -> None:
    with GraphDatabase.driver(uri,auth=(username,password,),) as driver:
        driver.verify_connectivity()
        driver.execute_query(
            """
            CREATE CONSTRAINT n10s_unique_uri
            IF NOT EXISTS
            FOR (resource:Resource)
            REQUIRE resource.uri IS UNIQUE
            """,
            database_=database,
        )


def main() -> None:
    load_ontology()


if __name__ == "__main__":
    main()