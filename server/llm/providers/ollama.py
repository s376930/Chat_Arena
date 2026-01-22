"""Ollama LLM provider for local model inference.

Ollama runs locally on your machine. To use this provider:
1. Install Ollama: https://ollama.ai/download
2. Pull a model: ollama pull huihui_ai/gemma3-abliterated:27b
3. Ollama runs automatically, or start with: ollama serve
4. The server runs at http://localhost:11434 by default
"""

import asyncio
import logging
from typing import AsyncIterator, Optional

import httpx

from ..base import BaseLLMProvider, LLMMessage, LLMResponse, ConversationContext

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Provider for local Ollama models.

    Ollama must be installed and running locally. This provider connects
    to the local Ollama server (default: http://localhost:11434).

    Supported models include: gemma3, llama3.2, mistral, phi3, etc.
    Run 'ollama list' to see installed models.
    """

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "huihui_ai/gemma3-abliterated:27b"

    def __init__(self, model: str = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Use gemma3 as default if no model specified
        model = model or self.DEFAULT_MODEL
        super().__init__(model, api_key, base_url or self.DEFAULT_BASE_URL)
        self._llm = None
        self._available = False

    async def _check_ollama_available(self) -> bool:
        """Check if Ollama server is running and accessible."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    return True
        except Exception as e:
            logger.debug(f"Ollama server check failed: {e}")
        return False

    async def _check_model_available(self) -> bool:
        """Check if the specified model is available in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                    # Check for exact match or model name without tag
                    model_name = self.model.split(":")[0]
                    return model_name in models or self.model in [m.get("name") for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Model check failed: {e}")
        return False

    async def _setup(self):
        """Initialize the Ollama client."""
        # First check if Ollama server is running
        if not await self._check_ollama_available():
            raise ConnectionError(
                f"Ollama server not available at {self.base_url}. "
                "Please install Ollama (https://ollama.ai) and run 'ollama serve'"
            )

        # Check if model is available
        if not await self._check_model_available():
            logger.warning(
                f"Model '{self.model}' not found in Ollama. "
                f"Run 'ollama pull {self.model}' to download it."
            )
            # Don't raise error - Ollama will pull the model on first use

        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError(
                "langchain-ollama package not installed. Run: pip install langchain-ollama"
            )

        self._llm = ChatOllama(
            model=self.model,
            base_url=self.base_url,
        )
        self._available = True
        logger.info(f"Ollama provider initialized with model: {self.model}")

    async def health_check(self) -> bool:
        """Check if Ollama is available and ready."""
        return await self._check_ollama_available()

    async def generate_response(
        self,
        messages: list[LLMMessage],
        system_prompt: str,
        context: Optional[ConversationContext] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a response using local Ollama."""
        try:
            await self.initialize()
        except (ConnectionError, ImportError) as e:
            logger.error(f"Ollama initialization failed: {e}")
            raise

        try:
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        except ImportError:
            raise ImportError("langchain-core package not installed. Run: pip install langchain")

        # Convert messages to LangChain format
        langchain_messages = [SystemMessage(content=system_prompt)]
        for msg in messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))

        # Set temperature for this request
        self._llm.temperature = temperature

        try:
            response = await self._llm.ainvoke(langchain_messages)
            content = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=0,
            finish_reason="stop",
            raw_response=None,
        )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        system_prompt: str,
        context: Optional[ConversationContext] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Generate a streaming response using local Ollama."""
        try:
            await self.initialize()
        except (ConnectionError, ImportError) as e:
            logger.error(f"Ollama initialization failed: {e}")
            raise

        try:
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        except ImportError:
            raise ImportError("langchain-core package not installed. Run: pip install langchain")

        langchain_messages = [SystemMessage(content=system_prompt)]
        for msg in messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))

        self._llm.temperature = temperature

        try:
            async for chunk in self._llm.astream(langchain_messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise
