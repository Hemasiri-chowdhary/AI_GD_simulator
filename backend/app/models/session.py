"""SQLAlchemy database models."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base


class Session(Base):
    """GD Session model."""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    topic = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)
    status = Column(String(20), default="active")  # active, completed, cancelled
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="session", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session {self.id}: {self.topic[:30]}...>"


class Message(Base):
    """Individual message in a GD session."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    speaker_id = Column(String(20), nullable=False)  # user, p1, p2, etc.
    speaker_name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), nullable=False)  # user, bot, moderator
    persona_role = Column(String(50), nullable=True)
    session_phase = Column(String(20), default="discussion")  # intro, discussion, conclusion
    timestamp = Column(DateTime, server_default=func.now())
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    
    def __repr__(self):
        return f"<Message {self.id}: {self.speaker_name}>"


class Feedback(Base):
    """Post-session feedback report."""
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, unique=True)
    
    # Scores (0-100)
    confidence_score = Column(Float, nullable=True)
    clarity_score = Column(Float, nullable=True)
    grammar_score = Column(Float, nullable=True)
    argument_score = Column(Float, nullable=True)
    participation_score = Column(Float, nullable=True)
    leadership_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    
    # Detailed feedback
    strengths = Column(JSON, nullable=True)
    improvements = Column(JSON, nullable=True)
    vocabulary_suggestions = Column(JSON, nullable=True)
    detailed_analysis = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    session = relationship("Session", back_populates="feedback")
    
    def __repr__(self):
        return f"<Feedback for Session {self.session_id}>"
