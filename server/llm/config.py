"""LLM configuration loader and settings management."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""
    enabled: bool = False
    model: str = ""
    api_key_env: str = ""
    base_url: Optional[str] = None

    @property
    def api_key(self) -> Optional[str]:
        """Get API key from environment variable."""
        if self.api_key_env:
            return os.getenv(self.api_key_env)
        return None


@dataclass
class BehaviorConfig:
    """AI behavior configuration."""
    idle_timeout_seconds: int = 120
    idle_check_interval_seconds: int = 30
    response_delay_min_ms: int = 500
    response_delay_max_ms: int = 3000


@dataclass
class AIParticipantsConfig:
    """AI participants configuration."""
    force_ai_on_odd_users: bool = True
    max_ai_participants: int = 5


@dataclass
class PairingConfig:
    """Pairing configuration."""
    delay_enabled: bool = True
    reassign_delay_seconds: int = 10


@dataclass
class LLMSettings:
    """Complete LLM configuration settings."""
    enabled: bool = True
    default_provider: str = "anthropic"
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    ai_participants: AIParticipantsConfig = field(default_factory=AIParticipantsConfig)
    pairing: PairingConfig = field(default_factory=PairingConfig)

    def get_provider_config(self, name: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider."""
        return self.providers.get(name)

    def get_enabled_providers(self) -> list[str]:
        """Get list of enabled provider names."""
        return [name for name, config in self.providers.items() if config.enabled]

    def get_default_provider_config(self) -> Optional[ProviderConfig]:
        """Get the default provider configuration."""
        return self.providers.get(self.default_provider)


class LLMConfigLoader:
    """Loader for LLM configuration from JSON file."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._settings: Optional[LLMSettings] = None

    def load(self) -> LLMSettings:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            # Return default settings if file doesn't exist
            return self._default_settings()

        with open(self.config_path, "r") as f:
            data = json.load(f)

        self._settings = self._parse_config(data)
        return self._settings

    def reload(self) -> LLMSettings:
        """Reload configuration from file."""
        self._settings = None
        return self.load()

    @property
    def settings(self) -> LLMSettings:
        """Get current settings, loading if necessary."""
        if self._settings is None:
            return self.load()
        return self._settings

    def _parse_config(self, data: dict) -> LLMSettings:
        """Parse JSON data into LLMSettings."""
        providers = {}
        for name, provider_data in data.get("providers", {}).items():
            providers[name] = ProviderConfig(
                enabled=provider_data.get("enabled", False),
                model=provider_data.get("model", ""),
                api_key_env=provider_data.get("api_key_env", ""),
                base_url=provider_data.get("base_url"),
            )

        behavior_data = data.get("behavior", {})
        behavior = BehaviorConfig(
            idle_timeout_seconds=behavior_data.get("idle_timeout_seconds", 120),
            idle_check_interval_seconds=behavior_data.get("idle_check_interval_seconds", 30),
            response_delay_min_ms=behavior_data.get("response_delay_min_ms", 500),
            response_delay_max_ms=behavior_data.get("response_delay_max_ms", 3000),
        )

        ai_data = data.get("ai_participants", {})
        ai_participants = AIParticipantsConfig(
            force_ai_on_odd_users=ai_data.get("force_ai_on_odd_users", True),
            max_ai_participants=ai_data.get("max_ai_participants", 5),
        )

        pairing_data = data.get("pairing", {})
        pairing = PairingConfig(
            delay_enabled=pairing_data.get("delay_enabled", True),
            reassign_delay_seconds=pairing_data.get("reassign_delay_seconds", 10),
        )

        return LLMSettings(
            enabled=data.get("enabled", True),
            default_provider=data.get("default_provider", "anthropic"),
            providers=providers,
            behavior=behavior,
            ai_participants=ai_participants,
            pairing=pairing,
        )

    def _default_settings(self) -> LLMSettings:
        """Return default settings when config file doesn't exist."""
        return LLMSettings(
            enabled=True,
            default_provider="anthropic",
            providers={
                "anthropic": ProviderConfig(
                    enabled=True,
                    model="claude-sonnet-4-20250514",
                    api_key_env="ANTHROPIC_API_KEY",
                ),
                "openai": ProviderConfig(
                    enabled=True,
                    model="gpt-4o",
                    api_key_env="OPENAI_API_KEY",
                ),
                "grok": ProviderConfig(
                    enabled=False,
                    model="grok-2",
                    api_key_env="XAI_API_KEY",
                    base_url="https://api.x.ai/v1",
                ),
                "ollama": ProviderConfig(
                    enabled=False,
                    model="llama3.2",
                    base_url="http://localhost:11434",
                ),
            },
            behavior=BehaviorConfig(),
            ai_participants=AIParticipantsConfig(),
            pairing=PairingConfig(),
        )
