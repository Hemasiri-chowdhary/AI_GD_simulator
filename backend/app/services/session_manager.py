"""Session Manager - Manages GD sessions and coordinates all services."""
import logging
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, List, Any

from fastapi import WebSocket

from app.services.ollama_client import OllamaClient
from app.services.topic_service import TopicService
from app.services.persona_manager import PersonaManager
from app.services.orchestrator import Orchestrator
from app.services.feedback_service import FeedbackService
from app.database import async_session
from app.models import Session, Message, Feedback
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SessionState(Enum):
    LOBBY = "lobby"
    PREP = "prep"
    ACTIVE = "active"
    ENDING = "ending"
    ENDED = "ended"


@dataclass
class SessionController:
    """Central session controller with state, tasks, and transcript."""

    session_id: str
    websocket: WebSocket
    topic: str
    category: str
    duration_seconds: int

    session_state: SessionState = SessionState.LOBBY
    start_timestamp: Optional[datetime] = None
    time_remaining: int = 0
    timer_task: Optional[asyncio.Task] = None
    orchestrator_task: Optional[asyncio.Task] = None
    active_speaker_id: Optional[str] = None
    transcript_full: List[Dict[str, Any]] = field(default_factory=list)
    transcript_context_last15: List[Dict[str, Any]] = field(default_factory=list)
    performance_report: Optional[Dict[str, Any]] = None
    end_reason: Optional[str] = None

    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_invitation_count: int = 0
    last_suggestion_time: float = 0.0
    _message_buffer: List[Dict[str, Any]] = field(default_factory=list)
    ws_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    speaker_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    end_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_timer_tick_at: Optional[datetime] = None
    is_locked: bool = False

    async def safe_send_json(self, data: dict) -> bool:
        """Safely send JSON through WebSocket with lock and state check."""
        if self.session_state in (SessionState.ENDED,):
            return False
        try:
            async with self.ws_lock:
                if self.session_state != SessionState.ENDED:
                    await self.websocket.send_json(data)
                    return True
        except Exception as e:
            logger.debug(f"Failed to send to websocket: {e}")
        return False

    def append_message(self, message: Dict[str, Any]) -> None:
        """Append message to transcript buffers."""
        self.messages.append(message)
        self.transcript_full.append(message)
        self.transcript_context_last15.append(message)
        if len(self.transcript_context_last15) > settings.max_context_messages:
            self.transcript_context_last15 = self.transcript_context_last15[-settings.max_context_messages:]


SESSION_REGISTRY: Dict[str, SessionController] = {}
SESSION_BY_CONNECTION: Dict[int, str] = {}


