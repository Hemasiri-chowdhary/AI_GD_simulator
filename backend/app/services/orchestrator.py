"""Orchestrator Engine - Controls speaker selection and turn-taking."""
import logging
import asyncio
import random
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from app.services.persona_manager import PersonaManager, Persona
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SessionPhase(Enum):
    INTRO = "intro"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"


@dataclass
class TurnState:
    """Tracks turn-taking state for a session."""
    turns_since_user: int = 0
    last_user_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_speaker_id: str = ""
    speaker_history: List[str] = field(default_factory=list)
    controversial_claim: bool = False
    repetitive_content: bool = False
    total_turns: int = 0
    user_message_count: int = 0
    time_warnings_sent: Set[int] = field(default_factory=set)
    recent_point_tokens: List[Set[str]] = field(default_factory=list)
    repeat_streak: int = 0
    loop_breaker_pending: bool = False
    
    def record_turn(self, speaker_id: str):
        """Record a turn taken."""
        if speaker_id == "user":
            self.turns_since_user = 0
            self.last_user_time = datetime.now(timezone.utc)
            self.user_message_count += 1
        else:
            self.turns_since_user += 1
        
        self.last_speaker_id = speaker_id
        self.speaker_history.append(speaker_id)
        self.total_turns += 1
        
        # Keep only last 10 speakers in history
        if len(self.speaker_history) > 10:
            self.speaker_history = self.speaker_history[-10:]

    def record_content_signature(self, token_signature: Set[str], is_repetitive: bool):
        """Record semantic signature of a message for anti-repetition handling."""
        if token_signature:
            self.recent_point_tokens.append(token_signature)
            if len(self.recent_point_tokens) > 12:
                self.recent_point_tokens = self.recent_point_tokens[-12:]

        if is_repetitive:
            self.repeat_streak += 1
        else:
            self.repeat_streak = 0

        if self.repeat_streak >= 2:
            self.loop_breaker_pending = True


