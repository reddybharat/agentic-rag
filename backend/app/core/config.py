from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    ollama_base_url: str = "http://localhost:11434"
    log_level: str = "INFO"
    log_json: bool = True
    default_owner_id: str = "local"
    readiness_timeout_s: float = 2.0
    models_config_path: Path = BACKEND_DIR / "config" / "models.yaml"
    llm_timeout_s: float = 120.0
    embedding_model: str = "qwen3-embedding:0.6b"
    embedding_dim: int = 1024
