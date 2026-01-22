"""AI Manager for creating and managing all AI participants.

The AI Manager handles graceful degradation - if LLM providers are unavailable,
the application continues to work normally with human-only pairing.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional, Callable, Awaitable

from .config import LLMConfigLoader, LLMSettings, ProviderConfig
from .providers import ProviderFactory, get_provider
from .personas import PersonaManager, Persona
from .base import BaseLLMProvider
from .ai_participant import AIParticipant, AIParticipantConfig

logger = logging.getLogger(__name__)


class AIManager:
    """
    Manages all AI participants in the system.

    Responsibilities:
    - Loading LLM configuration
    - Managing provider pool
    - Creating/removing AI participants
    - Enforcing limits

    The manager is designed to fail gracefully - if no LLM providers are available,
    the application continues to work with human-only pairing.
    """

    def __init__(
        self,
        llm_config_path: Path,
        personas_path: Path,
        on_ai_message: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ):
        """
        Initialize the AI Manager.

        Args:
            llm_config_path: Path to llm_config.json
            personas_path: Path to personas.json
            on_ai_message: Callback when any AI generates a message (ai_id, think, speech)
        """
        self.config_loader = LLMConfigLoader(llm_config_path)
        self.persona_manager = PersonaManager(personas_path)
        self.on_ai_message = on_ai_message

        self._settings: Optional[LLMSettings] = None
        self._providers: dict[str, BaseLLMProvider] = {}
        self._participants: dict[str, AIParticipant] = {}
        self._initialized = False
        self._initialization_error: Optional[str] = None

    async def initialize(self):
        """Initialize the AI manager, loading configuration and creating providers.

        This method is designed to never raise exceptions - it will log errors
        and disable AI features if initialization fails.
        """
        if self._initialized:
            return

        try:
            # Load configuration
            self._settings = self.config_loader.load()
        except Exception as e:
            logger.warning(f"Failed to load LLM config, AI features disabled: {e}")
            self._initialization_error = str(e)
            self._initialized = True
            return

        try:
            self.persona_manager.load()
        except Exception as e:
            logger.warning(f"Failed to load personas, using defaults: {e}")
            # Personas will use built-in defaults

        if not self._settings.enabled:
            logger.info("AI participants disabled in configuration")
            self._initialized = True
            return

        # Initialize providers (failures are handled individually)
        await self._initialize_providers()

        self._initialized = True

        if self._providers:
            logger.info(
                f"AI Manager initialized with providers: {list(self._providers.keys())}"
            )
        else:
            logger.warning(
                "AI Manager initialized but no providers available. "
                "AI features will be disabled. Check your API keys and configuration."
            )

    async def _initialize_providers(self):
        """Initialize all enabled LLM providers.

        Each provider is initialized independently - failures don't affect other providers.
        """
        if not self._settings:
            return

        for provider_name in self._settings.get_enabled_providers():
            config = self._settings.get_provider_config(provider_name)
            if not config:
                continue

            try:
                provider = get_provider(provider_name, config)
                if provider:
                    await provider.initialize()
                    self._providers[provider_name] = provider
                    logger.info(f"Initialized provider: {provider_name}")
            except ImportError as e:
                logger.warning(
                    f"Provider {provider_name} unavailable (missing dependency): {e}"
                )
            except ConnectionError as e:
                logger.warning(
                    f"Provider {provider_name} unavailable (connection failed): {e}"
                )
            except ValueError as e:
                logger.warning(
                    f"Provider {provider_name} unavailable (configuration error): {e}"
                )
            except Exception as e:
                logger.warning(
                    f"Provider {provider_name} unavailable (unexpected error): {e}"
                )

    @property
    def settings(self) -> Optional[LLMSettings]:
        """Get current settings."""
        return self._settings

    @property
    def is_enabled(self) -> bool:
        """Check if AI participants are enabled in configuration."""
        return self._settings is not None and self._settings.enabled

    @property
    def is_available(self) -> bool:
        """Check if AI participants are enabled AND providers are available.

        This is the main check to use before attempting to create AI participants.
        """
        return self.is_enabled and len(self._providers) > 0

    @property
    def force_ai_on_odd_users(self) -> bool:
        """Check if AI should be forced for odd users.

        Returns False if no providers are available (graceful degradation).
        """
        if not self._settings or not self.is_available:
            return False
        return self._settings.ai_participants.force_ai_on_odd_users

    @property
    def pairing_delay_enabled(self) -> bool:
        """Check if pairing delay is enabled."""
        if not self._settings:
            return False
        return self._settings.pairing.delay_enabled

    @property
    def reassign_delay_seconds(self) -> int:
        """Get the reassign delay in seconds."""
        if not self._settings:
            return 10
        return self._settings.pairing.reassign_delay_seconds

    def get_available_provider(self) -> Optional[BaseLLMProvider]:
        """Get an available provider, preferring the default."""
        if not self._providers:
            return None

        # Try default provider first
        if self._settings:
            default = self._settings.default_provider
            if default in self._providers:
                return self._providers[default]

        # Fall back to any available provider
        return next(iter(self._providers.values()), None)

    def get_provider(self, name: str) -> Optional[BaseLLMProvider]:
        """Get a specific provider by name."""
        return self._providers.get(name)

    async def create_ai_participant(
        self,
        partner_id: str,
        session_id: str,
        topic: str,
        task: str,
        persona_id: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> Optional[AIParticipant]:
        """
        Create a new AI participant for a conversation.

        Args:
            partner_id: Human partner's user ID
            session_id: Conversation session ID
            topic: Conversation topic
            task: AI's assigned task
            persona_id: Specific persona to use (random if None)
            provider_name: Specific provider to use (default if None)

        Returns:
            The created AIParticipant, or None if creation failed
        """
        if not self._initialized:
            await self.initialize()

        if not self.is_enabled:
            logger.warning("Cannot create AI participant: AI is disabled")
            return None

        # Check max participants limit
        max_ai = self._settings.ai_participants.max_ai_participants
        if len(self._participants) >= max_ai:
            logger.warning(f"Cannot create AI participant: max limit ({max_ai}) reached")
            return None

        # Get provider
        provider = (
            self.get_provider(provider_name)
            if provider_name
            else self.get_available_provider()
        )
        if not provider:
            logger.error("No available LLM provider")
            return None

        # Get persona
        persona = (
            self.persona_manager.get_persona(persona_id)
            if persona_id
            else self.persona_manager.get_random_persona()
        )
        if not persona:
            logger.error("No available persona")
            return None

        # Create AI ID
        ai_id = f"ai_{uuid.uuid4().hex[:8]}"

        # Create config from settings
        config = AIParticipantConfig(
            idle_timeout_seconds=self._settings.behavior.idle_timeout_seconds,
            idle_check_interval_seconds=self._settings.behavior.idle_check_interval_seconds,
            response_delay_min_ms=self._settings.behavior.response_delay_min_ms,
            response_delay_max_ms=self._settings.behavior.response_delay_max_ms,
        )

        # Create participant
        participant = AIParticipant(
            ai_id=ai_id,
            provider=provider,
            persona=persona,
            config=config,
            on_message=self.on_ai_message,
        )

        # Start conversation
        await participant.start_conversation(
            partner_id=partner_id,
            session_id=session_id,
            topic=topic,
            task=task,
        )

        self._participants[ai_id] = participant
        logger.info(
            f"Created AI participant {ai_id} with persona '{persona.name}' "
            f"for partner {partner_id}"
        )

        return participant

    async def remove_ai_participant(self, ai_id: str):
        """Remove an AI participant."""
        participant = self._participants.pop(ai_id, None)
        if participant:
            await participant.end_conversation()
            logger.info(f"Removed AI participant {ai_id}")

    async def remove_ai_by_partner(self, partner_id: str):
        """Remove the AI participant paired with a specific human."""
        ai_id = None
        for aid, participant in self._participants.items():
            if participant.state.partner_id == partner_id:
                ai_id = aid
                break

        if ai_id:
            await self.remove_ai_participant(ai_id)

    def get_ai_participant(self, ai_id: str) -> Optional[AIParticipant]:
        """Get an AI participant by ID."""
        return self._participants.get(ai_id)

    def get_ai_by_partner(self, partner_id: str) -> Optional[AIParticipant]:
        """Get the AI participant paired with a specific human."""
        for participant in self._participants.values():
            if participant.state.partner_id == partner_id:
                return participant
        return None

    def is_ai_participant(self, user_id: str) -> bool:
        """Check if a user ID belongs to an AI participant."""
        return user_id in self._participants or user_id.startswith("ai_")

    def get_active_ai_count(self) -> int:
        """Get the number of active AI participants."""
        return len(self._participants)

    def get_all_ai_states(self) -> list[dict]:
        """Get state dictionaries for all AI participants."""
        return [p.get_state_dict() for p in self._participants.values()]

    async def forward_message_to_ai(self, ai_id: str, content: str):
        """Forward a message from a human to their AI partner."""
        participant = self._participants.get(ai_id)
        if participant:
            await participant.receive_message(content)
        else:
            logger.warning(f"Tried to forward message to unknown AI: {ai_id}")

    async def shutdown(self):
        """Shutdown all AI participants and cleanup."""
        logger.info("Shutting down AI Manager...")

        # End all conversations
        for ai_id in list(self._participants.keys()):
            await self.remove_ai_participant(ai_id)

        # Clear providers
        self._providers.clear()
        self._initialized = False

        logger.info("AI Manager shutdown complete")
