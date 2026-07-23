"""Central configuration for OhOhOps.

A single typed Settings object loads and validates every environment variable at
startup. Anthropic, Gemini, and OpenRouter can drive chat inference. Gemini,
OpenAI, or a local model can provide embeddings. Keys that later phases depend
on are validated only when the feature that needs them is actually used.

Every service in the project reads its configuration through `get_settings()`,
which returns one cached instance for the whole process.
"""

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Required: inference + vector DB (Phase 1) ─────────────────────────
    openrouter_api_key: str | None = Field(
        default=None, description="OpenRouter API key for chat inference."
    )
    pinecone_api_key: str | None = Field(
        default=None, description="Pinecone serverless API key."
    )

    # ── Deployment Mode Foundation (Phase 0) ──────────────────────────────
    deployment_mode: str = "cloud"
    chroma_host: str | None = None
    chroma_port: int = 8000
    chroma_collection_prefix: str = "ohohops_3072_"

    @property
    def is_cloud(self) -> bool:
        return self.deployment_mode == "cloud"

    @property
    def is_local(self) -> bool:
        return self.deployment_mode == "local"

    # ── Optional until their phase comes online ───────────────────────────
    gemini_api_key: str | None = Field(
        default=None, description="Google AI Studio API key for Gemini embeddings."
    )
    gemini_api_key_chat: str | None = Field(
        default=None, description="Optional separate key for the main repair graph."
    )
    gemini_api_key_security: str | None = Field(
        default=None, description="Optional separate key for the security arbiter."
    )
    anthropic_api_key: str | None = Field(
        default=None, description="Anthropic API key for Claude inference."
    )
    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key for high-speed embeddings."
    )
    github_token: str | None = Field(
        default=None, description="Optional token for private GitHub ingestion."
    )
    supabase_db_url: str | None = Field(
        default=None, description="Postgres connection URL for the ledger (Phase 0.4)."
    )

    # ── Model selection ───────────────────────────────────────────────────
    openrouter_chat_model: str = "mistralai/mistral-7b-instruct:free"
    openrouter_security_model: str = "google/gemini-2.5-flash-lite"
    openrouter_referer: str | None = None
    openrouter_title: str = "OhOhOps SRE"
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_security_model: str = "gemini-2.5-flash"
    anthropic_chat_model: str = "claude-3-5-sonnet-20241022"
    gemini_embedding_model: str = "models/gemini-embedding-001"
    openai_embedding_model: str = "text-embedding-3-large"
    use_local_embeddings: bool = False
    embedding_dimension: int = 3072

    # ── Pinecone index (auto-created on startup if absent) ────────────────
    @property
    def pinecone_index(self) -> str:
        return "ohohops-3072"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_metric: str = "cosine"

    # ── Ingestion / RAG tuning ────────────────────────────────────────────
    chunk_size: int = 1200
    chunk_overlap: int = 150
    retrieval_top_k: int = 5

    # ── Sandbox (Phase 2) ─────────────────────────────────────────────────
    # "subprocess" = runs patches locally (fast, reliable on Windows dev)
    # "docker"     = runs patches in an isolated Docker container (production)
    sandbox_mode: str = "subprocess"
    sandbox_image: str = "python:3.12-slim"
    sandbox_mem_limit: str = "256m"
    sandbox_nano_cpus: int = 500_000_000  # 0.5 CPU cores
    sandbox_network_mode: str = "none"
    sandbox_timeout_seconds: int = 60

    # ── Cost / latency guardrails (Operational Validation Checklist) ──────
    max_retries: int = 3

    # ── Anomaly detection (Phase 3) ───────────────────────────────────────
    anomaly_contamination: float = 0.05
    anomaly_window_size: int = 100
    # Off by default: when enabled, the background loop samples metrics and can
    # autonomously fire real graph runs (LLM + Docker). Opt in deliberately.
    enable_telemetry_loop: bool = False

    # ── Post-Heal Restart (Phase 1.2) ─────────────────────────────────────
    enable_post_heal_restart: bool = True
    max_restart_attempts: int = 3
    restart_health_check_delay: float = 5.0
    restart_graceful_timeout: float = 10.0
    cloud_restart_strategy: str = "process"

    # ── Server ────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        # Cloud deployment (Vercel)
        "https://ohohops.vercel.app",
        "https://ohohops-frontend.vercel.app",
        "https://ohohops.vercel.app",
    ]
    
    # ── Mock/Demo Mode (allows testing without API keys / quotas) ────────
    use_mock_llm: bool = False

    # ── Security & Auth (Phase 5.5) ───────────────────────────────────────
    ohohops_api_key: str = "ohohops-dev-key"
    ohohops_webhook_secret: str = "ohohops-dev-secret"

    @field_validator(
        "openrouter_api_key",
        "gemini_api_key",
        "gemini_api_key_chat",
        "gemini_api_key_security",
        "anthropic_api_key",
        "openai_api_key",
        "github_token",
        mode="before",
    )
    @classmethod
    def _normalize_optional_keys(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("deployment_mode", mode="before")
    @classmethod
    def _normalize_mode(cls, value: str) -> str:
        v = value.strip().lower()
        if v not in ("cloud", "local"):
            raise ValueError("deployment_mode must be 'cloud' or 'local'")
        return v

    @field_validator("pinecone_api_key")
    @classmethod
    def _reject_blank(cls, value: str | None, info) -> str | None:
        if value is not None and not value.strip():
            raise ValueError(f"{info.field_name} must not be empty if provided")
        return value.strip() if value else None

    @model_validator(mode="after")
    def _validate_deployment_mode_requirements(self) -> "Settings":
        if self.deployment_mode == "cloud":
            if not self.pinecone_api_key:
                raise ValueError("pinecone_api_key is required when deployment_mode is 'cloud'")
        elif self.deployment_mode == "local":
            if not self.chroma_host:
                raise ValueError("chroma_host is required when deployment_mode is 'local'")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance.

    Cached so the .env file is parsed once and every importer shares the same
    object. Tests can clear the cache via `get_settings.cache_clear()`.
    """
    return Settings()
