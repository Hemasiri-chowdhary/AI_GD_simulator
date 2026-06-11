"""Pydantic schemas for API validation."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class MessageType(str, Enum):
    USER = "user"
    BOT = "bot"
    MODERATOR = "moderator"
    SYSTEM = "system"


class SessionPhase(str, Enum):
    INTRO = "intro"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Persona Schemas
class PersonaInfo(BaseModel):
    id: str
    name: str
    role: str
    avatar_color: str
    is_speaking: bool = False


# Topic Schemas
class TopicInfo(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    difficulty: str = "medium"


class CategoryInfo(BaseModel):
    id: str
    name: str
    icon: str
    topics_count: int


# Session Schemas
class SessionCreate(BaseModel):
    category: str
    topic: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    topic: str
    category: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    
    class Config:
        from_attributes = True


# Message Schemas
class MessageCreate(BaseModel):
    content: str
    speaker_id: str = "user"
    speaker_name: str = "You"


class MessageResponse(BaseModel):
    id: int
    session_id: str
    speaker_id: str
    speaker_name: str
    content: str
    message_type: str
    persona_role: Optional[str] = None
    session_phase: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


# Feedback Schemas
class FeedbackResponse(BaseModel):
    session_id: str
    confidence_score: Optional[float] = None
    clarity_score: Optional[float] = None
    grammar_score: Optional[float] = None
    argument_score: Optional[float] = None
    participation_score: Optional[float] = None
    leadership_score: Optional[float] = None
    overall_score: Optional[float] = None
    strengths: Optional[List[str]] = None
    improvements: Optional[List[str]] = None
    vocabulary_suggestions: Optional[List[str]] = None
    detailed_analysis: Optional[str] = None
    
    class Config:
        from_attributes = True


# WebSocket Message Schemas
class WebSocketMessage(BaseModel):
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None


class WSUserMessage(BaseModel):
    type: Literal["user_message"] = "user_message"
    content: str


class WSJoinSession(BaseModel):
    type: Literal["user_join_session"] = "user_join_session"
    category: str
    topic: Optional[str] = None
    user_key: Optional[str] = None


class WSSelectCategory(BaseModel):
    type: Literal["user_select_category"] = "user_select_category"
    category: str


class WSEndSession(BaseModel):
    type: Literal["user_end_session"] = "user_end_session"


# Session State
class SessionState(BaseModel):
    session_id: str
    topic: str
    category: str
    phase: SessionPhase = SessionPhase.INTRO
    participants: List[PersonaInfo]
    current_speaker: Optional[str] = None
    messages_count: int = 0
    time_remaining: int = 900  # 15 minutes in seconds
    is_user_turn: bool = False
    last_user_message_time: Optional[datetime] = None
