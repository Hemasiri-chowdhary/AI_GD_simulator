"""Tests for Pydantic schemas."""
import pytest
from datetime import datetime
from app.models.schemas import (
    MessageType,
    SessionPhase,
    SessionStatus,
    PersonaInfo,
    TopicInfo,
    CategoryInfo,
    SessionCreate,
    SessionResponse,
    MessageCreate,
    MessageResponse,
    FeedbackResponse,
    WebSocketMessage,
    WSUserMessage,
    WSJoinSession,
    WSEndSession,
    SessionState,
)


class TestEnums:
    """Test enum definitions."""

    def test_message_types(self):
        assert MessageType.USER == "user"
        assert MessageType.BOT == "bot"
        assert MessageType.MODERATOR == "moderator"
        assert MessageType.SYSTEM == "system"

    def test_session_phases(self):
        assert SessionPhase.INTRO == "intro"
        assert SessionPhase.DISCUSSION == "discussion"
        assert SessionPhase.CONCLUSION == "conclusion"

    def test_session_statuses(self):
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.COMPLETED == "completed"
        assert SessionStatus.CANCELLED == "cancelled"


class TestPersonaInfo:
    def test_creation(self):
        p = PersonaInfo(id="p1", name="Moderator", role="mod", avatar_color="blue")
        assert p.id == "p1"
        assert p.is_speaking is False

    def test_speaking_flag(self):
        p = PersonaInfo(id="p1", name="X", role="Y", avatar_color="Z", is_speaking=True)
        assert p.is_speaking is True


class TestTopicInfo:
    def test_defaults(self):
        t = TopicInfo(id="t1", title="AI Impact")
        assert t.difficulty == "medium"
        assert t.description is None


class TestCategoryInfo:
    def test_creation(self):
        c = CategoryInfo(id="tech", name="Technology", icon="💻", topics_count=10)
        assert c.topics_count == 10


class TestSessionCreate:
    def test_minimal(self):
        sc = SessionCreate(category="Technology")
        assert sc.topic is None

    def test_with_topic(self):
        sc = SessionCreate(category="Tech", topic="AI Ethics")
        assert sc.topic == "AI Ethics"


class TestMessageCreate:
    def test_defaults(self):
        mc = MessageCreate(content="Hello")
        assert mc.speaker_id == "user"
        assert mc.speaker_name == "You"


class TestWebSocketMessage:
    def test_defaults(self):
        wm = WebSocketMessage(type="ping")
        assert wm.payload == {}

    def test_with_payload(self):
        wm = WebSocketMessage(type="test", payload={"key": "value"})
        assert wm.payload["key"] == "value"


class TestWSUserMessage:
    def test_literal_type(self):
        m = WSUserMessage(content="Hello world")
        assert m.type == "user_message"


class TestWSJoinSession:
    def test_defaults(self):
        j = WSJoinSession(category="Tech")
        assert j.topic is None
        assert j.user_key is None


class TestSessionState:
    def test_defaults(self):
        state = SessionState(
            session_id="abc",
            topic="AI",
            category="Tech",
            participants=[],
        )
        assert state.phase == SessionPhase.INTRO
        assert state.messages_count == 0
        assert state.time_remaining == 900
        assert state.is_user_turn is False


class TestFeedbackResponse:
    def test_optional_fields(self):
        f = FeedbackResponse(session_id="abc")
        assert f.confidence_score is None
        assert f.strengths is None
