from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    codestral_deployment: str = "codestral"
    gpt4o_mini_deployment: str = "gpt-4o-mini"

    # Database
    db_path: str = "aiops.db"

    # Polling
    monitor_poll_interval: int = 15
    orchestrator_poll_interval: int = 10

    # Retries
    max_incident_retries: int = 3
    max_tool_iterations: int = 10

    # Server
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000

    model_config = {"env_file": ".env", "env_prefix": "AIOPS_"}


settings = Settings()
