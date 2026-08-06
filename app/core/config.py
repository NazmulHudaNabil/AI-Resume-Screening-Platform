from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ----- General App Settings -----
    app_name: str = "AI Resume Screening Platform"

    # ----- Database -----
    database_url: str = "postgresql://postgres:password@localhost:5432/postgres"

    # ----- Groq LLM (for structured extraction + explanation) -----
    groq_api_key: str = ""
    groq_fallback_api_key: str = ""

    # ----- Gemini (for embeddings) -----
    gemini_api_key: str = ""

    # ----- Qdrant Vector DB -----
    qdrant_url: str = "http://localhost:6333"           # local fallback
    qdrant_cluster_endpoint: str = ""                   # cloud endpoint
    qdrant_api_key: str = ""

    # ----- Redis / Upstash -----
    redis_url: str = "redis://localhost:6379/0"         # local fallback
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""

    # ----- Auth -----
    jwt_secret: str = "supersecretkey"

    # Load all variables from .env file automatically
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # ignore any extra keys in .env
    )


# Create a single shared instance — import this everywhere
settings = Settings()
