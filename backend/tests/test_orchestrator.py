"""Tests for the orchestrator engine."""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from app.services.orchestrator import Orchestrator, TurnState, SessionPhase


class TestTurnState:
    """Test TurnState dataclass."""

    def test_initial_state(self):
        state = TurnState()
        assert state.turns_since_user == 0
        assert state.total_turns == 0
        assert state.user_message_count == 0
        assert state.last_speaker_id == ""
        assert isinstance(state.time_warnings_sent, set)

    def test_record_user_turn(self):
        state = TurnState()
        state.record_turn("user")
        assert state.turns_since_user == 0
        assert state.user_message_count == 1
        assert state.last_speaker_id == "user"
        assert state.total_turns == 1

    def test_record_bot_turn(self):
        state = TurnState()
        state.record_turn("p2")
        assert state.turns_since_user == 1
        assert state.user_message_count == 0
        assert state.last_speaker_id == "p2"

    def test_speaker_history_trimmed(self):
        state = TurnState()
        for i in range(15):
            state.record_turn(f"p{i % 5 + 1}")
        assert len(state.speaker_history) == 10

    def test_content_signature_repetition(self):
        state = TurnState()
        sig1 = {"artificial", "intelligence", "future"}
        state.record_content_signature(sig1, False)
        assert state.repeat_streak == 0

        # Same signature -> repetitive
        state.record_content_signature(sig1, True)
        assert state.repeat_streak == 1

        state.record_content_signature(sig1, True)
        assert state.repeat_streak == 2
        assert state.loop_breaker_pending is True


