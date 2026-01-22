"""Agentic context builder for AI participants."""

from dataclasses import dataclass
from typing import Optional

from .personas import Persona
from .memory import ConversationMemory
from .base import ConversationContext


@dataclass
class SystemPromptContext:
    """Full context for building a system prompt."""
    persona: Persona
    topic: str
    task: str
    partner_sentiment: str = "neutral"
    conversation_turn: int = 0
    is_idle_prompt: bool = False
    partner_idle_seconds: int = 0


class ContextBuilder:
    """Builds system prompts and context for AI responses."""

    RESPONSE_FORMAT_INSTRUCTIONS = """
## Response Format

You MUST respond using EXACTLY this format:

<think>[Your internal reasoning, strategy, and observations about the conversation]</think>
<speech>[Your actual message to your conversation partner]</speech>

IMPORTANT:
- The <think> section is private - only for your internal reasoning
- The <speech> section is what your partner will see
- Both sections are REQUIRED in every response
- Keep your speech natural and conversational
- Your think section should show genuine engagement with the topic
"""

    CONVERSATION_GUIDELINES = """
## Conversation Guidelines

1. Be authentic to your persona while remaining respectful
2. Ask follow-up questions to show genuine interest
3. Share relevant thoughts and experiences
4. Keep responses conversational, not too long
5. Stay on topic but allow natural conversation flow
6. Be mindful of your partner's emotional state
7. If the conversation stalls, gently introduce new angles on the topic
"""

    IDLE_PROMPT_ADDITION = """
## Current Situation

Your conversation partner has been quiet for a while. Generate a friendly message to:
- Re-engage them in the conversation
- Ask an interesting question related to the topic
- Or share an observation that might spark discussion

Keep it natural - don't make them feel bad for being quiet.
"""

    def build_system_prompt(self, context: SystemPromptContext) -> str:
        """Build a complete system prompt for the AI."""
        sections = []

        # Persona section
        sections.append(context.persona.to_system_prompt_section())

        # Task section
        sections.append(self._build_task_section(context.topic, context.task))

        # Response format
        sections.append(self.RESPONSE_FORMAT_INSTRUCTIONS)

        # Guidelines
        sections.append(self.CONVERSATION_GUIDELINES)

        # Conversation state context
        sections.append(self._build_state_section(context))

        # Idle prompt if needed
        if context.is_idle_prompt:
            sections.append(self.IDLE_PROMPT_ADDITION)

        return "\n\n".join(sections)

    def _build_task_section(self, topic: str, task: str) -> str:
        """Build the task/topic section."""
        lines = ["## Your Conversation Task"]

        if topic:
            lines.append(f"\n**Topic**: {topic}")

        if task:
            lines.append(f"\n**Your Role**: {task}")

        lines.append(
            "\nEngage naturally in conversation about this topic while fulfilling your role. "
            "Be conversational and authentic, not robotic or formal."
        )

        return "\n".join(lines)

    def _build_state_section(self, context: SystemPromptContext) -> str:
        """Build the current conversation state section."""
        lines = ["## Current Conversation State"]

        lines.append(f"\n- Conversation turn: {context.conversation_turn}")
        lines.append(f"- Partner's apparent mood: {context.partner_sentiment}")

        if context.partner_idle_seconds > 0:
            lines.append(f"- Partner has been quiet for: {context.partner_idle_seconds} seconds")

        # Add sentiment-specific guidance
        if context.partner_sentiment in ["negative", "frustrated", "sad"]:
            lines.append("\n*Note: Your partner seems to be in a difficult mood. Be extra empathetic and supportive.*")
        elif context.partner_sentiment in ["excited", "happy", "enthusiastic"]:
            lines.append("\n*Note: Your partner seems engaged and positive. Match their energy!*")

        return "\n".join(lines)

    def build_conversation_context(
        self,
        memory: ConversationMemory,
        partner_sentiment: str = "neutral",
        partner_idle_seconds: int = 0,
        is_idle_prompt: bool = False,
    ) -> ConversationContext:
        """Build a ConversationContext from memory and current state."""
        return ConversationContext(
            topic=memory.topic,
            task=memory.task,
            partner_sentiment=partner_sentiment,
            conversation_turn=memory.get_turn_count(),
            partner_idle_seconds=partner_idle_seconds,
            is_idle_prompt=is_idle_prompt,
            additional_context={
                "partner_message_count": memory.get_partner_message_count(),
                "ai_message_count": memory.get_ai_message_count(),
                "recent_sentiments": memory.get_recent_sentiments(),
            },
        )

    def build_full_prompt_context(
        self,
        persona: Persona,
        memory: ConversationMemory,
        partner_sentiment: str = "neutral",
        partner_idle_seconds: int = 0,
        is_idle_prompt: bool = False,
    ) -> tuple[str, ConversationContext]:
        """Build both system prompt and conversation context."""
        system_context = SystemPromptContext(
            persona=persona,
            topic=memory.topic,
            task=memory.task,
            partner_sentiment=partner_sentiment,
            conversation_turn=memory.get_turn_count(),
            is_idle_prompt=is_idle_prompt,
            partner_idle_seconds=partner_idle_seconds,
        )

        system_prompt = self.build_system_prompt(system_context)

        conversation_context = self.build_conversation_context(
            memory=memory,
            partner_sentiment=partner_sentiment,
            partner_idle_seconds=partner_idle_seconds,
            is_idle_prompt=is_idle_prompt,
        )

        return system_prompt, conversation_context
