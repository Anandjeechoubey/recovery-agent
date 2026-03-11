from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_model_mini: str = "gpt-4o-mini"

    vapi_api_key: str = ""
    vapi_phone_number_id: str = ""
    vapi_webhook_url: str = ""
    voice_mode: str = "simulated"  # "simulated" or "live"

    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "collections"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Token budgets
    max_total_tokens: int = 2000
    max_handoff_tokens: int = 500

    # Learning loop
    learning_budget_usd: float = 20.0
    conversations_per_eval: int = 20
    max_learning_iterations: int = 8
    stat_significance_p: float = 0.05
    min_effect_size: float = 0.2

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
