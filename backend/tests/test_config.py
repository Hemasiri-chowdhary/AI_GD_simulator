"""Tests for configuration and settings."""
import pytest
from unittest.mock import patch
import os


class TestSettings:
    """Test suite for application settings."""

    def test_default_settings(self):
        """Test default settings values."""
        # Clear cache to get fresh settings
        from app.config import Settings
        settings = Settings()

        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_model == "llama3"
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000
        assert settings.debug is False  # Production default
        assert settings.log_level == "INFO"
        assert settings.max_message_length == 2000
        assert settings.session_duration_minutes == 10
        assert settings.preparation_time_seconds == 30
        assert settings.max_context_messages == 15
        assert settings.bot_response_timeout == 15
        assert settings.min_turn_delay == 2.0
        assert settings.max_turn_delay == 3.0
        assert settings.user_priority_turns == 4
        assert settings.user_silence_threshold == 30
        assert settings.max_user_invitations == 2

    def test_cors_origins_default(self):
        """Test CORS origins defaults."""
        from app.config import Settings
        settings = Settings()
        assert "http://localhost:3000" in settings.cors_origins
        assert "http://127.0.0.1:3000" in settings.cors_origins

    def test_settings_from_env(self):
        """Test that settings can be overridden via environment variables."""
        with patch.dict(os.environ, {"OLLAMA_MODEL": "mistral", "DEBUG": "true"}):
            from app.config import Settings
            settings = Settings()
            assert settings.ollama_model == "mistral"
            assert settings.debug is True

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        from app.config import get_settings
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