class SessionManager:
    """Manages all active GD sessions."""

    def __init__(self):
        self.ollama = OllamaClient()
        self.topic_service = TopicService()
        self.persona_manager = PersonaManager()
        self.orchestrator = Orchestrator()
        self.feedback_service = FeedbackService()

        self.connections: Dict[int, WebSocket] = {}
        self.session_by_connection = SESSION_BY_CONNECTION
        self.sessions = SESSION_REGISTRY

    async def register_connection(self, websocket: WebSocket, connection_id: int):
        """Register a new WebSocket connection."""
        self.connections[connection_id] = websocket
        logger.info(f"Registered connection: {connection_id}")

    async def unregister_connection(self, connection_id: int):
        """Unregister a WebSocket connection and clean up session."""
        session_id = self.session_by_connection.pop(connection_id, None)
        if session_id:
            session = self.sessions.get(session_id)
            if session and session.session_state not in (SessionState.ENDING, SessionState.ENDED):
                await self._end_session(session, end_reason="disconnect")
            self.sessions.pop(session_id, None)
            self.orchestrator.cleanup_session(session_id)

        self.connections.pop(connection_id, None)
        logger.info(f"Unregistered connection: {connection_id}")

    async def create_session(
        self,
        websocket: WebSocket,
        connection_id: int,
        category: str,
        topic: Optional[str] = None,
        duration_minutes: int = 10,
        user_key: Optional[str] = None
    ) -> str:
        """Create a new GD session."""

        session_id = str(uuid.uuid4())
        topic_memory_key = user_key or f"conn:{connection_id}"

        if not topic:
            topic_info = self.topic_service.get_random_topic(category, user_key=topic_memory_key)
            topic = topic_info.title if topic_info else f"General discussion about {category}"
        else:
            self.topic_service.record_manual_topic_usage(category, topic, user_key=topic_memory_key)

        duration_minutes = settings.session_duration_minutes
        duration_seconds = duration_minutes * 60

        session = SessionController(
            session_id=session_id,
            websocket=websocket,
            topic=topic,
            category=category,
            duration_seconds=duration_seconds,
            time_remaining=duration_seconds
        )

        self.sessions[session_id] = session
        self.session_by_connection[connection_id] = session_id

        self.orchestrator.init_session(session_id, duration_seconds)

        await self._save_session_to_db(session)

        await session.safe_send_json({
            "type": "session_started",
            "payload": {
                "session_id": session_id,
                "topic": topic,
                "category": category,
                "participants": self.persona_manager.get_participant_info(),
                "duration_seconds": duration_seconds,
                "preparation_time": settings.preparation_time_seconds
            }
        })

        asyncio.create_task(self._start_session_flow(session))

        return session_id

    async def _start_session_flow(self, session: SessionController):
        """Start the GD session with preparation, moderator opening, then leader opening."""
        logger.info(f"🎬 Starting session flow for {session.session_id}")

        if session.session_state != SessionState.LOBBY:
            return

        await asyncio.sleep(0.5)

        session.session_state = SessionState.PREP
        prep_time = settings.preparation_time_seconds

        await session.safe_send_json({
            "type": "prep_phase_start",
            "payload": {
                "duration_seconds": prep_time,
                "message": "Take a moment to think before speaking."
            }
        })

        for remaining in range(prep_time, 0, -1):
            if session.session_state != SessionState.PREP:
                return

            await session.safe_send_json({
                "type": "prep_timer_update",
                "payload": {
                    "seconds_remaining": remaining,
                    "formatted_time": f"0:{remaining:02d}"
                }
            })
            await asyncio.sleep(1)

        if session.session_state != SessionState.PREP:
            return

        await session.safe_send_json({
            "type": "prep_phase_end",
            "payload": {"message": "Discussion is starting now!"}
        })

        moderator = self.persona_manager.get_moderator()

        session.session_state = SessionState.ACTIVE
        session.start_timestamp = datetime.now(timezone.utc)
        session.time_remaining = session.duration_seconds
        self.orchestrator.mark_discussion_start(session.session_id)

        await self._send_typing_indicator(session, "p1", True)
        await session.safe_send_json({
            "type": "active_speaker_update",
            "payload": {"speaker_id": "p1", "is_active": True}
        })

        intro_prompt = f"""You are opening a GD right after preparation time has ended.

Topic: "{session.topic}"
Category: {session.category}

Give a short, professional moderator opening in exactly 2 concise sentences:
1) Welcome and state the topic clearly.
2) Invite the Leader to begin immediately.

Do not add filler text."""

        intro = await self._safe_generate(
            prompt=intro_prompt,
            system_prompt=moderator.system_prompt,
            temperature=0.6,
            max_tokens=120
        )

        await self._send_typing_indicator(session, "p1", False)
        await self._send_bot_message(session, "p1", moderator.name, intro, "intro")
        self.orchestrator.record_message(session.session_id, "p1", intro)

        await asyncio.sleep(0.2)

        leader = self.persona_manager.get_persona("p2")
        if leader and session.session_state == SessionState.ACTIVE:
            await self._send_typing_indicator(session, "p2", True)
            await session.safe_send_json({
                "type": "active_speaker_update",
                "payload": {"speaker_id": "p2", "is_active": True}
            })

            leader_prompt = f"""The moderator has just opened the discussion on: "{session.topic}"

Recent context: {self._get_recent_context(session)}

As the Leader, open the discussion by:
1. Briefly acknowledging the topic's importance
2. Presenting 1-2 clear dimensions to explore
3. Introducing a fresh angle (no repetition)

Keep it to 2-3 sentences. Be professional and confident."""

            leader_response = await self._safe_generate(
                prompt=leader_prompt,
                system_prompt=leader.system_prompt,
                context_messages=session.messages[-5:],
                temperature=0.7,
                max_tokens=150
            )

            await self._send_typing_indicator(session, "p2", False)
            await self._send_bot_message(session, "p2", leader.name, leader_response, "discussion")
            self.orchestrator.record_message(session.session_id, "p2", leader_response)

        session.timer_task = asyncio.create_task(self._run_timer(session))
        session.orchestrator_task = asyncio.create_task(self._continue_discussion(session))

    async def _continue_discussion(self, session: SessionController):
        """Continue the discussion with bot turns."""
        logger.info(f"🔄 Starting orchestrator loop for session {session.session_id}")

        while session.session_state == SessionState.ACTIVE:
            # Adaptive delay: shorter early on for responsiveness, longer later
            time_remaining = self.orchestrator.get_time_remaining(session.session_id)
            tick_delay = 1.5 if time_remaining > session.duration_seconds * 0.7 else 2.0
            await asyncio.sleep(tick_delay)

            if session.session_state != SessionState.ACTIVE:
                break

            time_remaining = self.orchestrator.get_time_remaining(session.session_id)
            phase = self.orchestrator.update_session_phase(session.session_id, time_remaining)

            if time_remaining <= 0:
                asyncio.create_task(self._end_session(session, end_reason="timer_zero"))
                break

            if (
                self.orchestrator.should_invite_user(session.session_id)
                and session.user_invitation_count < settings.max_user_invitations
            ):
                moderator = self.persona_manager.get_moderator()
                invite = self.orchestrator.get_concise_user_invite()
                await self._send_bot_message(session, "p1", moderator.name, invite, "discussion")
                session.user_invitation_count += 1
                self.orchestrator.reset_user_invitation_timer(session.session_id)
                await asyncio.sleep(10)
                continue

            last_message = session.messages[-1]["content"] if session.messages else ""
            available = ["p2", "p3", "p4", "p5"]

            next_speaker_id, reason = self.orchestrator.select_next_speaker(
                session.session_id,
                last_message,
                available
            )

            if next_speaker_id == "p1":
                if reason == "loop_breaker_moderator":
                    await self._moderator_loop_breaker_intervention(session)
                continue

            persona = self.persona_manager.get_persona(next_speaker_id)
            if not persona:
                continue

            async with session.speaker_lock:
                if session.session_state != SessionState.ACTIVE or session.is_locked:
                    break

                await self._send_typing_indicator(session, next_speaker_id, True)
                await asyncio.sleep(await self.orchestrator.get_thinking_delay())

                if session.session_state != SessionState.ACTIVE or session.is_locked:
                    break

                context_prompt = self.persona_manager.build_context_prompt(
                    persona,
                    session.topic,
                    phase.value
                )

                response_prompt = f"""Continue the discussion on: "{session.topic}"

Recent context: {self._get_recent_context(session)}

Important anti-repeat constraints:
- Do not repeat arguments already stated in recent context.
- Add one new example, counterpoint, or implementation angle.
- Keep the discussion evolving naturally.

Respond naturally in 2-3 sentences. Build on previous points or introduce new perspectives."""

                response = await self._safe_generate(
                    prompt=response_prompt,
                    system_prompt=context_prompt,
                    context_messages=session.messages[-settings.max_context_messages:],
                    temperature=0.75,
                    max_tokens=150
                )

                await self._send_typing_indicator(session, next_speaker_id, False)

                if session.session_state != SessionState.ACTIVE or session.is_locked:
                    break

                await self._send_bot_message(session, next_speaker_id, persona.name, response, phase.value)
                self.orchestrator.record_message(session.session_id, next_speaker_id, response)

    def _get_recent_context(self, session: SessionController) -> str:
        """Get recent messages as context string (concise to reduce LLM tokens)."""
        recent = session.messages[-5:] if len(session.messages) >= 5 else session.messages
        return " | ".join([f"{m['speaker_name']}: {m['content'][:100]}" for m in recent])

    async def _moderator_loop_breaker_intervention(self, session: SessionController) -> None:
        """Moderator redirects discussion when repetition loop is detected."""
        if session.session_state != SessionState.ACTIVE:
            return

        moderator = self.persona_manager.get_moderator()
        pivot_question = self.orchestrator.get_loop_breaker_question(session.topic)

        redirect_prompt = f"""The discussion is becoming repetitive on: "{session.topic}"

Recent context: {self._get_recent_context(session)}

Give a concise moderator intervention in 2 sentences:
1) Acknowledge repeated points and ask this new guiding question: "{pivot_question}"
2) Invite either Priya (Analyst) or Rahul (Opposer) to respond next for a fresh perspective.

Keep neutral, professional, and short."""

        await self._send_typing_indicator(session, "p1", True)
        redirect_message = await self._safe_generate(
            prompt=redirect_prompt,
            system_prompt=moderator.system_prompt,
            context_messages=session.messages[-settings.max_context_messages:],
            temperature=0.6,
            max_tokens=140
        )
        await self._send_typing_indicator(session, "p1", False)

        await self._send_bot_message(session, "p1", moderator.name, redirect_message, "discussion")
        self.orchestrator.record_message(session.session_id, "p1", redirect_message)
        self.orchestrator.consume_loop_breaker(session.session_id)

        forced_speaker_id = "p3" if session.messages and len(session.messages) % 2 == 0 else "p4"
        forced_persona = self.persona_manager.get_persona(forced_speaker_id)
        if not forced_persona or session.session_state != SessionState.ACTIVE:
            return

        await self._send_typing_indicator(session, forced_speaker_id, True)
        await asyncio.sleep(await self.orchestrator.get_thinking_delay())

        forced_prompt = f"""Moderator asked a new question to break repetition:
"{pivot_question}"

Topic: "{session.topic}"
Recent context: {self._get_recent_context(session)}

Respond with a fresh angle not already stated. Use 2-3 concise sentences."""

        forced_context = self.persona_manager.build_context_prompt(
            forced_persona,
            session.topic,
            self.orchestrator.get_session_phase(session.session_id).value
        )

        forced_response = await self._safe_generate(
            prompt=forced_prompt,
            system_prompt=forced_context,
            context_messages=session.messages[-settings.max_context_messages:],
            temperature=0.75,
            max_tokens=150
        )

        await self._send_typing_indicator(session, forced_speaker_id, False)

        if session.session_state == SessionState.ACTIVE:
            await self._send_bot_message(session, forced_speaker_id, forced_persona.name, forced_response, "discussion")
            self.orchestrator.record_message(session.session_id, forced_speaker_id, forced_response)

    async def process_user_message(self, connection_id: int, content: str):
        """Process a message from the user."""
        session_id = self.session_by_connection.get(connection_id)
        session = self.sessions.get(session_id) if session_id else None

        if not session or session.session_state != SessionState.ACTIVE:
            return

        # Input validation: enforce max message length
        max_len = settings.max_message_length
        if len(content) > max_len:
            content = content[:max_len]
            logger.warning(f"User message truncated to {max_len} chars for session {session_id}")

        message = {
            "speaker_id": "user",
            "speaker_name": "You",
            "content": content,
            "message_type": "user",
            "session_phase": self.orchestrator.get_session_phase(session.session_id).value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        session.append_message(message)

        await self._save_message_to_db(session.session_id, message)

        await session.safe_send_json({
            "type": "user_message_received",
            "payload": message
        })

        self.orchestrator.record_message(session.session_id, "user", content)

        asyncio.create_task(self._generate_user_suggestions(session, content))
        asyncio.create_task(self._respond_to_user(session, content))

    async def _generate_user_suggestions(self, session: SessionController, user_message: str):
        """Generate communication improvement suggestions for the user's message (debounced)."""
        import time as _time
        now = _time.monotonic()
        # Skip if last suggestion was generated less than 10 seconds ago
        if now - session.last_suggestion_time < 10.0:
            return
        session.last_suggestion_time = now

        try:
            suggestion_prompt = f"""You are a friendly communication coach helping students improve their Group Discussion skills.

Analyze this student's speech during a GD on "{session.topic}":

"{user_message}"

Provide EXACTLY 3 short, encouraging improvement tips. Focus on:
- Clarity and structure of argument
- Vocabulary enhancement (suggest better words)
- Grammar or filler word reduction (um, like, you know)
- Confidence and tone
- How to make points more impactful

Format: Return ONLY a JSON array with 3 strings, like:
["Tip 1 here", "Tip 2 here", "Tip 3 here"]

Keep each tip under 80 characters. Be motivating, not critical."""

            response = await self._safe_generate(
                prompt=suggestion_prompt,
                system_prompt="You are a supportive communication coach. Respond only with a valid JSON array of 3 improvement tips.",
                temperature=0.7,
                max_tokens=200
            )

            suggestions = self._parse_suggestions(response)

            if suggestions:
                await session.safe_send_json({
                    "type": "user_suggestions_update",
                    "payload": {
                        "suggestions": suggestions,
                        "message_preview": user_message[:50] + "..." if len(user_message) > 50 else user_message
                    }
                })
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")

    def _parse_suggestions(self, response: str) -> List[str]:
        """Parse suggestions from Ollama response."""
        import json
        import re

        try:
            suggestions = json.loads(response.strip())
            if isinstance(suggestions, list) and len(suggestions) >= 1:
                return suggestions[:3]
        except Exception:
            pass

        try:
            match = re.search(r"\[.*?\]", response, re.DOTALL)
            if match:
                suggestions = json.loads(match.group())
                if isinstance(suggestions, list) and len(suggestions) >= 1:
                    return suggestions[:3]
        except Exception:
            pass

        lines = [line.strip() for line in response.split("\n") if line.strip()]
        suggestions: List[str] = []
        for line in lines:
            cleaned = re.sub(r"^[\d]+[\.)]\s*", "", line)
            cleaned = cleaned.strip("\"'\"")
            if cleaned and len(cleaned) > 10:
                suggestions.append(cleaned)

        return suggestions[:3] if suggestions else [
            "Try to structure your points more clearly",
            "Use specific examples to support your argument",
            "Vary your vocabulary for impact"
        ]

    async def _respond_to_user(self, session: SessionController, user_message: str):
        """Generate bot response to user message."""
        await asyncio.sleep(1)

        if session.session_state != SessionState.ACTIVE:
            return

        available = ["p2", "p3", "p4", "p5"]
        next_speaker_id, _reason = self.orchestrator.select_next_speaker(
            session.session_id,
            user_message,
            available
        )

        persona = self.persona_manager.get_persona(next_speaker_id)
        if not persona:
            return

        async with session.speaker_lock:
            if session.session_state != SessionState.ACTIVE or session.is_locked:
                return

            await self._send_typing_indicator(session, next_speaker_id, True)
            await asyncio.sleep(await self.orchestrator.get_thinking_delay())

            response_prompt = f"""The user just said: "{user_message}"

Topic: "{session.topic}"

Recent context: {self._get_recent_context(session)}

Anti-repeat constraints:
- Do not repeat existing points.
- Add a new perspective, example, or counterpoint.

Respond appropriately in 2-3 sentences. Engage with their point directly."""

            context_prompt = self.persona_manager.build_context_prompt(
                persona,
                session.topic,
                self.orchestrator.get_session_phase(session.session_id).value
            )

            response = await self._safe_generate(
                prompt=response_prompt,
                system_prompt=context_prompt,
                context_messages=session.messages[-settings.max_context_messages:],
                temperature=0.75,
                max_tokens=150
            )

            await self._send_typing_indicator(session, next_speaker_id, False)
            await self._send_bot_message(session, next_speaker_id, persona.name, response, "discussion")
            self.orchestrator.record_message(session.session_id, next_speaker_id, response)

    async def _send_bot_message(
        self,
        session: SessionController,
        speaker_id: str,
        speaker_name: str,
        content: str,
        phase: str
    ):
        """Send a bot message to the client."""
        if session.session_state not in (SessionState.ACTIVE, SessionState.ENDING):
            return
        if session.session_state == SessionState.ENDING and phase != "conclusion":
            return

        message = {
            "speaker_id": speaker_id,
            "speaker_name": speaker_name,
            "content": content,
            "message_type": "moderator" if speaker_id == "p1" else "bot",
            "session_phase": phase,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        session.append_message(message)

        await self._save_message_to_db(session.session_id, message)

        await session.safe_send_json({
            "type": "bot_message",
            "payload": message
        })

    async def _send_typing_indicator(self, session: SessionController, speaker_id: str, is_typing: bool):
        """Send typing indicator to client."""
        await session.safe_send_json({
            "type": "typing_indicator",
            "payload": {
                "speaker_id": speaker_id,
                "is_typing": is_typing
            }
        })

    async def _run_timer(self, session: SessionController):
        """Run the session timer (independent, 1s ticks)."""
        logger.info(f"⏱️ Timer started for session {session.session_id}: {session.duration_seconds} seconds")

        if not session.start_timestamp:
            session.start_timestamp = datetime.now(timezone.utc)

        loop = asyncio.get_running_loop()
        start_monotonic = loop.time()
        duration = session.duration_seconds

        while session.session_state == SessionState.ACTIVE:
            elapsed = int(loop.time() - start_monotonic)
            remaining = max(0, duration - elapsed)
            session.time_remaining = remaining
            session.last_timer_tick_at = datetime.now(timezone.utc)

            payload = {
                "seconds_remaining": remaining,
                "formatted_time": f"{remaining // 60:02d}:{remaining % 60:02d}"
            }

            await session.safe_send_json({
                "type": "session_timer_update",
                "payload": payload
            })

            if remaining <= 0:
                break

            await asyncio.sleep(1)

        logger.info(
            f"⏱️ Timer ended for session {session.session_id} (state: {session.session_state})"
        )

        if session.session_state == SessionState.ACTIVE and session.time_remaining <= 0:
            asyncio.create_task(self._end_session(session, end_reason="timer_zero"))

    async def _cancel_task(self, task: Optional[asyncio.Task], name: str) -> None:
        """Cancel and await a task safely."""
        if task and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.CancelledError:
                logger.debug(f"Task {name} cancelled")
            except Exception as e:
                logger.debug(f"Task {name} cancellation error: {e}")

    async def _end_session(self, session: SessionController, end_reason: str):
        """End the GD session immediately and reliably."""
        async with session.end_lock:
            if session.session_state in (SessionState.ENDING, SessionState.ENDED):
                return

            session.session_state = SessionState.ENDING
            session.end_reason = end_reason
            session.is_locked = True

        await session.safe_send_json({
            "type": "session_ending",
            "payload": {
                "session_id": session.session_id,
                "reason": end_reason
            }
        })

        await self._cancel_task(session.timer_task, "timer")
        await self._cancel_task(session.orchestrator_task, "orchestrator")

        # Flush any buffered messages before generating feedback
        await self._flush_message_buffer(session)

        moderator = self.persona_manager.get_moderator()

        conclusion_prompt = f"""Conclude the Group Discussion on: "{session.topic}"

{"The time is up. " if end_reason == "timer_zero" else "The discussion is being concluded. "}Summarize 2-3 key points that were discussed and thank participants.
Keep it to 2-3 sentences. Be professional and conclusive."""

        try:
            conclusion = await self._safe_generate(
                prompt=conclusion_prompt,
                system_prompt=moderator.system_prompt,
                context_messages=session.messages[-10:],
                temperature=0.5,
                max_tokens=150
            )
            await self._send_bot_message(session, "p1", moderator.name, conclusion, "conclusion")
        except Exception as e:
            logger.error(f"Error generating conclusion: {e}")
            await self._send_bot_message(
                session,
                "p1",
                moderator.name,
                "Thank you all for this insightful discussion. We've covered some excellent points today.",
                "conclusion"
            )

        session.performance_report = await self._generate_feedback_with_timeout(session)

        await self._save_feedback_to_db(session.session_id, session.performance_report)

        await session.safe_send_json({
            "type": "session_ended",
            "payload": {
                "session_id": session.session_id,
                "feedback": session.performance_report,
                "auto_ended": end_reason == "timer_zero"
            }
        })

        await session.safe_send_json({
            "type": "performance_report_ready",
            "payload": {
                "session_id": session.session_id,
                "feedback": session.performance_report
            }
        })

        session.session_state = SessionState.ENDED
        self.orchestrator.cleanup_session(session.session_id)

    async def end_session(self, connection_id: int):
        """End a session early (triggered by user)."""
        session_id = self.session_by_connection.get(connection_id)
        session = self.sessions.get(session_id) if session_id else None
        if session:
            logger.info(f"🛑 User requested session end for connection {connection_id}")
            await self._end_session(session, end_reason="user_click")

    async def send_timer_snapshot(self, connection_id: int):
        """Send the current timer state to the client."""
        session_id = self.session_by_connection.get(connection_id)
        session = self.sessions.get(session_id) if session_id else None
        if not session:
            return

        payload = {
            "seconds_remaining": max(0, session.time_remaining),
            "formatted_time": f"{max(0, session.time_remaining) // 60:02d}:{max(0, session.time_remaining) % 60:02d}",
            "session_state": session.session_state.value
        }

        await session.safe_send_json({
            "type": "session_timer_update",
            "payload": payload
        })

    async def _generate_feedback_with_timeout(self, session: SessionController) -> Dict[str, Any]:
        """Generate feedback with a strict timeout and fallback."""
        try:
            return await asyncio.wait_for(
                self.feedback_service.generate_feedback(
                    session.session_id,
                    session.topic,
                    session.messages
                ),
                timeout=45.0
            )
        except Exception as e:
            logger.error(f"Feedback generation timeout or error: {e}")
            return self.feedback_service._fallback_feedback(
                session.session_id,
                [m for m in session.messages if m.get("speaker_id") == "user"],
                len(session.messages)
            )

    async def _safe_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context_messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> str:
        """Generate LLM response with strict timeout and fallback (fully async, no threads)."""
        try:
            return await asyncio.wait_for(
                self.ollama.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context_messages=context_messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                ),
                timeout=45.0
            )
        except Exception:
            logger.exception("LLM generate timeout or error")
        return self.ollama._get_fallback_response()

    async def _save_session_to_db(self, session: SessionController):
        """Save session to database."""
        try:
            async with async_session() as db:
                db_session = Session(
                    id=session.session_id,
                    topic=session.topic,
                    category=session.category,
                    status="active",
                    started_at=session.created_at,
                    duration_seconds=session.duration_seconds
                )
                db.add(db_session)
                await db.commit()
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    async def _save_message_to_db(self, session_id: str, message: Dict):
        """Buffer message for batch DB write (flushes every 5 messages)."""
        session = self.sessions.get(session_id)
        if session:
            session._message_buffer.append({"session_id": session_id, **message})
            if len(session._message_buffer) >= 5:
                await self._flush_message_buffer(session)

    async def _flush_message_buffer(self, session: SessionController):
        """Flush buffered messages to DB in a single transaction."""
        if not session._message_buffer:
            return
        buf = session._message_buffer[:]
        session._message_buffer.clear()
        try:
            async with async_session() as db:
                for msg in buf:
                    db_message = Message(
                        session_id=msg["session_id"],
                        speaker_id=msg["speaker_id"],
                        speaker_name=msg["speaker_name"],
                        content=msg["content"],
                        message_type=msg["message_type"],
                        session_phase=msg["session_phase"]
                    )
                    db.add(db_message)
                await db.commit()
        except Exception as e:
            logger.error(f"Error batch-saving messages: {e}")

    async def _save_feedback_to_db(self, session_id: str, feedback: Dict):
        """Save feedback to database."""
        try:
            async with async_session() as db:
                db_feedback = Feedback(
                    session_id=session_id,
                    confidence_score=feedback.get("confidence_score"),
                    clarity_score=feedback.get("clarity_fluency"),
                    grammar_score=feedback.get("grammar_accuracy"),
                    argument_score=feedback.get("argument_strength"),
                    participation_score=feedback.get("participation_ratio"),
                    leadership_score=feedback.get("leadership_initiative"),
                    overall_score=feedback.get("overall_score"),
                    strengths=feedback.get("top_strengths"),
                    improvements=feedback.get("top_improvements"),
                    vocabulary_suggestions={
                        "vocabulary_strength": feedback.get("vocabulary_strength"),
                        "suggested_phrases": feedback.get("suggested_phrases"),
                        "filler_words": feedback.get("filler_words")
                    },
                    detailed_analysis=feedback.get("detailed_summary")
                )
                db.add(db_feedback)

                from sqlalchemy import update
                await db.execute(
                    update(Session)
                    .where(Session.id == session_id)
                    .values(status="completed", ended_at=datetime.now(timezone.utc))
                )

                await db.commit()
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
    

