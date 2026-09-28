"""Abstract LLM provider interface with concrete implementations.

Supports OpenAI, Ollama, and Gemini through a single interface.
The factory selects the active provider based on configuration.
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Optional

from app.config.settings import get_settings
from app.core.exceptions import LLMProviderError, ConfigurationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: User prompt text.
            system_message: Optional system message for context.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum tokens in response.

        Returns:
            Generated text response.

        Raises:
            LLMProviderError: If the API call fails.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        ...


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY is required for Gemini provider. "
                "Set it in your .env file."
            )
        self._api_key = settings.gemini_api_key.strip() if settings.gemini_api_key else ""
        self._model = settings.llm_model
        self._client = None

    def _get_client(self):
        """Lazily initialize the Gemini client."""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._client = genai.GenerativeModel(self._model)
        return self._client

    async def generate(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        settings = get_settings()
        temp = temperature if temperature is not None else settings.llm_temperature
        tokens = max_tokens or settings.llm_max_tokens

        try:
            client = self._get_client()

            full_prompt = prompt
            if system_message:
                full_prompt = f"{system_message}\n\n{prompt}"

            generation_config = {
                "temperature": temp,
                "max_output_tokens": tokens,
            }

            # Run synchronous Gemini call in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                ),
            )
            return response.text

        except Exception as exc:
            raise LLMProviderError(
                f"Gemini API call failed: {exc}",
                detail=str(exc),
            ) from exc

    @property
    def provider_name(self) -> str:
        return "gemini"


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required for OpenAI provider."
            )
        self._api_key = settings.openai_api_key.strip() if settings.openai_api_key else ""
        self._model = settings.llm_model
        self._client = None

    def _get_client(self):
        """Lazily initialize the OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        settings = get_settings()
        temp = temperature if temperature is not None else settings.llm_temperature
        tokens = max_tokens or settings.llm_max_tokens

        try:
            client = self._get_client()
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            response = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temp,
                max_tokens=tokens,
            )
            return response.choices[0].message.content

        except Exception as exc:
            raise LLMProviderError(
                f"OpenAI API call failed: {exc}",
                detail=str(exc),
            ) from exc

    @property
    def provider_name(self) -> str:
        return "openai"


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url
        self._model = settings.llm_model

    async def generate(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        import aiohttp

        settings = get_settings()
        temp = temperature if temperature is not None else settings.llm_temperature

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temp},
        }
        if system_message:
            payload["system"] = system_message

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=settings.llm_timeout),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise LLMProviderError(
                            f"Ollama returned HTTP {resp.status}: {body}"
                        )
                    data = await resp.json()
                    return data.get("response", "")

        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(
                f"Ollama API call failed: {exc}",
                detail=str(exc),
            ) from exc

    @property
    def provider_name(self) -> str:
        return "ollama"


class GroqProvider(LLMProvider):
    """Groq LLM provider using OpenAI's compatible client."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.groq_api_key:
            raise ConfigurationError(
                "GROQ_API_KEY is required for Groq provider. "
                "Set it in your .env file."
            )
        self._api_key = settings.groq_api_key.strip() if settings.groq_api_key else ""
        self._model = settings.llm_model
        self._client = None

    def _get_client(self):
        """Lazily initialize the Groq client (via OpenAI compatibility)."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=get_settings().llm_timeout,
                max_retries=0,
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        settings = get_settings()
        temp = temperature if temperature is not None else settings.llm_temperature
        tokens = max_tokens or settings.llm_max_tokens

        try:
            client = self._get_client()
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            # Respect short provider throttles rather than immediately downgrading
            # the review to local heuristics. Retries are bounded by time and count.
            deadline = asyncio.get_running_loop().time() + 120
            for attempt in range(8):
                try:
                    response = await client.chat.completions.create(
                        model=self._model, messages=messages,
                        temperature=temp, max_tokens=tokens,
                    )
                    return response.choices[0].message.content
                except Exception as exc:
                    if getattr(exc, "status_code", None) != 429 or attempt == 7:
                        raise
                    delay = self._retry_delay(exc, attempt)
                    if asyncio.get_running_loop().time() + delay > deadline:
                        raise
                    logger.info("Groq rate limit: retrying after %.1f seconds", delay)
                    await asyncio.sleep(delay)

        except Exception as exc:
            status = getattr(exc, "status_code", None)
            daily_limit = status == 429 and ("tokens per day" in str(exc).lower() or "(tpd)" in str(exc).lower())
            message = (
                "Groq's daily token limit has been reached. Try again when quota is available." if daily_limit else
                "Groq is temporarily rate-limited. Please retry shortly." if status == 429 else
                "Groq review is unavailable. Check the provider configuration or try again."
            )
            raise LLMProviderError(message) from exc

    @staticmethod
    def _retry_delay(exc: Exception, attempt: int) -> float:
        headers = getattr(getattr(exc, "response", None), "headers", {})
        try:
            delay = float(headers.get("retry-after", ""))
        except (ValueError, TypeError):
            match = re.search(r"try again in ([0-9.hms ]+)", str(exc), re.I)
            durations = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*([hms])", match.group(1).lower()) if match else []
            delay = sum(float(value) * {'h':3600, 'm':60, 's':1}[unit] for value, unit in durations) if durations else 5 * (attempt + 1)
        # Do not shorten a long provider wait and hammer its exhausted quota.
        # generate() rejects delays beyond its remaining two-minute retry budget.
        return max(1.0, delay + 1.0)

    @property
    def provider_name(self) -> str:
        return "groq"


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    _providers: dict[str, type[LLMProvider]] = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
        "groq": GroqProvider,
    }

    @classmethod
    def create(cls, provider_name: str | None = None) -> LLMProvider:
        """Create an LLM provider instance.

        Args:
            provider_name: Name of the provider. If None, uses settings.

        Returns:
            LLMProvider instance.

        Raises:
            ConfigurationError: If provider is unknown.
        """
        name = provider_name or get_settings().llm_provider
        provider_cls = cls._providers.get(name.lower())
        if provider_cls is None:
            supported = ", ".join(cls._providers.keys())
            raise ConfigurationError(
                f"Unknown LLM provider '{name}'. Supported: {supported}"
            )
        return provider_cls()

    @classmethod
    def create_optional(cls) -> Optional[LLMProvider]:
        """Try to create an LLM provider; return None if not configured.

        Returns:
            LLMProvider instance or None.
        """
        try:
            return cls.create()
        except (ConfigurationError, LLMProviderError) as exc:
            logger.warning("LLM provider not available: %s", exc.message)
            return None
