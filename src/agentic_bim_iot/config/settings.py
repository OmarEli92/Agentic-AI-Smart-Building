from functools import lru_cache
from enum import StrEnum
from typing import Self
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict



class AgentOrchestration(StrEnum):
    """ There are two different roads to choose a full workflow configuration
    where the strategy is to used the LLM when is needed or use a ReAct configuration in which the
    LLM reason and pick the tool that it needs 
    """

    WORKFLOW = "workflow"
    FULL_REACT = "full_react"
class LLMProvider(StrEnum):
    """The LLM provider supported by the application.
    The provider is only a configuration detail since i will be using
    different free providers like groq or openrouter when i finish the free tokens and usage
    """
    GROQ = "groq"
    OPENROUTER = "openrouter"
    OPENAI = "openai"

class SemanticBackend(StrEnum):
    """The type of data sources that can be used for the bim, for now i mantained the original
    configuration that leverage graphdb and neo4j"""
    GRAPHDB = "graphdb"
    NEO4J = "neo4j"

class ActuatorResolutionStrategy(StrEnum):
    """This class represents the possible strategy that can be used to retrieve the actuators in the building"""
    LLM = "llm"
    ONTOLOGY_PROFILE = "ontology_profile"


class ObservabilityBackend(StrEnum):
    """This class represent the observability layer for now it could be none or with the usage of Langfuse framework"""
    NONE = "none"
    LANGFUSE = "langfuse"


class EvaluationFramework(StrEnum):
    """This class represents the Evaluation layer that can be selected for the system's evaluation"""
    NONE = "none"
    LANGFUSE = "langfuse"
    DEEPEVAL = "deepeval"
    RAGAS = "ragas"
    
     
class BIMCacheBackend(StrEnum):
    """The cache in the system"""
    NONE = "none"
    REDIS = "redis"
    
    
class ThingsBoardIntegration(StrEnum):
    """The ThingsBoard integration selected by the application."""
    REST = "rest"
    MCP = "mcp"    
   

class ThingsBoardActuationBackend(StrEnum):
    TELEMETRY = "telemetry"
    RPC = "rpc"
    

class Settings(BaseSettings):
    """This class represents the basic settings configuration for the application
    it can be loaded from the .env file locally or inside Docker"""   
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    ) 
    
    app_env: str = Field(
        default="development",
        validation_alias="APP_ENV"
    )
#LLM
    llm_provider: LLMProvider = Field(
        default= LLMProvider.GROQ,
        validation_alias="LLM_PROVIDER"
    )
    
    llm_model: str = Field(validation_alias="LLM_MODEL")
    llm_api_key: SecretStr = Field(validation_alias="LLM_API_KEY")
    
    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        validation_alias="LLM_TEMPERATURE"
    )
    
    llm_max_tokens: int = Field(
        default=2048,
        validation_alias="LLM_MAX_TOKENS"
    )
    
    llm_max_retries: int = Field(
        default=2,
        validation_alias="LLM_MAX_RETRIES"
    )
    
    llm_timeout_seconds: float = Field(
        default=60.0,
        validation_alias="LLM_TIMEOUT_SECONDS"
    )
    
#Agent orchestration    
    agent_orchestration: AgentOrchestration = Field(
        default=AgentOrchestration.WORKFLOW,
        validation_alias="AGENT_ORCHESTRATION",
    )

    full_react_recursion_limit: int = Field(
        default=30,
        ge=5,
        validation_alias="FULL_REACT_RECURSION_LIMIT",
    )
    
    full_react_model_call_limit: int = Field(
        default=6,
        ge=2,
        validation_alias="FULL_REACT_MODEL_CALL_LIMIT",
    )

    full_react_tool_call_limit: int = Field(
        default=8,
        ge=1,
        validation_alias="FULL_REACT_TOOL_CALL_LIMIT",
    )
    
