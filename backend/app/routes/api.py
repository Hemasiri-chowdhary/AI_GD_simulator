"""REST API routes for non-realtime operations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import Session, Feedback, SessionResponse, FeedbackResponse, CategoryInfo
from app.services.topic_service import TopicService

router = APIRouter()
topic_service = TopicService()


@router.get("/categories", response_model=List[CategoryInfo])
async def get_categories():
    """Get all available discussion categories."""
    return topic_service.get_categories()


@router.get("/topics/{category}")
async def get_topics_by_category(category: str):
    """Get all topics for a specific category."""
    topics = topic_service.get_topics_by_category(category)
    if not topics:
        raise HTTPException(status_code=404, detail="Category not found")
    return topics


@router.get("/topic/random/{category}")
async def get_random_topic(category: str, user_key: str = "global"):
    """Get a random topic from a category."""
    topic = topic_service.get_random_topic(category, user_key=user_key)
    if not topic:
        raise HTTPException(status_code=404, detail="No topics found for category")
    return topic


@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(db: AsyncSession = Depends(get_db)):
    """Get all sessions."""
    result = await db.execute(
        select(Session).order_by(Session.started_at.desc())
    )
    sessions = result.scalars().all()
    return sessions


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/feedback", response_model=FeedbackResponse)
async def get_session_feedback(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get feedback for a specific session."""
    result = await db.execute(
        select(Feedback).where(Feedback.session_id == session_id)
    )
    feedback = result.scalar_one_or_none()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback


@router.get("/sessions/{session_id}/transcript")
async def get_session_transcript(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get the full transcript for a session."""
    from app.models import Message
    
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages_result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.timestamp)
    )
    messages = messages_result.scalars().all()
    
    return {
        "session_id": session_id,
        "topic": session.topic,
        "category": session.category,
        "messages": [
            {
                "speaker_name": msg.speaker_name,
                "content": msg.content,
                "message_type": msg.message_type,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]
    }
