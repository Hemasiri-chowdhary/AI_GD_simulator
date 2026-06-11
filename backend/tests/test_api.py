"""Tests for API routes."""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRootEndpoints:
    """Test root and health endpoints."""

    @pytest.mark.asyncio
    async def test_root(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "AI-GD-Pro"
        assert data["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "ollama_reachable" in data


class TestCategoryEndpoints:
    """Test category and topic API endpoints."""

    @pytest.mark.asyncio
    async def test_get_categories(self, client):
        response = await client.get("/api/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 10
        names = [c["name"] for c in data]
        assert "Technology" in names

    @pytest.mark.asyncio
    async def test_get_topics_by_category(self, client):
        response = await client.get("/api/topics/Technology")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_get_topics_invalid_category(self, client):
        response = await client.get("/api/topics/NonExistentCategory")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_random_topic(self, client):
        response = await client.get("/api/topic/random/Technology")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data

    @pytest.mark.asyncio
    async def test_get_random_topic_invalid_category(self, client):
        response = await client.get("/api/topic/random/NonExistent123")
        assert response.status_code == 404


class TestSessionEndpoints:
    """Test session API endpoints."""

    @pytest.mark.asyncio
    async def test_get_sessions_empty(self, client):
        response = await client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, client):
        response = await client.get("/api/sessions/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_feedback_not_found(self, client):
        response = await client.get("/api/sessions/nonexistent-id/feedback")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_transcript_not_found(self, client):
        response = await client.get("/api/sessions/nonexistent-id/transcript")
        assert response.status_code == 404
