"""AI participant controller for managing a single AI in a conversation."""

import asyncio
import random
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Awaitable

from .base import BaseLLMProvider, LLMResponse
from .personas import Persona
from .memory import ConversationMemory
from .context import ContextBuilder
from .sentiment import SentimentAnalyzer, SentimentResult

logger = logging.getLogger(__name__)


def sanitize_speech(text: str) -> str:
    """
    Remove LLM artifacts from speech text while preserving the actual message.

    Removes:
    - XML/HTML-like tags: <speech>, </speech>, <tag>, etc.
    - Square bracket content: [stage directions], [actions], etc.
    - Parenthetical stage directions: (sighs), (laughing), etc.

    Args:
        text: Raw speech text from LLM

    Returns:
        Cleaned speech text
    """
    if not text:
        return text

    # Remove XML/HTML-like tags (but keep content between opening/closing tags)
    # Matches <word>, </word>, <word/>, <word attr="value">, etc.
    text = re.sub(r'<[^>]+>', '', text)

    # Remove square bracket content entirely (stage directions, actions)
    # Matches [anything here], [Steepling hands], etc.
    text = re.sub(r'\[[^\]]*\]', '', text)

    # Remove parenthetical stage directions (action words at start or standalone)
    # Common patterns: (sighs), (laughing nervously), (pauses), etc.
    # Only remove if it looks like a stage direction, not normal parenthetical text
    stage_direction_pattern = r'\(\s*(?:[A-Z][a-z]*(?:ing|s|ed)?(?:\s+\w+)*)\s*\)'
    text = re.sub(stage_direction_pattern, '', text)

    # Also remove parentheticals that are clearly actions (lowercase action verbs)
    action_verbs = r'\(\s*(?:sighs?|laughs?|laughing|chuckles?|chuckling|smiles?|smiling|'
    action_verbs += r'grins?|grinning|nods?|nodding|shrugs?|shrugging|pauses?|pausing|'
    action_verbs += r'thinks?|thinking|frowns?|frowning|winks?|winking|gestures?|gesturing|'
    action_verbs += r'leans?\s+\w+|clears?\s+throat|rolls?\s+eyes?|raises?\s+eyebrow)'
    action_verbs += r'(?:\s+\w+)*\s*\)'
    text = re.sub(action_verbs, '', text, flags=re.IGNORECASE)

    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


@dataclass
class AIParticipantConfig:
    """Configuration for an AI participant."""
    idle_timeout_seconds: int = 120
    idle_check_interval_seconds: int = 30
    response_delay_min_ms: int = 500
    response_delay_max_ms: int = 3000
    max_retries: int = 3


@dataclass
class AIParticipantState:
    """Current state of an AI participant."""
    partner_id: str = ""
    session_id: str = ""
    topic: str = ""
    task: str = ""
    is_active: bool = False
    last_partner_message_time: Optional[datetime] = None
    last_ai_message_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