#The Bim sources
    semantic_backend: SemanticBackend = Field(
        default=SemanticBackend.GRAPHDB,
        validation_alias="SEMANTIC_BACKEND"
    )

    actuator_resolution_strategy: ActuatorResolutionStrategy = Field(
        default=ActuatorResolutionStrategy.LLM,
        validation_alias="ACTUATOR_RESOLUTION_STRATEGY"
    )

 
# GraphDB
    graphdb_url: str = Field(
        default="http://localhost:7200/",
        validation_alias="GRAPHDB_URL"
    )

    graphdb_repository: str = Field(
        default="smartHome",
        validation_alias="GRAPHDB_REPOSITORY"
    )
    
    graphdb_username: str | None = Field(validation_alias="GRAPHDB_USERNAME")
    graphdb_password: SecretStr | None = Field(validation_alias="GRAPHDB_PASSWORD")
    
    graphdb_max_repair_retries: int = Field(
        default=2,
        validation_alias="GRAPHDB_MAX_REPAIR_RETRIES"
    )

    graphdb_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="GRAPHDB_TIMEOUT_SECONDS"
    )
    
    graphdb_ontology_path: str = Field(
        default="resources/ontology/openSmartHome_Donkers_v2.ttl",
        validation_alias="GRAPHDB_ONTOLOGY_PATH"
    )
# Neo4j
    neo4j_uri: str = Field(
        default="neo4j://localhost:7687",
        validation_alias="NEO4J_URI"
    )

    neo4j_username: str | None = Field(validation_alias="NEO4J_USERNAME")
    neo4j_password: SecretStr | None = Field(validation_alias="NEO4J_PASSWORD")

    neo4j_database: str = Field(
        default="neo4j",
        validation_alias="NEO4J_DATABASE"
    )
    
    neo4j_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="NEO4J_TIMEOUT_SECONDS"
    )
    
    
    semantic_max_execution_repair_retries: int = Field(
        default=2,
        validation_alias=("SEMANTIC_MAX_EXECUTION_REPAIR_RETRIES")
    )
    
#Proposal  and execution  
    proposal_database_path: str = Field(
        default="data/proposals.db",
        validation_alias="PROPOSAL_DATABASE_PATH"
    )

    proposal_ttl_seconds: int = Field(
        default=900,
        ge=60,
        validation_alias="PROPOSAL_TTL_SECONDS"
    )
    
    execution_database_path: str = Field(
        default="data/executions.db",
        validation_alias="EXECUTION_DATABASE_PATH"
    )
    
#Thingsboard
    thingsboard_url: str = Field(
        default="http://localhost:8080",
        validation_alias="THINGSBOARD_URL"
    )

    thingsboard_api_key: SecretStr | None = Field(validation_alias="THINGSBOARD_API_KEY")
    thingsboard_username: str | None = Field(validation_alias="THINGSBOARD_USERNAME")
    thingsboard_password: SecretStr | None = Field(validation_alias="THINGSBOARD_PASSWORD")    

    thingsboard_integration: ThingsBoardIntegration = Field(
        default=ThingsBoardIntegration.REST,
        validation_alias="THINGSBOARD_INTEGRATION"
    )

    thingsboard_mcp_sse_url: str = Field(
        default="http://localhost:8000/sse",
        validation_alias="THINGSBOARD_MCP_SSE_URL"
    )

    thingsboard_mcp_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="THINGSBOARD_MCP_TIMEOUT_SECONDS"
    )
    
    thingsboard_actuation_backend: ThingsBoardActuationBackend = Field(
        default=ThingsBoardActuationBackend.TELEMETRY,
        validation_alias="THINGSBOARD_ACTUATION_BACKEND",
    )

    actuator_rpc_profile_path: str = Field(
        default="resources/config/actuator_rpc_profile.yaml",
        validation_alias="ACTUATOR_RPC_PROFILE_PATH",
    )

    thingsboard_rpc_request_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="THINGSBOARD_RPC_REQUEST_TIMEOUT_SECONDS",
    )
        
    
