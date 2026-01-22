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

    def create_conversation(
        self,
        session_id: str,
        topic: str,
        participants: list[dict]
    ) -> Conversation:
        """Create a new conversation in memory."""
        conversation = Conversation(
            session_id=session_id,
            topic=topic,
            participants=[Participant(**p) for p in participants],
            messages=[],
            started_at=datetime.utcnow().isoformat() + "Z"
        )
        self._conversations[session_id] = conversation
        return conversation

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> Optional[ConversationMessage]:
        """Add a message to a conversation."""
        if session_id not in self._conversations:
            return None

        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        self._conversations[session_id].messages.append(message)
        return message

    async def end_conversation(self, session_id: str) -> bool:
        """End a conversation and save to disk."""
        if session_id not in self._conversations:
            return False

        conversation = self._conversations[session_id]
        conversation.ended_at = datetime.utcnow().isoformat() + "Z"

        # Save to disk
        file_path = CONVERSATIONS_DIR / f"{session_id}.json"
        try:
            async with aiofiles.open(file_path, "w") as f:
                await f.write(json.dumps(conversation.model_dump(), indent=2))

            # Remove from memory
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
            async with aiofiles.open(TOPICS_TASKS_FILE, "r") as f:
                content = await f.read()
                data = json.loads(content)
                return TopicsTasksData(**data)
        except FileNotFoundError:
            return TopicsTasksData(topics=[], tasks=[])

    async def save_topics_tasks(self, data: TopicsTasksData) -> bool:
        """Save topics and tasks to JSON file."""
        try:
            async with aiofiles.open(TOPICS_TASKS_FILE, "w") as f:
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
            async with aiofiles.open(CONSENT_FILE, "r") as f:
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
            async with aiofiles.open(CONSENT_FILE, "w") as f:
                await f.write(json.dumps(data.model_dump(), indent=2))
            return True
        except Exception as e:
            print(f"Error saving consent: {e}")
            return False


# Global instance
storage_service = StorageService()
