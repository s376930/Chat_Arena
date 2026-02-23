import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional
from collections import deque

from .config import TOPICS_TASKS_FILE
from .models import Topic, Task, TopicsTasksData


class PairingService:
    """Manages user queue and pairing logic."""

    def __init__(self):
        # Queue of user_ids waiting to be paired
        self.queue: deque[str] = deque()
        # Cached topics and tasks
        self._topics: list[Topic] = []
        self._tasks: list[Task] = []
        self._load_topics_tasks()

        # Delay tracking for users after disconnect/reassign
        self._delayed_users: dict[str, datetime] = {}
        self._delay_seconds: int = 10  # Default delay

        # Lock for thread-safe queue and pairing operations
        self._lock = asyncio.Lock()

    def _load_topics_tasks(self) -> None:
        """Load topics and tasks from JSON file."""
        try:
            with open(TOPICS_TASKS_FILE, "r") as f:
                data = json.load(f)
                self._topics = [Topic(**t) for t in data.get("topics", [])]
                self._tasks = [Task(**t) for t in data.get("tasks", [])]
        except FileNotFoundError:
            self._topics = []
            self._tasks = []

    def reload_topics_tasks(self) -> None:
        """Reload topics and tasks from file (called after admin updates)."""
        self._load_topics_tasks()

    def get_topics(self) -> list[Topic]:
        """Get all topics."""
        return self._topics

    def get_tasks(self) -> list[Task]:
        """Get all tasks."""
        return self._tasks

    def add_to_queue(self, user_id: str) -> int:
        """
        Add a user to the pairing queue.
        Returns the user's position in the queue.
        """
        if user_id not in self.queue:
            self.queue.append(user_id)
        return list(self.queue).index(user_id) + 1

    def remove_from_queue(self, user_id: str) -> None:
        """Remove a user from the queue."""
        if user_id in self.queue:
            self.queue.remove(user_id)

    def get_queue_position(self, user_id: str) -> int:
        """Get a user's position in the queue (1-indexed)."""
        try:
            return list(self.queue).index(user_id) + 1
        except ValueError:
            return 0

    def try_pair(self, user_id: str) -> Optional[str]:
        """
        Try to pair a user with someone from the queue.
        Returns the partner's user_id if pairing successful, None otherwise.
        Respects delay timing for recently reassigned users.

        NOTE: This is the synchronous version. For thread-safe operations,
        use try_pair_atomic() instead.
        """
        # Skip if user is currently delayed
        if self.is_delayed(user_id):
            return None

        # Need at least 2 people in queue to pair
        if len(self.queue) < 2:
            return None

        # Remove the current user from queue first
        self.remove_from_queue(user_id)

        # Find a non-delayed partner from the queue
        partner_id = None
        checked_users = []

        while len(self.queue) > 0:
            candidate = self.queue.popleft()
            if not self.is_delayed(candidate):
                partner_id = candidate
                break
            checked_users.append(candidate)

        # Put checked users back in queue in same order (reverse before appendleft to maintain order)
        for u in reversed(checked_users):
            self.queue.appendleft(u)

        if partner_id:
            return partner_id

        # Put user back in queue if no partner found
        self.add_to_queue(user_id)
        return None

    async def try_pair_atomic(self, user_id: str) -> Optional[str]:
        """
        Thread-safe version of try_pair using asyncio.Lock.
        This prevents race conditions when multiple users try to pair simultaneously.
        """
        async with self._lock:
            return self.try_pair(user_id)

    async def add_to_queue_atomic(self, user_id: str) -> int:
        """Thread-safe version of add_to_queue."""
        async with self._lock:
            return self.add_to_queue(user_id)

    async def remove_from_queue_atomic(self, user_id: str) -> None:
        """Thread-safe version of remove_from_queue."""
        async with self._lock:
            self.remove_from_queue(user_id)

    async def get_queue_position_atomic(self, user_id: str) -> int:
        """Thread-safe version of get_queue_position."""
        async with self._lock:
            return self.get_queue_position(user_id)

    async def has_odd_user_waiting_atomic(self) -> bool:
        """Thread-safe version of has_odd_user_waiting."""
        async with self._lock:
            return self.has_odd_user_waiting()

    async def get_odd_user_atomic(self) -> Optional[str]:
        """Thread-safe version of get_odd_user."""
        async with self._lock:
            return self.get_odd_user()

    def get_random_topic(self) -> Optional[Topic]:
        """Get a random topic for a conversation."""
        if not self._topics:
            return None
        return random.choice(self._topics)

    def get_random_tasks(self, count: int = 2) -> list[Task]:
        """Get random tasks for participants (different tasks for each)."""
        if not self._tasks:
            return []
        if len(self._tasks) < count:
            return self._tasks.copy()
        return random.sample(self._tasks, count)

    def generate_session_id(self) -> str:
        """Generate a unique session ID for a conversation."""
        return uuid.uuid4().hex[:12]

    def queue_size(self) -> int:
        """Get the current queue size."""
        return len(self.queue)

    # Delay management methods

    def set_delay_seconds(self, seconds: int) -> None:
        """Set the delay duration in seconds."""
        self._delay_seconds = seconds

    def add_delay(self, user_id: str) -> None:
        """Add a delay for a user after disconnect/reassign."""
        self._delayed_users[user_id] = datetime.now() + timedelta(seconds=self._delay_seconds)

    def remove_delay(self, user_id: str) -> None:
        """Remove delay for a user."""
        self._delayed_users.pop(user_id, None)

    def is_delayed(self, user_id: str) -> bool:
        """Check if a user is currently delayed."""
        if user_id not in self._delayed_users:
            return False

        delay_until = self._delayed_users[user_id]
        if datetime.now() >= delay_until:
            # Delay has expired, remove it
            del self._delayed_users[user_id]
            return False

        return True

    def get_delay_remaining(self, user_id: str) -> int:
        """Get remaining delay time in seconds for a user."""
        if user_id not in self._delayed_users:
            return 0

        delay_until = self._delayed_users[user_id]
        remaining = (delay_until - datetime.now()).total_seconds()
        return max(0, int(remaining))

    def cleanup_expired_delays(self) -> None:
        """Remove all expired delays."""
        now = datetime.now()
        expired = [uid for uid, until in self._delayed_users.items() if now >= until]
        for uid in expired:
            del self._delayed_users[uid]

    # Odd user detection methods

    def has_odd_user_waiting(self) -> bool:
        """Check if there's a single user waiting who could be paired with AI."""
        self.cleanup_expired_delays()
        # Count non-delayed users in queue
        non_delayed = [u for u in self.queue if not self.is_delayed(u)]
        return len(non_delayed) == 1

    def get_odd_user(self) -> Optional[str]:
        """Get the single waiting user if there's only one non-delayed user."""
        self.cleanup_expired_delays()
        non_delayed = [u for u in self.queue if not self.is_delayed(u)]
        if len(non_delayed) == 1:
            return non_delayed[0]
        return None

    def get_waiting_users(self) -> list[str]:
        """Get list of all users currently in queue."""
        return list(self.queue)

    def get_non_delayed_waiting_users(self) -> list[str]:
        """Get list of non-delayed users currently in queue."""
        self.cleanup_expired_delays()
        return [u for u in self.queue if not self.is_delayed(u)]


# Global instance
pairing_service = PairingService()
