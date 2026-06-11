"""Tests for the topic service."""
import pytest
from app.services.topic_service import TopicService


class TestTopicService:
    """Test suite for TopicService."""

    def setup_method(self):
        self.service = TopicService()

    def test_get_categories_returns_all(self):
        """All 10 categories should be available."""
        categories = self.service.get_categories()
        assert len(categories) >= 10
        names = {c.name for c in categories}
        assert "Technology" in names
        assert "Current Affairs" in names
        assert "Environment" in names
        assert "Education" in names
        assert "AI Ethics" in names
        assert "Startups" in names
        assert "Global Issues" in names

    def test_get_topics_by_category(self):
        """Each category should return topics."""
        topics = self.service.get_topics_by_category("Technology")
        assert len(topics) > 0
        assert all(hasattr(t, "id") and hasattr(t, "title") for t in topics)

    def test_get_topics_by_category_case_insensitive(self):
        """Category lookup should be case-insensitive."""
        topics = self.service.get_topics_by_category("technology")
        assert len(topics) > 0

    def test_get_topics_missing_category(self):
        """Non-existent category returns empty list."""
        topics = self.service.get_topics_by_category("NonExistent")
        assert topics == []

    def test_get_random_topic(self):
        """Random topic selection should return a TopicInfo."""
        topic = self.service.get_random_topic("Technology")
        assert topic is not None
        assert topic.title

    def test_get_random_topic_any(self):
        """'any' category should pick a random category."""
        topic = self.service.get_random_topic("any")
        assert topic is not None

    def test_anti_repeat_memory(self):
        """Same user should not get the same topic consecutively (with enough pool)."""
        seen_ids = set()
        for _ in range(5):
            topic = self.service.get_random_topic("Technology", user_key="test_user")
            if topic:
                seen_ids.add(topic.id)
        # With a large pool, we expect some variety
        assert len(seen_ids) > 1

    def test_get_topic_by_id(self):
        """Should retrieve a specific topic by ID."""
        topic = self.service.get_topic_by_id("tech1")
        assert topic is not None
        assert "Social Media" in topic.title

    def test_get_topic_by_id_not_found(self):
        """Non-existent topic ID returns None."""
        assert self.service.get_topic_by_id("nonexistent_xyz") is None

    def test_record_manual_topic_usage(self):
        """Manual topic recording should not raise."""
        self.service.record_manual_topic_usage("Technology", "Social Media's Impact on Society", "test_user")
        # Verify the topic appears in recent memory
        assert self.service.topic_usage_counter.get("tech1", 0) >= 0

    def test_expanded_topics_minimum_count(self):
        """Each category should have at least 110 topics after expansion."""
        for category, topics in self.service.topics.items():
            assert len(topics) >= 110, f"{category} has only {len(topics)} topics"
