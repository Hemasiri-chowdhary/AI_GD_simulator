"""Tests for the Ollama client."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ollama_client import OllamaClient


class TestOllamaClient:
    """Test suite for OllamaClient."""

    def setup_method(self):
        self.client = OllamaClient()

    def test_default_config(self):
        assert self.client.base_url == "http://localhost:11434"
        assert self.client.max_retries == 3

    def test_build_messages_basic(self):
        messages = self.client._build_messages("Hello", None, None)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_build_messages_with_system(self):
        messages = self.client._build_messages("Hello", "You are helpful", None)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"

    def test_build_messages_with_context(self):
        context = [
            {"speaker_id": "user", "speaker_name": "You", "content": "test1"},
            {"speaker_id": "p2", "speaker_name": "Arjun", "content": "test2"},
        ]
        messages = self.client._build_messages("Question", "System", context)
        assert len(messages) == 4  # system + 2 context + prompt
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_fallback_response(self):
        response = self.client._get_fallback_response()
        assert isinstance(response, str)
        assert len(response) > 10

    @pytest.mark.asyncio
    async def test_check_connection_failure(self):
        """Should return False when Ollama is not reachable."""
        with patch.object(self.client, '_get_async_client') as mock:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock.return_value = mock_client
            result = await self.client.check_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_generate_fallback_on_failure(self):
        """Should return fallback when all retries fail."""
        with patch.object(self.client, '_get_async_client') as mock:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock.return_value = mock_client
            self.client.max_retries = 1
            self.client.retry_delay = 0.01
            result = await self.client.generate("test prompt")
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Should return generated content on success."""
        with patch.object(self.client, '_get_async_client') as mock:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": {"content": "  Generated response  "}
            }
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock.return_value = mock_client

            result = await self.client.generate("test prompt")
            assert result == "Generated response"

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Should close the persistent client."""
        await self.client._get_async_client()
        assert self.client._async_client is not None
        await self.client.close()
        assert self.client._async_client is None
