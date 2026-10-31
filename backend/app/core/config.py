from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    ollama_base_url: str = "http://localhost:11434"
    log_level: str = "INFO"
    log_json: bool = True
    default_owner_id: str = "local"
    readiness_timeout_s: float = 2.0
