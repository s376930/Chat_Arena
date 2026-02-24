import json
import aiofiles
from datetime import datetime
from typing import Optional

from .config import (
    CONVERSATIONS_DIR,
    TOPICS_TASKS_FILE,
    CONSENT_FILE
)
from .models import (
    Conversation,
    ConversationMessage,
    Participant,
    ConsentData,
    TopicsTasksData,
    Topic,
    Task
)


class StorageService:
    """Handles all file storage operations."""

    def __init__(self):
        # In-memory cache of active conversations
        self._conversations: dict[str, Conversation] = {}

    # ==================== Conversation Storage ====================

    def _save_conversation_sync(self, conversation: Conversation) -> bool:
        """Synchronously save conversation to disk (for use in sync methods)."""
        file_path = CONVERSATIONS_DIR / f"{conversation.session_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(conversation.model_dump(), indent=2))
            return True
        except Exception as e:
            print(f"Error saving conversation {conversation.session_id}: {e}")
            return False

    def _load_conversation_from_disk(self, session_id: str) -> Optional[Conversation]:
        """Load a conversation from disk if it exists."""
        file_path = CONVERSATIONS_DIR / f"{session_id}.json"
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return Conversation(**data)
        except Exception as e:
            print(f"Error loading conversation {session_id}: {e}")
        return None

    def create_conversation(
        self,
        session_id: str,
        topic: str,
        participants: list[dict]
    ) -> Conversation:
        """Create a new conversation and save to disk immediately."""
        conversation = Conversation(
            session_id=session_id,
            topic=topic,
            participants=[Participant(**p) for p in participants],
            messages=[],
            started_at=datetime.utcnow().isoformat() + "Z"
        )
        self._conversations[session_id] = conversation
        # Save to disk immediately for persistence across restarts/workers
        self._save_conversation_sync(conversation)
        return conversation

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> Optional[ConversationMessage]:
        """Add a message to a conversation and save to disk."""
        # Try to get from memory first
        conversation = self._conversations.get(session_id)

        # If not in memory, try to load from disk (handles server restarts/multiple workers)
        if conversation is None:
            conversation = self._load_conversation_from_disk(session_id)
            if conversation:
                self._conversations[session_id] = conversation

        if conversation is None:
            print(f"Warning: Conversation {session_id} not found in memory or on disk")
            return None

        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        conversation.messages.append(message)

        # Save to disk immediately to persist messages
        self._save_conversation_sync(conversation)

        return message

    async def end_conversation(self, session_id: str) -> bool:
        """End a conversation and save final state to disk."""
        # Try to get from memory first
        conversation = self._conversations.get(session_id)

        # If not in memory, try to load from disk
        if conversation is None:
            conversation = self._load_conversation_from_disk(session_id)

        if conversation is None:
            return False

        conversation.ended_at = datetime.utcnow().isoformat() + "Z"

        # Save final state to disk
        file_path = CONVERSATIONS_DIR / f"{session_id}.json"
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(conversation.model_dump(), indent=2))

            # Remove from memory cache
            if session_id in self._conversations:
                del self._conversations[session_id]
            return True
        except Exception as e:
            print(f"Error saving conversation {session_id}: {e}")
            return False

    def get_conversation(self, session_id: str) -> Optional[Conversation]:
        """Get an active conversation from memory."""
        return self._conversations.get(session_id)

    # ==================== Topics & Tasks Storage ====================

    async def load_topics_tasks(self) -> TopicsTasksData:
        """Load topics and tasks from JSON file."""
        try:
            async with aiofiles.open(TOPICS_TASKS_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                return TopicsTasksData(**data)
        except FileNotFoundError:
            return TopicsTasksData(topics=[], tasks=[])

    async def save_topics_tasks(self, data: TopicsTasksData) -> bool:
        """Save topics and tasks to JSON file."""
        try:
            async with aiofiles.open(TOPICS_TASKS_FILE, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data.model_dump(), indent=2))
            return True
        except Exception as e:
            print(f"Error saving topics/tasks: {e}")
            return False

    async def add_topic(self, text: str) -> Topic:
        """Add a new topic and return it."""
        data = await self.load_topics_tasks()
        new_id = max([t.id for t in data.topics], default=0) + 1
        topic = Topic(id=new_id, text=text)
        data.topics.append(topic)
        await self.save_topics_tasks(data)
        return topic

    async def update_topic(self, topic_id: int, text: str) -> Optional[Topic]:
        """Update a topic by ID."""
        data = await self.load_topics_tasks()
        for topic in data.topics:
            if topic.id == topic_id:
                topic.text = text
                await self.save_topics_tasks(data)
                return topic
        return None

    async def delete_topic(self, topic_id: int) -> bool:
        """Delete a topic by ID."""
        data = await self.load_topics_tasks()
        original_len = len(data.topics)
        data.topics = [t for t in data.topics if t.id != topic_id]
        if len(data.topics) < original_len:
            await self.save_topics_tasks(data)
            return True
        return False

    async def add_task(self, text: str) -> Task:
        """Add a new task and return it."""
        data = await self.load_topics_tasks()
        new_id = max([t.id for t in data.tasks], default=0) + 1
        task = Task(id=new_id, text=text)
        data.tasks.append(task)
        await self.save_topics_tasks(data)
        return task

    async def update_task(self, task_id: int, text: str) -> Optional[Task]:
        """Update a task by ID."""
        data = await self.load_topics_tasks()
        for task in data.tasks:
            if task.id == task_id:
                task.text = text
                await self.save_topics_tasks(data)
                return task
        return None

    async def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID."""
        data = await self.load_topics_tasks()
        original_len = len(data.tasks)
        data.tasks = [t for t in data.tasks if t.id != task_id]
        if len(data.tasks) < original_len:
            await self.save_topics_tasks(data)
            return True
        return False

    # ==================== Consent Storage ====================

    async def load_consent(self) -> ConsentData:
        """Load consent configuration from JSON file."""
        try:
            async with aiofiles.open(CONSENT_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                return ConsentData(**json.loads(content))
        except FileNotFoundError:
            return ConsentData(
                title="Research Participation Consent",
                version="1.0",
                content="By participating, you agree to have your conversation data collected for research purposes.",
                checkboxes=["I am 18 years or older", "I consent to data collection for research"]
            )

    async def save_consent(self, data: ConsentData) -> bool:
        """Save consent configuration to JSON file."""
        try:
            async with aiofiles.open(CONSENT_FILE, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data.model_dump(), indent=2))
            return True
        except Exception as e:
            print(f"Error saving consent: {e}")
            return False


# Global instance
storage_service = StorageService()
