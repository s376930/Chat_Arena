"""Anthropic Claude LLM provider."""

from typing import AsyncIterator, Optional

from ..base import BaseLLMProvider, LLMMessage, LLMResponse, ConversationContext


class AnthropicProvider(BaseLLMProvider):
    """Provider for Anthropic's Claude models."""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        self._client = None

    async def _setup(self):
        """Initialize the Anthropic client."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def generate_response(
        self,
        messages: list[LLMMessage],
        system_prompt: str,
        context: Optional[ConversationContext] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a response using Claude."""
        await self.initialize()

        formatted_messages = self.format_messages(messages)

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=formatted_messages,
        )

        content = response.content[0].text if response.content else ""

        return LLMResponse(
            content=content,
            model=response.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            finish_reason=response.stop_reason or "",
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
        """Generate a streaming response using Claude."""
        await self.initialize()

        formatted_messages = self.format_messages(messages)

        async with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=formatted_messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
