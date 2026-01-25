from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    JOIN = "join"
    MESSAGE = "message"
    REASSIGN = "reassign"
    DISCONNECT = "disconnect"
    WAITING = "waiting"
    PAIRED = "paired"
    PARTNER_MESSAGE = "partner_message"
    PARTNER_LEFT = "partner_left"
    INACTIVITY_KICK = "inactivity_kick"
    ERROR = "error"


# Client -> Server messages
class JoinMessage(BaseModel):
    type: str = "join"
    consent: bool


class ChatMessage(BaseModel):
    type: str = "message"
    think: str
    speech: str


class ReassignMessage(BaseModel):
    type: str = "reassign"


class DisconnectMessage(BaseModel):
    type: str = "disconnect"


# Server -> Client messages
class WaitingResponse(BaseModel):
    type: str = "waiting"
    position: int


class PairedResponse(BaseModel):
    type: str = "paired"
    topic: str
    task: str
    session_id: str


class PartnerMessageResponse(BaseModel):
    type: str = "partner_message"
    content: str
    timestamp: str


class PartnerLeftResponse(BaseModel):
    type: str = "partner_left"


class ErrorResponse(BaseModel):
    type: str = "error"
    message: str


# Data models
class Topic(BaseModel):
    id: int
    text: str


class Task(BaseModel):
    id: int
    text: str


class TopicsTasksData(BaseModel):
    topics: list[Topic]
    tasks: list[Task]


class ConsentCheckbox(BaseModel):
    text: str


class ConsentData(BaseModel):
    title: str
    version: str
    content: str
    checkboxes: list[str]


# Conversation storage (HuggingFace format)
class Participant(BaseModel):
    user_id: str
    task: str


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str


class Conversation(BaseModel):
    session_id: str
    topic: str
    participants: list[Participant]
    messages: list[ConversationMessage]
    started_at: str
    ended_at: Optional[str] = None


# User session
class UserSession(BaseModel):
    user_id: str
    consented: bool = False
    paired: bool = False
    partner_id: Optional[str] = None
    session_id: Optional[str] = None
    task: Optional[str] = None
    is_ai_partner: bool = False  # True if partner is an AI
    last_activity: Optional[datetime] = None  # Track last activity for inactivity timeout


# AI session tracking
class AISession(BaseModel):
    ai_id: str
    partner_id: str
    session_id: str
    persona_id: str
    persona_name: str
    provider: str
    model: str
    topic: str
    task: str
    is_active: bool = True
    created_at: str


# Admin API models
class TopicCreate(BaseModel):
    text: str


class TopicUpdate(BaseModel):
    text: str


class TaskCreate(BaseModel):
    text: str


class TaskUpdate(BaseModel):
    text: str