#Observability and logging
    
    observability_backend: ObservabilityBackend = Field(
        default=ObservabilityBackend.NONE,
        validation_alias="OBSERVABILITY_BACKEND"
    )

    evaluation_framework: EvaluationFramework = Field(
        default=EvaluationFramework.NONE,
        validation_alias="EVALUATION_FRAMEWORK"
    )
    
    
    log_file_path: str = Field(
        default="logs/agentic_bim_iot.log",
        validation_alias="LOG_FILE_PATH"
    )

    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL"
    )
    
    
#Cache
    bim_cache_backend: BIMCacheBackend = Field(
        default=BIMCacheBackend.NONE,
        validation_alias="BIM_CACHE_BACKEND",
    )

    bim_cache_redis_url: SecretStr = Field(
        default=SecretStr("redis://localhost:6380/0"),
        validation_alias="BIM_CACHE_REDIS_URL",
    )

    bim_cache_ttl_seconds: int = Field(
        default=604800, # 7 giorni
        ge=60,
        validation_alias="BIM_CACHE_TTL_SECONDS",
    )

    bim_cache_key_prefix: str = Field(
        default="agentic-smart-building",
        validation_alias="BIM_CACHE_KEY_PREFIX",
    )

    bim_cache_version: str = Field(
        default="v1",
        validation_alias="BIM_CACHE_VERSION",
    )

    bim_cache_fail_open: bool = Field(
        default=True,
        validation_alias="BIM_CACHE_FAIL_OPEN",
    )
#proactive agent
    proactive_comfort_enabled: bool = Field(
        default=False,
        validation_alias="PROACTIVE_COMFORT_ENABLED",
    )

    proactive_comfort_interval_seconds: int = Field(
        default=60,
        ge=10,
        validation_alias="PROACTIVE_COMFORT_INTERVAL_SECONDS",
    )

    proactive_comfort_rooms: str = Field(
        default="kitchen",
        validation_alias="PROACTIVE_COMFORT_ROOMS",
    )

    proactive_proposal_cooldown_seconds: int = Field(
        default=900,
        ge=60,
        validation_alias="PROACTIVE_PROPOSAL_COOLDOWN_SECONDS",
    )

    notification_database_path: str = Field(
        default="data/notifications.db",
        validation_alias="NOTIFICATION_DATABASE_PATH",
    )
    
#Streamlit
    streamlit_page_title: str = Field(
        default="Agentic Smart Building",
        validation_alias="STREAMLIT_PAGE_TITLE",
    )

    streamlit_notification_poll_seconds: int = Field(
        default=5,
        ge=1,
        validation_alias="STREAMLIT_NOTIFICATION_POLL_SECONDS",
    )
    
    
    @model_validator(mode="after")
    def validate_llm_configuration(self) -> Self:
        """Verify if the required api key and the llm model are selected correctly"""
        if not self.llm_api_key.get_secret_value().strip():
            raise ValueError("The LLM api it'necessary and cannot be empty!")
        if not self.llm_model.strip():
            raise ValueError("The LLM Model it's necessary and cannot be empty") 
        return self
    
    
    @model_validator(mode="after")
    def validate_database_credentials(self) -> Self:
        self._validate_credential_pair(username=self.graphdb_username,password=self.graphdb_password,service_name="GraphDB")
        self._validate_credential_pair(username=self.neo4j_username,password=self.neo4j_password,service_name="Neo4j")
        return self


    @staticmethod
    def _validate_credential_pair(*,username: str | None,password: SecretStr | None,service_name: str,) -> None:
        normalized_username = (username.strip() if username else None)
        normalized_password = (password.get_secret_value().strip()if password else None)
        if bool(normalized_username) != bool(normalized_password):
            raise ValueError(
                f"{service_name} username and password must either both be provided or both be omitted.")
            
 
    @model_validator(mode="after")
    def validate_thingsboard_integration(self) -> Self:
        """Verify the ThingsBoard integration configuration."""

        if self.thingsboard_integration == ThingsBoardIntegration.MCP and not self.thingsboard_mcp_sse_url.strip():
            raise ValueError("The ThingsBoard MCP SSE URL cannot be empty when MCP integration is enabled.")
        return self
   
@lru_cache
def get_settings() -> Settings:
    return Settings()


