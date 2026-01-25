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

    def generate_user_id(self) -> str:
        """Generate a unique user ID."""
        return f"user_{uuid.uuid4().hex[:8]}"

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection and create a session."""
        await websocket.accept()
        user_id = self.generate_user_id()
        self.connections[user_id] = websocket
        self.sessions[user_id] = UserSession(user_id=user_id)
        return user_id

    def disconnect(self, user_id: str) -> Optional[str]:
        """
        Remove a user's connection and session.
        Returns the partner_id if the user was paired.
        """
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

    def update_session(self, user_id: str, **kwargs) -> None:
        """Update a user's session with the given fields."""
        if user_id in self.sessions:
            for key, value in kwargs.items():
                if hasattr(self.sessions[user_id], key):
                    setattr(self.sessions[user_id], key, value)

    async def send_json(self, user_id: str, data: dict) -> bool:
        """Send JSON data to a specific user. Returns True if successful."""
        if user_id in self.connections:
            try:
                await self.connections[user_id].send_json(data)
                return True
            except Exception:
                return False
        return False

    async def send_to_partner(self, user_id: str, data: dict) -> bool:
        """Send JSON data to a user's partner. Returns True if successful."""
        session = self.get_session(user_id)
        if session and session.partner_id:
            return await self.send_json(session.partner_id, data)
        return False

    def is_paired(self, user_id: str) -> bool:
        """Check if a user is currently paired."""
        session = self.get_session(user_id)
        return session is not None and session.paired

    def get_partner_id(self, user_id: str) -> Optional[str]:
        """Get a user's partner ID."""
        session = self.get_session(user_id)
        return session.partner_id if session else None

    def clear_pairing(self, user_id: str) -> None:
        """Clear a user's pairing status."""
        self.update_session(
            user_id,
            paired=False,
            partner_id=None,
            session_id=None,
            task=None,
            is_ai_partner=False
        )

    def update_activity(self, user_id: str) -> None:
        """Update a user's last activity timestamp."""
        if user_id in self.sessions:
            self.sessions[user_id].last_activity = datetime.now()

    def get_inactive_users(self, timeout_seconds: int) -> list[str]:
        """Get list of user IDs that have been inactive for longer than timeout."""
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

    def get_ai_session_by_partner(self, partner_id: str) -> Optional[AISession]:
        """Get the AI session for a given human partner."""
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

    def get_all_ai_sessions(self) -> list[AISession]:
        """Get all AI sessions."""
        return list(self.ai_sessions.values())

    def get_active_ai_count(self) -> int:
        """Get the number of active AI sessions."""
        return sum(1 for s in self.ai_sessions.values() if s.is_active)


# Global instance
manager = WebSocketManager()
