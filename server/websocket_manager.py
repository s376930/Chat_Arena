import asyncio
from fastapi import WebSocket
from typing import Optional
import json
import uuid
from datetime import datetime, timedelta

from .models import UserSession, AISession


class WebSocketManager:
    """Manages WebSocket connections and user sessions."""

    def __init__(self):
        # Map user_id -> WebSocket connection
        self.connections: dict[str, WebSocket] = {}
        # Map user_id -> UserSession
        self.sessions: dict[str, UserSession] = {}
        # Map ai_id -> AISession (for tracking AI participants)
        self.ai_sessions: dict[str, AISession] = {}
        # Lock for thread-safe session operations
        self._session_lock = asyncio.Lock()

    def generate_user_id(self) -> str:
        """Generate a unique user ID."""
        return f"user_{uuid.uuid4().hex[:8]}"

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection and create a session."""
        await websocket.accept()
        user_id = self.generate_user_id()
        async with self._session_lock:
            self.connections[user_id] = websocket
            self.sessions[user_id] = UserSession(user_id=user_id)
        return user_id

    async def disconnect(self, user_id: str) -> Optional[str]:
        """
        Remove a user's connection and session.
        Returns the partner_id if the user was paired.
        """
        async with self._session_lock:
            partner_id = None

            if user_id in self.sessions:
                session = self.sessions[user_id]
                partner_id = session.partner_id
                del self.sessions[user_id]

            if user_id in self.connections:
                del self.connections[user_id]

            return partner_id

    def get_session(self, user_id: str) -> Optional[UserSession]:
        """Get a user's session."""
        return self.sessions.get(user_id)

    async def update_session(self, user_id: str, **kwargs) -> None:
        """Update a user's session with the given fields."""
        async with self._session_lock:
            if user_id in self.sessions:
                for key, value in kwargs.items():
                    if hasattr(self.sessions[user_id], key):
                        setattr(self.sessions[user_id], key, value)

    async def send_json(self, user_id: str, data: dict) -> bool:
        """Send JSON data to a specific user. Returns True if successful."""
        # Get connection reference while holding lock to prevent race condition
        ws = None
        async with self._session_lock:
            ws = self.connections.get(user_id)
        
        if ws:
            try:
                await ws.send_json(data)
                return True
            except (RuntimeError, ConnectionError) as e:
                return False
        return False

    async def send_to_partner(self, user_id: str, data: dict) -> bool:
        """Send JSON data to a user's partner. Returns True if successful."""
        # Hold lock during partner verification to prevent race conditions
        ws = None
        async with self._session_lock:
            session = self.get_session(user_id)
            if not session or not session.partner_id:
                return False

            partner_id = session.partner_id
            # Verify partner still considers us their partner (prevents cross-talk)
            partner_session = self.get_session(partner_id)
            if partner_session and partner_session.partner_id == user_id:
                ws = self.connections.get(partner_id)
            else:
                # For AI partners, check AI sessions instead
                ai_session = self.get_ai_session(partner_id)
                if ai_session and ai_session.partner_id == user_id:
                    ws = self.connections.get(partner_id)
        
        # Send outside lock to avoid holding it during async operation
        if ws:
            try:
                await ws.send_json(data)
                return True
            except (RuntimeError, ConnectionError) as e:
                return False
        return False

    async def is_paired(self, user_id: str) -> bool:
        """Check if a user is currently paired."""
        async with self._session_lock:
            session = self.sessions.get(user_id)
            return session is not None and session.paired

    async def get_partner_id(self, user_id: str) -> Optional[str]:
        """Get a user's partner ID."""
        async with self._session_lock:
            session = self.sessions.get(user_id)
            return session.partner_id if session else None

    async def clear_pairing(self, user_id: str) -> None:
        """Clear a user's pairing status."""
        async with self._session_lock:
            if user_id in self.sessions:
                session = self.sessions[user_id]
                session.paired = False
                session.partner_id = None
                session.session_id = None
                session.task = None
                session.is_ai_partner = False

    async def pair_users_atomic(
        self,
        user_id: str,
        partner_id: str,
        session_id: str,
        user_task: str,
        partner_task: str
    ) -> bool:
        """
        Atomically pair two users. Both sessions are updated together under a lock.
        Returns True if successful, False if either user is no longer available.
        """
        async with self._session_lock:
            # Verify both users still exist and are not already paired
            user_session = self.sessions.get(user_id)
            partner_session = self.sessions.get(partner_id)

            if not user_session or not partner_session:
                return False

            if user_session.paired or partner_session.paired:
                return False

            # Update both sessions atomically
            user_session.paired = True
            user_session.partner_id = partner_id
            user_session.session_id = session_id
            user_session.task = user_task
            user_session.is_ai_partner = False
            user_session.last_activity = datetime.now()

            partner_session.paired = True
            partner_session.partner_id = user_id
            partner_session.session_id = session_id
            partner_session.task = partner_task
            partner_session.is_ai_partner = False
            partner_session.last_activity = datetime.now()

            return True

    async def clear_pairing_atomic(self, user_id: str) -> Optional[str]:
        """
        Atomically clear a user's pairing status.
        Returns the partner_id if user was paired, None otherwise.
        """
        async with self._session_lock:
            session = self.sessions.get(user_id)
            if not session:
                return None

            partner_id = session.partner_id

            session.paired = False
            session.partner_id = None
            session.session_id = None
            session.task = None
            session.is_ai_partner = False

            return partner_id

    async def verify_pairing(self, user_id: str, partner_id: str) -> bool:
        """Verify that two users are mutually paired."""
        async with self._session_lock:
            user_session = self.sessions.get(user_id)
            partner_session = self.sessions.get(partner_id)

            if not user_session or not partner_session:
                return False

            return (
                user_session.paired and
                partner_session.paired and
                user_session.partner_id == partner_id and
                partner_session.partner_id == user_id
            )

    async def update_activity(self, user_id: str) -> None:
        """Update a user's last activity timestamp."""
        async with self._session_lock:
            if user_id in self.sessions:
                self.sessions[user_id].last_activity = datetime.now()

    async def get_inactive_users(self, timeout_seconds: int) -> list[str]:
        """Get list of user IDs that have been inactive for longer than timeout."""
        async with self._session_lock:
            inactive_users = []
            cutoff_time = datetime.now() - timedelta(seconds=timeout_seconds)

            for user_id, session in self.sessions.items():
                # Only check users who are paired (in an active conversation)
                if session.paired and session.last_activity:
                    if session.last_activity < cutoff_time:
                        inactive_users.append(user_id)

            return inactive_users

    # AI session management methods

    def create_ai_session(
        self,
        ai_id: str,
        partner_id: str,
        session_id: str,
        persona_id: str,
        persona_name: str,
        provider: str,
        model: str,
        topic: str,
        task: str,
    ) -> AISession:
        """Create and store an AI session."""
        ai_session = AISession(
            ai_id=ai_id,
            partner_id=partner_id,
            session_id=session_id,
            persona_id=persona_id,
            persona_name=persona_name,
            provider=provider,
            model=model,
            topic=topic,
            task=task,
            is_active=True,
            created_at=datetime.now().isoformat(),
        )
        self.ai_sessions[ai_id] = ai_session
        return ai_session

    def get_ai_session(self, ai_id: str) -> Optional[AISession]:
        """Get an AI session by ID."""
        return self.ai_sessions.get(ai_id)

    async def get_ai_session_by_partner(self, partner_id: str) -> Optional[AISession]:
        """Get the AI session for a given human partner."""
        async with self._session_lock:
            for ai_session in self.ai_sessions.values():
                if ai_session.partner_id == partner_id and ai_session.is_active:
                    return ai_session
            return None

    def update_ai_session(self, ai_id: str, **kwargs) -> None:
        """Update an AI session with the given fields."""
        if ai_id in self.ai_sessions:
            ai_session = self.ai_sessions[ai_id]
            for key, value in kwargs.items():
                if hasattr(ai_session, key):
                    setattr(ai_session, key, value)

    def remove_ai_session(self, ai_id: str) -> Optional[AISession]:
        """Remove and return an AI session."""
        return self.ai_sessions.pop(ai_id, None)

    def is_ai_participant(self, user_id: str) -> bool:
        """Check if a user ID belongs to an AI participant."""
        return user_id in self.ai_sessions or user_id.startswith("ai_")

    async def get_all_ai_sessions(self) -> list[AISession]:
        """Get all AI sessions."""
        async with self._session_lock:
            return list(self.ai_sessions.values())

    async def get_active_ai_count(self) -> int:
        """Get the number of active AI sessions."""
        async with self._session_lock:
            return sum(1 for s in self.ai_sessions.values() if s.is_active)


# Global instance
manager = WebSocketManager()
