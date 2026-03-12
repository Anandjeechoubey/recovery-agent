from __future__ import annotations

from openai import AsyncAzureOpenAI
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2025-04-01-preview"

    # Deployment names — these map to your Azure-hosted model deployments
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_deployment_mini: str = "gpt-4o-mini"

    vapi_api_key: str = ""
    vapi_phone_number_id: str = ""
    vapi_webhook_url: str = ""
    voice_mode: str = "simulated"  # "simulated" or "live"

    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "collections"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://recovery:recovery@localhost:5433/recovery_agents"

    # Token budgets
    max_total_tokens: int = 2000
    max_handoff_tokens: int = 500

    # Learning loop
    learning_budget_usd: float = 20.0
    conversations_per_eval: int = 20
    conversations_per_persona: int = 3  # repeats per persona (total = this × len(PERSONAS))
    max_learning_iterations: int = 8
    stat_significance_p: float = 0.10  # relaxed for small samples; meta-evaluator can tighten
    min_effect_size: float = 0.1  # 0.1 on 1-5 scale is meaningful with 0.5-increment scoring

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()


def get_openai_client() -> AsyncAzureOpenAI:
    """Create an Azure OpenAI async client."""
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )
