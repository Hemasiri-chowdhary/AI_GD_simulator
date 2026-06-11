"""Tests for the feedback service."""
import pytest
from app.services.feedback_service import FeedbackService


class TestFeedbackService:
    """Test suite for FeedbackService."""

    def setup_method(self):
        self.service = FeedbackService()

    def test_build_transcript(self):
        """Transcript should clearly mark user messages."""
        messages = [
            {"speaker_id": "user", "speaker_name": "You", "content": "Hello"},
            {"speaker_id": "p2", "speaker_name": "Arjun", "content": "Hi there"},
        ]
        transcript = self.service._build_transcript(messages)
        assert "[USER - You]: Hello" in transcript
        assert "[Arjun]: Hi there" in transcript

    def test_empty_feedback_no_participation(self):
        """Empty feedback when user didn't participate."""
        result = self.service._empty_feedback("s1", "No participation")
        assert result["session_id"] == "s1"
        assert result["overall_score"] == 0
        assert result["confidence_score"] == 0

    def test_fallback_feedback_basic(self):
        """Fallback feedback should produce reasonable scores."""
        user_messages = [
            {"speaker_id": "user", "speaker_name": "You", "content": "I think AI will create more jobs than it destroys."},
            {"speaker_id": "user", "speaker_name": "You", "content": "However, we need reskilling programs to manage the transition."},
        ]
        result = self.service._fallback_feedback("s1", user_messages, 10)

        assert result["session_id"] == "s1"
        assert 0 <= result["confidence_score"] <= 10
        assert 0 <= result["overall_score"] <= 100
        assert isinstance(result["top_strengths"], list)
        assert isinstance(result["top_improvements"], list)
        assert len(result["top_strengths"]) <= 3
        assert len(result["top_improvements"]) <= 3

    def test_fallback_feedback_detects_fillers(self):
        """Fallback should detect filler words."""
        user_messages = [
            {"speaker_id": "user", "speaker_name": "You", "content": "Um, like, I basically think you know this is important"},
        ]
        result = self.service._fallback_feedback("s1", user_messages, 5)
        assert len(result["filler_words"]) > 0

    def test_fallback_feedback_high_participation(self):
        """High participation should yield higher scores."""
        user_messages = [
            {"speaker_id": "user", "content": f"Point {i} about the topic with detailed analysis and examples"} 
            for i in range(5)
        ]
        result = self.service._fallback_feedback("s1", user_messages, 10)
        assert result["participation_ratio"] == 50.0

    def test_parse_feedback_response_valid_json(self):
        """Should parse valid JSON from LLM response."""
        response = '{"confidence_score": 8, "clarity_fluency": 7, "overall_score": 75}'
        result = self.service._parse_feedback_response(response)
        assert result["confidence_score"] == 8

    def test_parse_feedback_response_embedded_json(self):
        """Should extract JSON from surrounding text."""
        response = 'Here is the analysis:\n{"confidence_score": 9}\nThank you.'
        result = self.service._parse_feedback_response(response)
        assert result["confidence_score"] == 9

    def test_parse_feedback_response_invalid(self):
        """Should return defaults for unparseable response."""
        result = self.service._parse_feedback_response("This is not JSON at all")
        assert result["confidence_score"] == 6
        assert result["overall_score"] == 60

    def test_compute_overall_score(self):
        """Overall score should be average of metrics * 10."""
        feedback = {
            "confidence_score": 8,
            "clarity_fluency": 7,
            "grammar_accuracy": 6,
            "vocabulary_strength": 7,
            "argument_strength": 8,
            "leadership_initiative": 5,
        }
        score = self.service._compute_overall_score(feedback)
        expected = round(sum([8, 7, 6, 7, 8, 5]) / 6 * 10, 1)
        assert score == expected

    def test_compute_overall_score_zeros(self):
        """Should handle all-zero metrics."""
        feedback = {
            "confidence_score": 0,
            "clarity_fluency": 0,
            "grammar_accuracy": 0,
            "vocabulary_strength": 0,
            "argument_strength": 0,
            "leadership_initiative": 0,
        }
        assert self.service._compute_overall_score(feedback) == 0.0
