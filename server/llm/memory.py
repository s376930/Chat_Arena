"""Conversation memory management for AI participants."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base import LLMMessage


@dataclass
class MemoryEntry:
    """A single entry in conversation memory."""
    role: str  # "user" (human partner) or "assistant" (AI)
    content: str
    think: str = ""
    speech: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    sentiment: str = "neutral"


class ConversationMemory:
    """Manages conversation history for a single AI participant."""

    def __init__(self, max_entries: int = 50):
        self.max_entries = max_entries
        self._entries: list[MemoryEntry] = []
        self._topic: str = ""
        self._task: str = ""
        self._partner_name: str = "Partner"
        self._session_id: str = ""

    def set_context(
        self,
        topic: str = "",
        task: str = "",
        partner_name: str = "Partner",
        session_id: str = "",
    ):
        """Set the conversation context."""
        self._topic = topic
        self._task = task
        self._partner_name = partner_name
        self._session_id = session_id

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def task(self) -> str:
        return self._task

    @property
    def partner_name(self) -> str:
        return self._partner_name

    @property
    def session_id(self) -> str:
        return self._session_id

    def add_partner_message(self, content: str, sentiment: str = "neutral"):
        """Add a message from the human partner."""
        entry = MemoryEntry(
            role="user",
            content=content,
            speech=content,
            sentiment=sentiment,
        )
        self._add_entry(entry)

    def add_ai_message(self, think: str, speech: str):
        """Add a message from the AI (self)."""
        content = f"<think>{think}</think><speech>{speech}</speech>"
        entry = MemoryEntry(
            role="assistant",
            content=content,
            think=think,
            speech=speech,
        )
        self._add_entry(entry)

    def _add_entry(self, entry: MemoryEntry):
        """Add an entry, maintaining max size."""
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            # Remove oldest entries but keep at least the first few for context
            self._entries = self._entries[-self.max_entries:]

    def get_messages_for_llm(self) -> list[LLMMessage]:
        """Get messages formatted for LLM API calls."""
        messages = []
        for entry in self._entries:
            if entry.role == "user":
                # Partner messages are just their speech
                messages.append(LLMMessage(role="user", content=entry.speech or entry.content))
            else:
                # Our own messages include both think and speech
                messages.append(LLMMessage(role="assistant", content=entry.content))
        return messages

    def get_last_partner_message(self) -> Optional[MemoryEntry]:
        """Get the most recent message from the partner."""
        for entry in reversed(self._entries):
            if entry.role == "user":
                return entry
        return None

    def get_last_ai_message(self) -> Optional[MemoryEntry]:
        """Get the most recent AI message."""
        for entry in reversed(self._entries):
            if entry.role == "assistant":
                return entry
        return None

    def get_turn_count(self) -> int:
        """Get the total number of conversation turns."""
        return len(self._entries)

    def get_partner_message_count(self) -> int:
        """Get the number of messages from the partner."""
        return sum(1 for e in self._entries if e.role == "user")

    def get_ai_message_count(self) -> int:
        """Get the number of AI messages."""
        return sum(1 for e in self._entries if e.role == "assistant")

    def get_recent_sentiments(self, count: int = 5) -> list[str]:
        """Get recent partner message sentiments."""
        sentiments = []
        for entry in reversed(self._entries):
            if entry.role == "user":
                sentiments.append(entry.sentiment)
                if len(sentiments) >= count:
                    break
        return list(reversed(sentiments))

    def get_conversation_summary(self) -> dict:
        """Get a summary of the conversation."""
        return {
            "topic": self._topic,
            "task": self._task,
            "total_turns": self.get_turn_count(),
            "partner_messages": self.get_partner_message_count(),
            "ai_messages": self.get_ai_message_count(),
            "recent_sentiments": self.get_recent_sentiments(),
        }

    def clear(self):
        """Clear all memory."""
        self._entries.clear()
        self._topic = ""
        self._task = ""
        self._partner_name = "Partner"
        self._session_id = ""

    def to_dict(self) -> dict:
        """Serialize memory to dictionary."""
        return {
            "topic": self._topic,
            "task": self._task,
            "partner_name": self._partner_name,
            "session_id": self._session_id,
            "entries": [
                {
                    "role": e.role,
                    "content": e.content,
                    "think": e.think,
                    "speech": e.speech,
                    "timestamp": e.timestamp.isoformat(),
                    "sentiment": e.sentiment,
                }
                for e in self._entries
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMemory":
        """Deserialize memory from dictionary."""
        memory = cls()
        memory._topic = data.get("topic", "")
        memory._task = data.get("task", "")
        memory._partner_name = data.get("partner_name", "Partner")
        memory._session_id = data.get("session_id", "")

        for entry_data in data.get("entries", []):
            entry = MemoryEntry(
                role=entry_data["role"],
                content=entry_data["content"],
                think=entry_data.get("think", ""),
                speech=entry_data.get("speech", ""),
                timestamp=datetime.fromisoformat(entry_data.get("timestamp", datetime.now().isoformat())),
                sentiment=entry_data.get("sentiment", "neutral"),
            )
            memory._entries.append(entry)

        return memory
