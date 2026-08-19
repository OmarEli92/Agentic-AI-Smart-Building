from functools import lru_cache
from enum import StrEnum
from typing import Self
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    
    llm_model: str = Field(
        validation_alias="LLM_MODEL"
    )
    
    llm_api_key: SecretStr = Field(
        validation_alias="LLM_API_KEY",
    )
    
    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        validation_alias="LLM_TEMPERATURE"
    )
    
    llm_max_tokens: int = Field(
        default=512,
        gt=0,
        validation_alias="LLM_MAX_TOKENS"
    )
    
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        validation_alias="LLM_MAX_RETRIES"
    )
    
    llm_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        validation_alias="LLM_TIMEOUT_SECONDS",
    )
    #The Bim sources
    semantic_backend: SemanticBackend = Field(
        default=SemanticBackend.GRAPHDB,
        validation_alias="SEMANTIC_BACKEND",
    )

    # GraphDB
    graphdb_url: str = Field(
        default="http://localhost:7200/",
        validation_alias="GRAPHDB_URL",
    )

    graphdb_repository: str = Field(
        default="smartHome",
        validation_alias="GRAPHDB_REPOSITORY",
    )
    
    graphdb_username: str | None = Field(
        default=None,
        validation_alias="GRAPHDB_USERNAME",
    )

    graphdb_password: SecretStr | None = Field(
        default=None,
        validation_alias="GRAPHDB_PASSWORD",
    )
    # Neo4j
    neo4j_uri: str = Field(
        default="neo4j://localhost:7687",
        validation_alias="NEO4J_URI",
    )

    neo4j_username: str | None = Field(
        default=None,
        validation_alias="NEO4J_USERNAME",
    )

    neo4j_password: SecretStr | None = Field(
        default=None,
        validation_alias="NEO4J_PASSWORD",
    )

    neo4j_database: str = Field(
        default="neo4j",
        validation_alias="NEO4J_DATABASE",
    )

    graphdb_max_repair_retries: int = Field(
        default=2,
        ge=0,
        validation_alias="GRAPHDB_MAX_REPAIR_RETRIES",
    )

    graphdb_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias="GRAPHDB_TIMEOUT_SECONDS",
    )
    
    neo4j_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias="NEO4J_TIMEOUT_SECONDS",
    )
    graphdb_ontology_path: str = Field(
        default="src/resources/ontology/openSmartHome_Donkers_v2.ttl",
        validation_alias="GRAPHDB_ONTOLOGY_PATH",
    )
    
    semantic_max_execution_repair_retries: int = Field(
        default=2,
        ge=0,
        validation_alias=("SEMANTIC_MAX_EXECUTION_REPAIR_RETRIES")
    )
    
    #Thingsboard
    thingsboard_url: str = Field(
    default="http://localhost:8080",
    validation_alias="THINGSBOARD_URL",
    )

    thingsboard_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="THINGSBOARD_API_KEY",
    )

    thingsboard_username: str | None = Field(
        default=None,
        validation_alias="THINGSBOARD_USERNAME",
    )

    thingsboard_password: SecretStr | None = Field(
        default=None,
        validation_alias="THINGSBOARD_PASSWORD",
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
            
    
@lru_cache
def get_settings() -> Settings:
    return Settings()