class AIParticipant:
    """
    Controls a single AI participant in a conversation.

    Handles:
    - Receiving and responding to partner messages
    - Idle detection and re-engagement
    - Response generation with proper formatting
    - Typing simulation delays
    """

    def __init__(
        self,
        ai_id: str,
        provider: BaseLLMProvider,
        persona: Persona,
        config: Optional[AIParticipantConfig] = None,
        on_message: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ):
        """
        Initialize an AI participant.

        Args:
            ai_id: Unique identifier for this AI
            provider: LLM provider for generating responses
            persona: The persona this AI should embody
            config: Configuration options
            on_message: Callback when AI generates a message (ai_id, think, speech)
        """
        self.ai_id = ai_id
        self.provider = provider
        self.persona = persona
        self.config = config or AIParticipantConfig()
        self.on_message = on_message

        self.memory = ConversationMemory()
        self.context_builder = ContextBuilder()
        self.sentiment_analyzer = SentimentAnalyzer()

        self.state = AIParticipantState()
        self._idle_task: Optional[asyncio.Task] = None
        self._current_sentiment = "neutral"

    async def start_conversation(
        self,
        partner_id: str,
        session_id: str,
        topic: str,
        task: str,
    ):
        """Start a conversation with a human partner."""
        self.state.partner_id = partner_id
        self.state.session_id = session_id
        self.state.topic = topic
        self.state.task = task
        self.state.is_active = True
        self.state.last_partner_message_time = datetime.now()

        self.memory.set_context(
            topic=topic,
            task=task,
            session_id=session_id,
        )

        # Start idle monitoring
        self._start_idle_monitor()

        logger.info(f"AI {self.ai_id} started conversation with {partner_id}")

    async def end_conversation(self):
        """End the current conversation."""
        self.state.is_active = False
        self._stop_idle_monitor()

        # Clear memory for next conversation
        self.memory.clear()

        logger.info(f"AI {self.ai_id} ended conversation")

    async def receive_message(self, content: str):
        """
        Receive a message from the human partner.

        Args:
            content: The message content from the partner
        """
        if not self.state.is_active:
            logger.warning(f"AI {self.ai_id} received message but not active")
            return

        # Update timing
        self.state.last_partner_message_time = datetime.now()

        # Analyze sentiment
        sentiment_result = self.sentiment_analyzer.analyze(content)
        self._current_sentiment = sentiment_result.sentiment

        # Add to memory
        self.memory.add_partner_message(content, sentiment_result.sentiment)

        # Generate and send response
        await self._generate_and_send_response()

    async def _generate_and_send_response(self, is_idle_prompt: bool = False) -> bool:
        """Generate a response and send it via callback.

        Returns:
            True if message was successfully generated and sent, False otherwise.
        """
        # Calculate idle time
        idle_seconds = 0
        if self.state.last_partner_message_time:
            idle_seconds = int(
                (datetime.now() - self.state.last_partner_message_time).total_seconds()
            )

        # Build prompt and context
        system_prompt, context = self.context_builder.build_full_prompt_context(
            persona=self.persona,
            memory=self.memory,
            partner_sentiment=self._current_sentiment,
            partner_idle_seconds=idle_seconds,
            is_idle_prompt=is_idle_prompt,
        )

        # Get conversation history
        messages = self.memory.get_messages_for_llm()

        # Generate response with retries
        response = await self._generate_with_retry(messages, system_prompt, context)
        if not response:
            logger.error(f"AI {self.ai_id} failed to generate response")
            return False

        # Sanitize speech to remove LLM artifacts
        clean_speech = sanitize_speech(response.speech)

        # Check if speech is empty after sanitization
        if not clean_speech:
            logger.warning(f"AI {self.ai_id} speech was empty after sanitization")
            return False

        # Simulate typing delay
        await self._simulate_typing_delay(clean_speech)

        # Add to memory (store original for context, but send sanitized)
        self.memory.add_ai_message(response.think, clean_speech)
        self.state.last_ai_message_time = datetime.now()

        # Send via callback (sanitized speech)
        if self.on_message:
            await self.on_message(self.ai_id, response.think, clean_speech)

        return True

    async def _generate_with_retry(
        self,
        messages,
        system_prompt: str,
        context,
    ) -> Optional[LLMResponse]:
        """Generate a response with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                response = await self.provider.generate_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    context=context,
                )

                # Validate response has required parts
                if response.speech:
                    return response

                logger.warning(
                    f"AI {self.ai_id} got response without speech (attempt {attempt + 1})"
                )

            except Exception as e:
                logger.error(
                    f"AI {self.ai_id} generation error (attempt {attempt + 1}): {e}"
                )

            # Wait before retry
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(1.0)

        return None

    async def _simulate_typing_delay(self, text: str):
        """Simulate typing delay based on message length."""
        # Base delay on word count
        word_count = len(text.split())

        # Calculate delay: roughly 200ms per word, with min/max bounds
        base_delay = word_count * 200
        delay_ms = max(
            self.config.response_delay_min_ms,
            min(base_delay, self.config.response_delay_max_ms),
        )

        # Add some randomness
        delay_ms = int(delay_ms * random.uniform(0.8, 1.2))

        await asyncio.sleep(delay_ms / 1000.0)

    def _start_idle_monitor(self):
        """Start the idle monitoring task."""
        if self._idle_task:
            self._idle_task.cancel()
        self._idle_task = asyncio.create_task(self._idle_monitor_loop())

    def _stop_idle_monitor(self):
        """Stop the idle monitoring task."""
        if self._idle_task:
            self._idle_task.cancel()
            self._idle_task = None

    async def _idle_monitor_loop(self):
        """Monitor for partner idle and send re-engagement messages."""
        try:
            while self.state.is_active:
                await asyncio.sleep(self.config.idle_check_interval_seconds)

                if not self.state.is_active:
                    break

                # Check if partner is idle
                if self.state.last_partner_message_time:
                    idle_seconds = (
                        datetime.now() - self.state.last_partner_message_time
                    ).total_seconds()

                    if idle_seconds >= self.config.idle_timeout_seconds:
                        logger.info(
                            f"AI {self.ai_id} partner idle for {idle_seconds}s, "
                            f"sending re-engagement"
                        )
                        success = await self._generate_and_send_response(is_idle_prompt=True)
                        # Only reset the timer if message was successfully sent
                        if success:
                            self.state.last_partner_message_time = datetime.now()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"AI {self.ai_id} idle monitor error: {e}")

    def get_state_dict(self) -> dict:
        """Get the current state as a dictionary."""
        return {
            "ai_id": self.ai_id,
            "partner_id": self.state.partner_id,
            "session_id": self.state.session_id,
            "topic": self.state.topic,
            "task": self.state.task,
            "is_active": self.state.is_active,
            "persona_id": self.persona.id,
            "persona_name": self.persona.name,
            "provider": self.provider.name,
            "model": self.provider.model,
            "turn_count": self.memory.get_turn_count(),
            "current_sentiment": self._current_sentiment,
        }
