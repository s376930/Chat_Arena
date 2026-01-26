"""OpenAI ChatGPT LLM provider."""

import logging
from typing import AsyncIterator, Optional

from ..base import BaseLLMProvider, LLMMessage, LLMResponse, ConversationContext

logger = logging.getLogger(__name__)

# Valid OpenAI models (as of 2024-2025)
VALID_OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-4",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "o1",
    "o1-mini",
    "o1-preview",
]


class OpenAIProvider(BaseLLMProvider):
    """Provider for OpenAI's ChatGPT models."""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        self._client = None

    async def _setup(self):
        """Initialize the OpenAI client."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        # Warn if using an unrecognized model
        if self.model not in VALID_OPENAI_MODELS:
            logger.warning(
                f"Model '{self.model}' is not in the known OpenAI models list. "
                f"Valid models include: {', '.join(VALID_OPENAI_MODELS[:5])}..."
            )

        self._client = openai.AsyncOpenAI(api_key=self.api_key)
        logger.info(f"OpenAI provider initialized with model: {self.model}")

    async def generate_response(
        self,
        messages: list[LLMMessage],
        system_prompt: str,
        context: Optional[ConversationContext] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a response using ChatGPT."""
        try:
            await self.initialize()
        except (ImportError, ValueError) as e:
            logger.error(f"OpenAI initialization failed: {e}")
            raise

        # OpenAI uses system message in the messages list
        formatted_messages = [{"role": "system", "content": system_prompt}]
        formatted_messages.extend(self.format_messages(messages))

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice and choice.message else ""

        return LLMResponse(
            content=content or "",
            model=response.model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            finish_reason=choice.finish_reason if choice else "",
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        system_prompt: str,
        context: Optional[ConversationContext] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Generate a streaming response using ChatGPT."""
        try:
            await self.initialize()
        except (ImportError, ValueError) as e:
            logger.error(f"OpenAI initialization failed: {e}")
            raise

        formatted_messages = [{"role": "system", "content": system_prompt}]
        formatted_messages.extend(self.format_messages(messages))

        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            raise
