"""Tests for the persona manager."""
import pytest
from app.services.persona_manager import PersonaManager, PERSONAS


class TestPersonaManager:
    """Test suite for PersonaManager."""

    def setup_method(self):
        self.manager = PersonaManager()

    def test_all_personas_defined(self):
        """All 5 personas (p1-p5) should exist."""
        for pid in ["p1", "p2", "p3", "p4", "p5"]:
            assert pid in PERSONAS
            persona = PERSONAS[pid]
            assert persona.id == pid
            assert persona.name
            assert persona.role
            assert persona.system_prompt
            assert persona.avatar_color

    def test_get_moderator(self):
        """Moderator should be p1."""
        mod = self.manager.get_moderator()
        assert mod.id == "p1"
        assert mod.name == "Moderator"

    def test_get_all_participants(self):
        """Should return p2-p5 (excluding moderator)."""
        participants = self.manager.get_all_participants()
        ids = [p.id for p in participants]
        assert "p1" not in ids
        assert set(ids) == {"p2", "p3", "p4", "p5"}

    def test_get_persona_valid(self):
        """Valid persona ID returns persona."""
        persona = self.manager.get_persona("p3")
        assert persona is not None
        assert persona.name == "Priya"

    def test_get_persona_invalid(self):
        """Invalid persona ID returns None."""
        assert self.manager.get_persona("invalid") is None

    def test_get_participant_info_includes_user(self):
        """Participant info should include user placeholder."""
        info = self.manager.get_participant_info()
        ids = [p["id"] for p in info]
        assert "user" in ids
        assert "p1" in ids  # Moderator included

    def test_get_participant_info_count(self):
        """Should include moderator + 4 bots + user = 6."""
        info = self.manager.get_participant_info()
        assert len(info) == 6

    def test_build_context_prompt_phases(self):
        """Context prompt should vary by phase."""
        persona = self.manager.get_persona("p2")
        intro = self.manager.build_context_prompt(persona, "AI Ethics", "intro")
        discussion = self.manager.build_context_prompt(persona, "AI Ethics", "discussion")
        conclusion = self.manager.build_context_prompt(persona, "AI Ethics", "conclusion")

        assert "just introduced" in intro
        assert "discussing" in discussion
        assert "wrapping up" in conclusion

    def test_build_context_prompt_anti_repeat(self):
        """Context prompt should include anti-repetition rules."""
        persona = self.manager.get_persona("p3")
        prompt = self.manager.build_context_prompt(persona, "Test Topic")
        assert "anti-repetition" in prompt.lower()

    def test_persona_priority_weights(self):
        """Leader should have higher weight, moderator lower."""
        leader = PERSONAS["p2"]
        moderator = PERSONAS["p1"]
        assert leader.priority_weight > moderator.priority_weight
