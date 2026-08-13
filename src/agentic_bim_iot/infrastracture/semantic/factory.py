from contextlib import ExitStack
from typing import assert_never
from langchain_core.language_models.chat_models import BaseChatModel
from neo4j import GraphDatabase
from pydantic import SecretStr
from rdflib.contrib.graphdb.client import GraphDBClient
from agentic_bim_iot.application.interfaces.semantic import BIMQueryService
from agentic_bim_iot.config.settings import SemanticBackend,Settings
from agentic_bim_iot.infrastracture.semantic.graphdb.adapter import GraphDBBIMQueryAdapter
from agentic_bim_iot.infrastracture.semantic.graphdb.repository import GraphDBRepository
from agentic_bim_iot.infrastracture.semantic.neo4j.adapter import Neo4jBIMQueryAdapter


def create_bim_query_service(settings: Settings,chat_model: BaseChatModel,resources: ExitStack) -> BIMQueryService:
    """
    Create the configured BIM semantic backend.. graphDB and neo4j are provided
    """

    match settings.semantic_backend:
        case SemanticBackend.GRAPHDB:
            return _create_graphdb_service(settings=settings,chat_model=chat_model,resources=resources)

        case SemanticBackend.NEO4J:
            return _create_neo4j_service(settings=settings,chat_model=chat_model,resources=resources,)
        
        case unsupported_backend:assert_never(unsupported_backend)


def _create_graphdb_service(*,settings: Settings,chat_model: BaseChatModel,resources: ExitStack) -> BIMQueryService:
    credentials = _get_credentials(username=settings.graphdb_username, password=settings.graphdb_password)
    if credentials is None:
        client = resources.enter_context(GraphDBClient(settings.graphdb_url,timeout=settings.graphdb_timeout_seconds,))
    else:
        client = resources.enter_context(GraphDBClient(settings.graphdb_url,auth=credentials,timeout=settings.graphdb_timeout_seconds,))
    repository = GraphDBRepository(client=client,repository_id=settings.graphdb_repository,)
    return GraphDBBIMQueryAdapter(chat_model=chat_model,graph_store=repository,max_repair_retries=(settings.graphdb_max_repair_retries))


def _create_neo4j_service(*,settings: Settings,chat_model: BaseChatModel,resources: ExitStack) -> BIMQueryService:
    credentials = _get_credentials(username=settings.neo4j_username, password=settings.neo4j_password)
    if credentials is None:
        driver = resources.enter_context(GraphDatabase.driver(settings.neo4j_uri))
    else:
        driver = resources.enter_context(GraphDatabase.driver(settings.neo4j_uri,auth=credentials,))
    driver.verify_connectivity()
    return Neo4jBIMQueryAdapter(chat_model=chat_model,driver=driver,database=settings.neo4j_database,)


def _get_credentials( *,username: str | None, password: SecretStr | None) -> tuple[str, str] | None:
    if username is None or password is None:
        return None
    normalized_username = username.strip()
    normalized_password = password.get_secret_value().strip()
    if not normalized_username or not normalized_password:
        return None
    return (normalized_username,normalized_password)