class Orchestrator:
    """Central brain for managing GD turn-taking and flow."""
    
    def __init__(self):
        self.persona_manager = PersonaManager()
        self.turn_states: Dict[str, TurnState] = {}
        self.speaker_locks: Dict[str, asyncio.Lock] = {}
        self.session_phases: Dict[str, SessionPhase] = {}
        self.session_start_times: Dict[str, datetime] = {}
        self.session_durations: Dict[str, int] = {}  # Session-specific durations
        
    def init_session(self, session_id: str, duration_seconds: int = None) -> None:
        """Initialize state for a new session (start time set when discussion starts)."""
        self.turn_states[session_id] = TurnState()
        self.speaker_locks[session_id] = asyncio.Lock()
        self.session_phases[session_id] = SessionPhase.INTRO
        self.session_durations[session_id] = duration_seconds or (settings.session_duration_minutes * 60)
        logger.info(f"Orchestrator initialized for session {session_id} with duration {self.session_durations[session_id]}s")

    def mark_discussion_start(self, session_id: str) -> None:
        """Mark the actual discussion start time (after preparation)."""
        self.session_start_times[session_id] = datetime.now(timezone.utc)
        logger.info(f"Discussion start time set for session {session_id}")
    
    def cleanup_session(self, session_id: str) -> None:
        """Clean up session state."""
        self.turn_states.pop(session_id, None)
        self.speaker_locks.pop(session_id, None)
        self.session_phases.pop(session_id, None)
        self.session_start_times.pop(session_id, None)
        self.session_durations.pop(session_id, None)
        logger.info(f"Orchestrator cleaned up session {session_id}")
    
    async def acquire_speaker_lock(self, session_id: str) -> bool:
        """Acquire the speaker lock for a session."""
        lock = self.speaker_locks.get(session_id)
        if lock:
            return await asyncio.wait_for(lock.acquire(), timeout=5.0)
        return False
    
    def release_speaker_lock(self, session_id: str) -> None:
        """Release the speaker lock for a session."""
        lock = self.speaker_locks.get(session_id)
        if lock and lock.locked():
            lock.release()
    
    def get_session_phase(self, session_id: str) -> SessionPhase:
        """Get the current phase of the session."""
        return self.session_phases.get(session_id, SessionPhase.DISCUSSION)
    
    def update_session_phase(self, session_id: str, time_remaining: int) -> SessionPhase:
        """Update session phase based on time remaining."""
        duration = self.session_durations.get(session_id, settings.session_duration_minutes * 60)
        
        if time_remaining > duration - 60:  # First minute
            phase = SessionPhase.INTRO
        elif time_remaining < 120:  # Last 2 minutes
            phase = SessionPhase.CONCLUSION
        else:
            phase = SessionPhase.DISCUSSION
        
        self.session_phases[session_id] = phase
        return phase
    
    def record_turn(self, session_id: str, speaker_id: str) -> None:
        """Record a turn taken by a speaker."""
        state = self.turn_states.get(session_id)
        if state:
            state.record_turn(speaker_id)

    def record_message(self, session_id: str, speaker_id: str, content: str) -> None:
        """Record turn plus content signature for anti-repetition control."""
        state = self.turn_states.get(session_id)
        if not state:
            return

        state.record_turn(speaker_id)

        if speaker_id == "user":
            state.repeat_streak = 0
            state.loop_breaker_pending = False
            return

        token_signature = self._tokenize_message(content)
        recent_signatures = state.recent_point_tokens[-6:]
        is_repetitive = any(self._jaccard_similarity(token_signature, old) >= 0.6 for old in recent_signatures)
        state.record_content_signature(token_signature, is_repetitive)
    
    def select_next_speaker(
        self,
        session_id: str,
        last_message: str,
        available_personas: List[str]
    ) -> Tuple[str, str]:
        """
        Select the next speaker based on turn-taking rules.
        Returns (persona_id, reason)
        """
        state = self.turn_states.get(session_id)
        if not state:
            return ("p2", "default_leader")
        
        phase = self.get_session_phase(session_id)

        if state.loop_breaker_pending:
            return ("p1", "loop_breaker_moderator")
        
        # Phase-specific logic
        if phase == SessionPhase.INTRO and state.total_turns < 2:
            return ("p2", "leader_opens_discussion")
        
        if phase == SessionPhase.CONCLUSION:
            return ("p1", "moderator_concludes")
        
        # Priority rules
        
        # Rule 1: Check if user has been silent too long
        silence_duration = int((datetime.now(timezone.utc) - state.last_user_time).total_seconds())
        if silence_duration > settings.user_silence_threshold and state.turns_since_user > 2:
            return ("p1", "invite_user")  # Moderator invites user
        
        # Rule 2: If controversial claim, opposer responds
        if self._detect_controversial(last_message):
            if "p4" in available_personas and state.last_speaker_id != "p4":
                return ("p4", "challenge_claim")
        
        # Rule 3: If agreement/support, maybe challenge it
        if self._detect_agreement(last_message):
            if "p4" in available_personas and random.random() > 0.5:
                return ("p4", "balance_perspective")
        
        # Rule 4: After disagreement, supporter builds consensus
        if self._detect_disagreement(last_message):
            if "p5" in available_personas:
                return ("p5", "build_consensus")
        
        # Rule 5: Prevent same speaker twice in a row
        filtered = [p for p in available_personas if p != state.last_speaker_id]
        if not filtered:
            filtered = available_personas
        
        # Rule 6: Prefer speakers who haven't spoken recently
        recent_speakers = set(state.speaker_history[-4:])
        underrepresented = [p for p in filtered if p not in recent_speakers]
        
        if underrepresented:
            selected = random.choice(underrepresented)
            return (selected, "balanced_participation")
        
        # Default: weighted random selection
        selected = self._weighted_selection(filtered)
        return (selected, "normal_turn")
    
    def _weighted_selection(self, persona_ids: List[str]) -> str:
        """Select a persona with weighted probability."""
        personas = [self.persona_manager.get_persona(pid) for pid in persona_ids]
        weights = [p.priority_weight if p else 1.0 for p in personas]
        total = sum(weights)
        weights = [w / total for w in weights]
        
        return random.choices(persona_ids, weights=weights, k=1)[0]
    
    def _detect_controversial(self, message: str) -> bool:
        """Detect if a message makes a controversial claim."""
        controversial_markers = [
            "always", "never", "everyone knows", "obviously",
            "clearly wrong", "the only solution", "must", "definitely"
        ]
        message_lower = message.lower()
        return any(marker in message_lower for marker in controversial_markers)
    
    def _detect_agreement(self, message: str) -> bool:
        """Detect if a message shows strong agreement."""
        agreement_markers = [
            "i agree", "exactly", "absolutely", "that's right",
            "well said", "great point", "i think so too"
        ]
        message_lower = message.lower()
        return any(marker in message_lower for marker in agreement_markers)
    
    def _detect_disagreement(self, message: str) -> bool:
        """Detect if a message shows disagreement."""
        disagreement_markers = [
            "disagree", "however", "but", "on the other hand",
            "not quite", "i don't think", "counterpoint"
        ]
        message_lower = message.lower()
        return any(marker in message_lower for marker in disagreement_markers)

    def _tokenize_message(self, message: str) -> Set[str]:
        """Tokenize message for approximate semantic overlap detection."""
        stopwords = {
            "the", "and", "for", "that", "this", "with", "from", "have", "has", "are",
            "was", "were", "will", "would", "should", "could", "into", "about", "their",
            "them", "they", "also", "very", "more", "most", "just", "what", "when", "where",
            "which", "while", "then", "than", "because", "there", "here", "our", "your", "you"
        }
        tokens = re.findall(r"[a-zA-Z]{3,}", message.lower())
        return {token for token in tokens if token not in stopwords}

    def _jaccard_similarity(self, a: Set[str], b: Set[str]) -> float:
        """Compute Jaccard similarity for two token sets."""
        if not a or not b:
            return 0.0
        union = a | b
        if not union:
            return 0.0
        return len(a & b) / len(union)

    def should_trigger_loop_breaker(self, session_id: str) -> bool:
        """Return True when moderator should redirect a looping discussion."""
        state = self.turn_states.get(session_id)
        return bool(state and state.loop_breaker_pending)

    def consume_loop_breaker(self, session_id: str) -> None:
        """Clear loop-breaker state after moderator intervention."""
        state = self.turn_states.get(session_id)
        if state:
            state.loop_breaker_pending = False
            state.repeat_streak = 0

    def get_loop_breaker_question(self, topic: str) -> str:
        """Return moderator redirect question to inject a fresh angle."""
        prompts = [
            f"Let's pivot slightly on '{topic}': what is one practical implementation challenge we haven't covered yet?",
            f"To move this forward on '{topic}', can we compare short-term and long-term outcomes?",
            f"Fresh angle for '{topic}': who benefits the most, and who might be left out?",
            f"Let's break repetition on '{topic}': what would be a realistic policy or business execution plan?"
        ]
        return random.choice(prompts)
    
    def should_invite_user(self, session_id: str) -> bool:
        """Check if the moderator should invite the user to speak."""
        state = self.turn_states.get(session_id)
        if not state:
            return False
        
        silence_duration = int((datetime.now(timezone.utc) - state.last_user_time).total_seconds())
        # Only invite if silent for more than 30 seconds AND at least 4 bot turns
        return (
            state.turns_since_user >= settings.user_priority_turns
            and silence_duration > settings.user_silence_threshold
        )
    
    def reset_user_invitation_timer(self, session_id: str):
        """Reset the user invitation timer after sending an invitation."""
        state = self.turn_states.get(session_id)
        if state:
            state.last_user_time = datetime.now(timezone.utc)
            state.turns_since_user = 0
    
    def get_concise_user_invite(self) -> str:
        """Get a concise, non-spammy message to invite the user to participate."""
        invites = [
            "Whenever you're ready, feel free to share your thoughts.",
            "Would you like to add your opinion here?",
        ]
        return random.choice(invites)
    
    def get_user_invite_message(self) -> str:
        """Get a message to invite the user to participate (legacy, use get_concise_user_invite instead)."""
        return self.get_concise_user_invite()
    
    async def get_thinking_delay(self) -> float:
        """Get a realistic thinking delay."""
        return random.uniform(settings.min_turn_delay, settings.max_turn_delay)
    
    def get_time_remaining(self, session_id: str) -> int:
        """Get time remaining in seconds for a session."""
        duration = self.session_durations.get(session_id, settings.session_duration_minutes * 60)
        start_time = self.session_start_times.get(session_id)
        
        # If discussion hasn't started yet, return full duration
        if not start_time:
            return duration
        
        elapsed = int((datetime.now(timezone.utc) - start_time).total_seconds())
        remaining = max(0, duration - elapsed)
        return remaining
    
    def should_end_session(self, session_id: str) -> bool:
        """Check if the session should end based on time."""
        return self.get_time_remaining(session_id) <= 0
    
    def get_time_warning_message(self, session_id: str, time_remaining: int) -> Optional[str]:
        """Get a time warning message if applicable (only once per threshold)."""
        state = self.turn_states.get(session_id)
        if not state:
            return None
        
        # Only send each warning once
        if time_remaining <= 120 and time_remaining > 115 and 120 not in state.time_warnings_sent:
            state.time_warnings_sent.add(120)
            return "We have 2 minutes remaining. Let's start wrapping up our key points."
        elif time_remaining <= 60 and time_remaining > 55 and 60 not in state.time_warnings_sent:
            state.time_warnings_sent.add(60)
            return "One minute left. Any final thoughts before we conclude?"
        return None
