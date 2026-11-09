"""Configuration settings for the Codebase Intelligent Assistant."""

from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Workspace directory (defaults to current working directory)
    workspace_dir: Path = Field(
        default_factory=Path.cwd,
        description="Path to the repository workspace being inspected/modified",
    )

    # Local LLM settings
    llm_provider: Literal["ollama", "openai_compatible"] = Field(
        default="ollama",
        description="Local LLM backend provider",
    )
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama server URL",
    )
    openai_compatible_url: str = Field(
        default="http://127.0.0.1:8000/v1",
        description="OpenAI-compatible server endpoint for vLLM, LM Studio, or llama.cpp",
    )
    llm_model: str = Field(
        default="qwen2.5-coder:7b",
        description="Model name to invoke",
    )
    llm_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Sampling temperature",
    )
    llm_max_tokens: int = Field(
        default=4096,
        gt=0,
        description="Maximum output tokens per LLM completion",
    )
    llm_context_window: int = Field(
        default=16384,
        gt=1024,
        description="Effective context window budget",
    )

    # Embeddings settings
    embedding_provider: Literal["fastembed", "ollama"] = Field(
        default="fastembed",
        description="Embedding model provider",
    )
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Embedding model name",
    )

    # Server & UI settings
    server_host: str = Field(
        default="127.0.0.1",
        description="FastAPI server host",
    )
    server_port: int = Field(
        default=8000,
        description="FastAPI server port",
    )
    popup_always_on_top: bool = Field(
        default=True,
        description="Whether the floating pop-up remains pinned on top",
    )
    popup_width: int = Field(
        default=500,
        description="Pop-up window width in pixels",
    )
    popup_height: int = Field(
        default=750,
        description="Pop-up window height in pixels",
    )

    # Storage & safety settings
    storage_dir_name: str = Field(
        default=".codebase_agent",
        description="Directory name for index caches, vector stores, and metadata",
    )
    require_diff_confirmation: bool = Field(
        default=True,
        description="Require explicit user confirmation before applying file patches",
    )
    auto_git_branch: bool = Field(
        default=False,
        description="Automatically create a new git branch for agent-suggested edits",
    )
    max_agent_iterations: int = Field(
        default=12,
        gt=0,
        description="Maximum ReAct loop iterations before returning",
    )

    @property
    def storage_dir(self) -> Path:
        """Absolute path to the storage cache directory inside workspace."""
        path = self.workspace_dir / self.storage_dir_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_db_dir(self) -> Path:
        """Directory for ChromaDB persistent vector storage."""
        path = self.storage_dir / "chroma"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cache_db_path(self) -> Path:
        """SQLite cache database path for delta indexing and tags."""
        return self.storage_dir / "metadata_cache.db"


# Global singleton instance
settings = Settings()
