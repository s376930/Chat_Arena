"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str  # "user", "assistant", or "system"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    think: str = ""
    speech: str = ""
    model: str = ""
    tokens_used: int = 0
    finish_reason: str = ""
    raw_response: Optional[dict] = None

    def __post_init__(self):
        """Parse think and speech from content if not provided."""
        if self.content and not self.think and not self.speech:
            self._parse_content()

    def _parse_content(self):
        """Parse <think> and <speech> tags from content."""
        import re

        think_match = re.search(r"<think>(.*?)</think>", self.content, re.DOTALL)
        speech_match = re.search(r"<speech>(.*?)</speech>", self.content, re.DOTALL)

        if think_match:
            self.think = think_match.group(1).strip()
        if speech_match:
            self.speech = speech_match.group(1).strip()

        # If no tags found, treat entire content as speech
        if not self.think and not self.speech:
            self.speech = self.content.strip()


@dataclass
class ConversationContext:
    """Context information for generating responses."""
    topic: str = ""
    task: str = ""
    partner_sentiment: str = "neutral"
    conversation_turn: int = 0
    partner_idle_seconds: int = 0
    is_idle_prompt: bool = False
    additional_context: dict = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._initialized = False

    @property
    def name(self) -> str:
        """Return the provider name."""
        return self.__class__.__name__.replace("Provider", "").lower()

    async def initialize(self):
        """Initialize the provider (create client, validate credentials)."""
        if not self._initialized:
            await self._setup()
            self._initialized = True

    @abstractmethod
    async def _setup(self):
        """Provider-specific setup. Override in subclasses."""
        pass

    @abstractmethod
    async def generate_response(
        self,
        messages: list[LLMMessage],
        system_prompt: str,
        context: Optional[ConversationContext] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: Conversation history
            system_prompt: System prompt for the AI
            context: Additional context for generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            LLMResponse with the generated content
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        system_prompt: str,
        context: Optional[ConversationContext] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM.

        Args:
            messages: Conversation history
            system_prompt: System prompt for the AI
            context: Additional context for generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            String chunks of the response
        """
        pass

    async def health_check(self) -> bool:
        """Check if the provider is healthy and ready."""
        try:
            await self.initialize()
            return True
        except Exception:
            return False

    def format_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Format messages for the API. Override if needed."""
        return [{"role": m.role, "content": m.content} for m in messages]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model})"
