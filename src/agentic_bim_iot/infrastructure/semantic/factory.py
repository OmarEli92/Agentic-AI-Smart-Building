from contextlib import ExitStack
from dataclasses import dataclass
from typing import assert_never

from langchain_core.language_models.chat_models import BaseChatModel
from neo4j import GraphDatabase
from pydantic import SecretStr
from rdflib.contrib.graphdb.client import GraphDBClient

from agentic_bim_iot.application.interfaces.actuator import ActuatorResolver
from agentic_bim_iot.application.interfaces.semantic import BIMQueryService
from agentic_bim_iot.application.interfaces.sensor import SensorResolver
from agentic_bim_iot.config.settings import SemanticBackend, Settings
from agentic_bim_iot.infrastructure.semantic.actuator.factory import create_graphdb_actuator_resolver
from agentic_bim_iot.infrastructure.semantic.graphdb.adapter import GraphDBBIMQueryAdapter
from agentic_bim_iot.infrastructure.semantic.graphdb.repository import GraphDBRepository
from agentic_bim_iot.infrastructure.semantic.graphdb.sensor_resolver import GraphDBSensorResolver
from agentic_bim_iot.infrastructure.semantic.neo4j.adapter import Neo4jBIMQueryAdapter
from agentic_bim_iot.infrastructure.semantic.neo4j.sensor_resolver import Neo4jSensorResolver


@dataclass(frozen=True, slots=True)
class SemanticServices:
    bim_query_service: BIMQueryService
    sensor_resolver: SensorResolver
    actuator_resolver: ActuatorResolver | None


def create_semantic_services(settings: Settings, chat_model: BaseChatModel, resources: ExitStack) -> SemanticServices:
    """Create the configured BIM semantic backend. GraphDB and Neo4j are provided."""
    match settings.semantic_backend:
        case SemanticBackend.GRAPHDB:
            return _create_graphdb_service(
                settings=settings,
                chat_model=chat_model,
                resources=resources,
            )
        case SemanticBackend.NEO4J:
            return _create_neo4j_service(
                settings=settings,
                chat_model=chat_model,
                resources=resources,
            )
        case unsupported_backend:
            assert_never(unsupported_backend)


def _create_graphdb_service(*, settings: Settings, chat_model: BaseChatModel, resources: ExitStack) -> SemanticServices:
    credentials = _get_credentials(
        username=settings.graphdb_username,
        password=settings.graphdb_password,
    )

    if credentials is None:
        client = resources.enter_context(
            GraphDBClient(settings.graphdb_url, timeout=settings.graphdb_timeout_seconds)
        )
    else:
        client = resources.enter_context(
            GraphDBClient(settings.graphdb_url, auth=credentials, timeout=settings.graphdb_timeout_seconds)
        )

    repository = GraphDBRepository(
        client=client,
        repository_id=settings.graphdb_repository,
    )

    bim_query_service = GraphDBBIMQueryAdapter(
        chat_model=chat_model,
        graph_store=repository,
        max_repair_retries=settings.graphdb_max_repair_retries,
    )
    sensor_resolver = GraphDBSensorResolver(
        chat_model=chat_model,
        graph_store=repository,
        max_repair_retries=settings.graphdb_max_repair_retries,
    )
    actuator_resolver = create_graphdb_actuator_resolver(
        strategy=settings.actuator_resolution_strategy,
        graph_store=repository,
        chat_model=chat_model,
    )

    return SemanticServices(
        bim_query_service=bim_query_service,
        sensor_resolver=sensor_resolver,
        actuator_resolver=actuator_resolver,
    )


def _create_neo4j_service(*, settings: Settings, chat_model: BaseChatModel, resources: ExitStack) -> SemanticServices:
    credentials = _get_credentials(
        username=settings.neo4j_username,
        password=settings.neo4j_password,
    )

    if credentials is None:
        driver = resources.enter_context(GraphDatabase.driver(settings.neo4j_uri))
    else:
        driver = resources.enter_context(GraphDatabase.driver(settings.neo4j_uri, auth=credentials))

    driver.verify_connectivity()

    bim_query_service = Neo4jBIMQueryAdapter(
        chat_model=chat_model,
        driver=driver,
        database=settings.neo4j_database,
    )
    sensor_resolver = Neo4jSensorResolver(
        chat_model=chat_model,
        driver=driver,
        database=settings.neo4j_database,
        max_repair_retries=settings.semantic_max_execution_repair_retries,
    )

    return SemanticServices(
        bim_query_service=bim_query_service,
        sensor_resolver=sensor_resolver,
        actuator_resolver=None,
    )


def _get_credentials(*, username: str | None, password: SecretStr | None) -> tuple[str, str] | None:
    if username is None or password is None:
        return None

    normalized_username = username.strip()
    normalized_password = password.get_secret_value().strip()

    if not normalized_username or not normalized_password:
        return None

    return (normalized_username, normalized_password)