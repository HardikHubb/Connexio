"""
Central settings object. Every other module reads config from here rather
than calling os.environ directly, so we have one place to see (and change)
everything the app depends on.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "testpassword123"
    neo4j_database: str = "neo4j"

    # CORS — comma-separated origins allowed to call this API
    cors_origins: str = "http://localhost:5173"

    # Reserved for later stages (NER / GraphRAG) — unused in Stage 0
    llm_api_key: str = ""

    # Where raw uploads and parsed intermediate JSON live (Stage 3+).
    # A plain folder, not a database — this is deliberately simple; if we
    # ever need multi-instance deployment this becomes object storage, but
    # for the hackathon prototype the filesystem is the right amount of
    # infrastructure.
    storage_dir: str = "storage"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
