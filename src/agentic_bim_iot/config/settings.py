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

    

    
    @model_validator(mode="after")
    def validate_llm_configuration(self) -> Self:
        """Verify if the required api key and the llm model are selected correctly"""
        if not self.llm_api_key.get_secret_value().strip():
            raise ValueError("The LLM api it'necessary and cannot be empty!")
        if not self.llm_model.strip():
            raise ValueError("The LLM Model it's necessary and cannot be empty") 
        return self
    
@lru_cache
def get_settings() -> Settings:
    return Settings()