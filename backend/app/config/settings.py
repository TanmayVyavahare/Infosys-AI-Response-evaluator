"""
Centralized configuration for Aegis.

All thresholds, weights, model parameters, and system limits are defined here.
No magic numbers anywhere else in the codebase.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables and .env file."""

    # ── Application ────────────────────────────────────────────────────
    app_name: str = "Aegis"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Paths ──────────────────────────────────────────────────────────
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Optional[Path] = None
    faiss_cache_dir: Optional[Path] = None
    uploads_dir: Optional[Path] = None

    # ── Embedding Model ────────────────────────────────────────────────
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # ── Chunking ───────────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_length: int = 20

    # ── Retrieval ──────────────────────────────────────────────────────
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.3

    # ── LLM Provider ──────────────────────────────────────────────────
    llm_provider: str = "gemini"  # "openai" | "ollama" | "gemini"
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2048
    llm_timeout: int = 30

    # Provider-specific keys
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"

    # ── Evaluation Weights ─────────────────────────────────────────────
    weight_relevance: float = 0.25
    weight_accuracy: float = 0.30
    weight_groundedness: float = 0.25
    weight_completeness: float = 0.20

    # ── Evaluation Thresholds ──────────────────────────────────────────
    similarity_threshold_high: float = 0.8
    similarity_threshold_medium: float = 0.5
    similarity_threshold_low: float = 0.3

    # Penalty thresholds
    critical_hallucination_threshold: float = 0.3
    factually_unreliable_threshold: float = 0.3
    off_topic_threshold: float = 0.2

    # Score reduction for critical issues
    critical_penalty_factor: float = 0.5

    # ── Verdict Labels ─────────────────────────────────────────────────
    verdict_excellent: float = 0.85
    verdict_good: float = 0.70
    verdict_acceptable: float = 0.55
    verdict_poor: float = 0.40
    # Below verdict_poor → "Unacceptable"

    # ── NER ────────────────────────────────────────────────────────────
    entity_overlap_weight: float = 0.3
    semantic_weight: float = 0.7

    # ── JSON Validation ────────────────────────────────────────────────
    max_json_retries: int = 1

    # ── API ────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    def model_post_init(self, __context) -> None:
        """Set derived paths after initialization."""
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"
        if self.faiss_cache_dir is None:
            self.faiss_cache_dir = self.data_dir / "faiss_cache"
        if self.uploads_dir is None:
            self.uploads_dir = self.data_dir / "uploads"

        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.faiss_cache_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
