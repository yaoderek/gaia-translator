from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    database_url: str

    supabase_url: str
    supabase_service_key: str
    supabase_storage_bucket: str = "gaia-papers"

    # Local temp dirs used during PDF processing
    papers_dir: str = "/tmp/gaia_papers"
    figures_dir: str = "/tmp/gaia_figures"

    model_config = {
        "env_file": str(Path(__file__).resolve().parents[2] / ".env"),
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
