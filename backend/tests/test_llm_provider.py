"""Tests for the LLM Provider implementations and factory.
"""

import pytest
from app.config.settings import Settings
from app.core.exceptions import ConfigurationError
from app.services.llm_provider import LLMProviderFactory, GroqProvider


def test_groq_provider_creation_without_key(monkeypatch):
    """Ensure GroqProvider raises ConfigurationError if GROQ_API_KEY is missing."""
    # Temporarily unset GROQ_API_KEY from settings
    monkeypatch.setattr("app.services.llm_provider.get_settings", lambda: Settings(groq_api_key=None))
    
    with pytest.raises(ConfigurationError) as exc_info:
        GroqProvider()
    assert "GROQ_API_KEY is required" in str(exc_info.value)


def test_groq_provider_creation_with_key(monkeypatch):
    """Ensure GroqProvider is created successfully when API key is provided."""
    mock_settings = Settings(groq_api_key="mock-key-1234", llm_provider="groq", llm_model="llama-3.3-70b-versatile")
    monkeypatch.setattr("app.services.llm_provider.get_settings", lambda: mock_settings)
    
    provider = GroqProvider()
    assert provider.provider_name == "groq"
    assert provider._model == "llama-3.3-70b-versatile"
    
    client = provider._get_client()
    assert client is not None
    assert client.api_key == "mock-key-1234"
    assert str(client.base_url) == "https://api.groq.com/openai/v1/"


def test_factory_creates_groq_provider(monkeypatch):
    """Ensure the LLMProviderFactory creates a GroqProvider instance."""
    mock_settings = Settings(groq_api_key="mock-key-1234", llm_provider="groq")
    monkeypatch.setattr("app.services.llm_provider.get_settings", lambda: mock_settings)
    
    provider = LLMProviderFactory.create()
    assert isinstance(provider, GroqProvider)
    assert provider.provider_name == "groq"