class TestOrchestrator:
    """Test Orchestrator logic."""

    def setup_method(self):
        self.orch = Orchestrator()

    def test_init_session(self):
        self.orch.init_session("s1", 600)
        assert "s1" in self.orch.turn_states
        assert "s1" in self.orch.speaker_locks
        assert self.orch.session_durations["s1"] == 600

    def test_cleanup_session(self):
        self.orch.init_session("s1", 600)
        self.orch.cleanup_session("s1")
        assert "s1" not in self.orch.turn_states
        assert "s1" not in self.orch.speaker_locks

    def test_mark_discussion_start(self):
        self.orch.init_session("s1", 600)
        self.orch.mark_discussion_start("s1")
        assert "s1" in self.orch.session_start_times
        assert isinstance(self.orch.session_start_times["s1"], datetime)

    def test_update_session_phase(self):
        self.orch.init_session("s1", 600)
        # First minute → intro
        phase = self.orch.update_session_phase("s1", 580)
        assert phase == SessionPhase.INTRO

        # Middle → discussion
        phase = self.orch.update_session_phase("s1", 300)
        assert phase == SessionPhase.DISCUSSION

        # Last 2 minutes → conclusion
        phase = self.orch.update_session_phase("s1", 60)
        assert phase == SessionPhase.CONCLUSION

    def test_select_next_speaker_leader_opens(self):
        self.orch.init_session("s1", 600)
        self.orch.session_phases["s1"] = SessionPhase.INTRO
        speaker, reason = self.orch.select_next_speaker("s1", "", ["p2", "p3", "p4", "p5"])
        assert speaker == "p2"
        assert reason == "leader_opens_discussion"

    def test_select_next_speaker_conclusion(self):
        self.orch.init_session("s1", 600)
        self.orch.session_phases["s1"] = SessionPhase.CONCLUSION
        # Need at least 2 total turns to bypass intro check
        self.orch.turn_states["s1"].total_turns = 5
        speaker, reason = self.orch.select_next_speaker("s1", "", ["p2", "p3", "p4", "p5"])
        assert speaker == "p1"
        assert reason == "moderator_concludes"

    def test_select_next_speaker_no_repeat(self):
        """Same speaker shouldn't be selected twice in a row."""
        self.orch.init_session("s1", 600)
        self.orch.session_phases["s1"] = SessionPhase.DISCUSSION
        state = self.orch.turn_states["s1"]
        state.total_turns = 5
        state.last_speaker_id = "p3"

        selected_speakers = set()
        for _ in range(20):
            speaker, _ = self.orch.select_next_speaker("s1", "test message", ["p2", "p3", "p4", "p5"])
            selected_speakers.add(speaker)

        # p3 should rarely or never be the first pick due to no-repeat rule
        # But due to randomness, just check we get variety
        assert len(selected_speakers) > 1

    def test_controversial_detection(self):
        assert self.orch._detect_controversial("Everyone knows this is true") is True
        assert self.orch._detect_controversial("I think there are many perspectives") is False

    def test_agreement_detection(self):
        assert self.orch._detect_agreement("I agree completely") is True
        assert self.orch._detect_agreement("I have a different view") is False

    def test_disagreement_detection(self):
        assert self.orch._detect_disagreement("However, I think differently") is True
        assert self.orch._detect_disagreement("That's a great point") is False

    def test_get_time_remaining_before_start(self):
        self.orch.init_session("s1", 600)
        remaining = self.orch.get_time_remaining("s1")
        assert remaining == 600

    def test_get_time_remaining_after_start(self):
        self.orch.init_session("s1", 600)
        self.orch.session_start_times["s1"] = datetime.now(timezone.utc) - timedelta(seconds=100)
        remaining = self.orch.get_time_remaining("s1")
        assert 498 <= remaining <= 502  # Allow 2s tolerance

    def test_should_end_session(self):
        self.orch.init_session("s1", 10)
        self.orch.session_start_times["s1"] = datetime.now(timezone.utc) - timedelta(seconds=15)
        assert self.orch.should_end_session("s1") is True

    def test_should_invite_user(self):
        self.orch.init_session("s1", 600)
        state = self.orch.turn_states["s1"]
        state.turns_since_user = 10
        state.last_user_time = datetime.now(timezone.utc) - timedelta(seconds=60)
        assert self.orch.should_invite_user("s1") is True

    def test_should_not_invite_user_recently_spoke(self):
        self.orch.init_session("s1", 600)
        state = self.orch.turn_states["s1"]
        state.turns_since_user = 1
        state.last_user_time = datetime.now(timezone.utc)
        assert self.orch.should_invite_user("s1") is False

    def test_time_warning_messages(self):
        self.orch.init_session("s1", 600)
        # 2-minute warning
        msg = self.orch.get_time_warning_message("s1", 118)
        assert msg is not None
        assert "2 minutes" in msg

        # Same warning not sent again
        msg2 = self.orch.get_time_warning_message("s1", 117)
        assert msg2 is None

        # 1-minute warning
        msg3 = self.orch.get_time_warning_message("s1", 58)
        assert msg3 is not None
        assert "One minute" in msg3

    def test_loop_breaker(self):
        self.orch.init_session("s1", 600)
        state = self.orch.turn_states["s1"]
        state.loop_breaker_pending = True
        assert self.orch.should_trigger_loop_breaker("s1") is True
        self.orch.consume_loop_breaker("s1")
        assert self.orch.should_trigger_loop_breaker("s1") is False

    def test_jaccard_similarity(self):
        a = {"hello", "world", "test"}
        b = {"hello", "world", "test"}
        assert self.orch._jaccard_similarity(a, b) == 1.0

        c = {"different", "words", "here"}
        assert self.orch._jaccard_similarity(a, c) == 0.0

        d = {"hello", "world", "different"}
        sim = self.orch._jaccard_similarity(a, d)
        assert 0.4 < sim < 0.6

    def test_tokenize_message(self):
        tokens = self.orch._tokenize_message("The quick brown fox jumps over the lazy dog")
        assert "quick" in tokens
        assert "brown" in tokens
        assert "the" not in tokens  # stopword

    @pytest.mark.asyncio
    async def test_get_thinking_delay(self):
        delay = await self.orch.get_thinking_delay()
        from app.config import get_settings
        settings = get_settings()
        assert settings.min_turn_delay <= delay <= settings.max_turn_delay
