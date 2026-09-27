"""Custom exception hierarchy for Aegis."""

from __future__ import annotations


class AegisError(Exception):
    """Base exception for all Aegis errors."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


class LLMProviderError(AegisError):
    """Raised when an LLM provider call fails."""


class LLMResponseValidationError(AegisError):
    """Raised when LLM output cannot be parsed or validated."""


class EvaluationError(AegisError):
    """Raised when an evaluator encounters an unrecoverable error."""


class RetrievalError(AegisError):
    """Raised when document retrieval fails."""


class DocumentLoadError(AegisError):
    """Raised when a document cannot be loaded or parsed."""


class ConfigurationError(AegisError):
    """Raised when configuration is invalid or missing."""
