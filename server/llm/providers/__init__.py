"""LLM Provider factory and registration."""

from typing import Optional

from ..base import BaseLLMProvider
from ..config import ProviderConfig


class ProviderFactory:
    """Factory for creating LLM providers."""

    _providers: dict[str, type[BaseLLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[BaseLLMProvider]):
        """Register a provider class."""
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create(cls, name: str, config: ProviderConfig) -> Optional[BaseLLMProvider]:
        """Create a provider instance from configuration."""
        provider_class = cls._providers.get(name.lower())
        if not provider_class:
            return None

        return provider_class(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of registered provider names."""
        return list(cls._providers.keys())


def get_provider(name: str, config: ProviderConfig) -> Optional[BaseLLMProvider]:
    """Convenience function to create a provider."""
    return ProviderFactory.create(name, config)


# Import and register providers
from .anthropic import AnthropicProvider
from .openai_provider import OpenAIProvider
from .grok import GrokProvider
from .ollama import OllamaProvider

ProviderFactory.register("anthropic", AnthropicProvider)
ProviderFactory.register("openai", OpenAIProvider)
ProviderFactory.register("grok", GrokProvider)
ProviderFactory.register("ollama", OllamaProvider)

__all__ = [
    "ProviderFactory",
    "get_provider",
    "AnthropicProvider",
    "OpenAIProvider",
    "GrokProvider",
    "OllamaProvider",
]
