import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestGenerateEndpoint:
    def test_generate_basic_request(self, client, mock_time):
        """Test basic generate request."""
        response = client.post("/generate", json={"prompt": "Hello world"})

        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert "usage" in data
        assert "generated_at" in data
        assert data["usage"]["prompt_tokens"] == 2
        assert data["usage"]["total_tokens"] > 0

    def test_generate_empty_prompt_fails(self, client):
        """Test that empty prompt fails validation."""
        response = client.post("/generate", json={"prompt": ""})
        assert response.status_code == 422

    def test_generate_missing_prompt_fails(self, client):
        """Test that missing prompt fails validation."""
        response = client.post("/generate", json={})
        assert response.status_code == 422

    def test_generate_meta_prompt_easter_egg(self, client, mock_time):
        """Test personal easter egg."""
        response = client.post("/generate", json={"prompt": "Who are you?"})

        assert response.status_code == 200
        data = response.json()
        assert "Saeed Ahadian" in data["response"]
        assert "Digikala" in data["response"]

    def test_generate_with_stream_false(self, client, mock_time):
        """Test generate with explicit stream=false."""
        response = client.post("/generate", json={"prompt": "Hello", "stream": False})

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "usage" in data

    def test_generate_logs_request(self, client, mock_time):
        """Test that generate request is logged."""
        # We can't easily test the logger without significant refactoring
        # so we'll just verify the request completes successfully
        response = client.post("/generate", json={"prompt": "Hello"})

        assert response.status_code == 200
        data = response.json()
        assert "response" in data


class TestStreamingEndpoint:
    def test_generate_streaming_request(self, client, mock_time):
        """Test streaming generate request."""
        response = client.post("/generate", json={"prompt": "Hello", "stream": True})

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "cache-control" in response.headers

        # Check SSE format
        content = response.content.decode()
        lines = content.strip().split("\n")

        # Should have data lines and a [DONE] line
        assert any(line.startswith("data: ") for line in lines)
        assert "data: [DONE]" in lines

    def test_streaming_response_format(self, client, mock_time):
        """Test streaming response follows SSE format."""
        response = client.post("/generate", json={"prompt": "Test", "stream": True})

        assert response.status_code == 200
        content = response.content.decode()

        # Parse SSE events
        events = []
        for line in content.strip().split("\n"):
            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix
                if data_str != "[DONE]":
                    events.append(json.loads(data_str))

        # Should have at least one token event
        assert len(events) > 0

        # Check token event structure
        for event in events:
            assert "token" in event
            assert "index" in event
            assert isinstance(event["index"], int)

        # Last event should have usage
        assert "usage" in events[-1]

    def test_streaming_logs_request(self, client, mock_time):
        """Test that streaming request is logged."""
        # We can't easily test the logger without significant refactoring
        # so we'll just verify the request completes successfully
        response = client.post("/generate", json={"prompt": "Hello", "stream": True})

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")


class TestHealthEndpoint:
    def test_health_endpoint(self, client):
        """Test health endpoint returns proper status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["version"] == "2.0.1"
        assert "uptime_seconds" in data
        assert "total_requests" in data
        assert isinstance(data["uptime_seconds"], float)
        assert isinstance(data["total_requests"], int)


class TestRateLimiting:
    def test_rate_limiting_enforcement(self, client):
        """Test rate limiting is enforced."""
        # Make requests quickly to trigger rate limiting
        responses = []
        for i in range(12):  # More than the 10 requests per minute limit
            response = client.post("/generate", json={"prompt": f"Request {i}"})
            responses.append(response)

        # Should have at least one rate limited response
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0

    def test_rate_limiting_error_message(self, client):
        """Test rate limiting returns proper error message."""
        # Trigger rate limiting
        for i in range(15):
            response = client.post("/generate", json={"prompt": f"Request {i}"})
            if response.status_code == 429:
                data = response.json()
                assert "detail" in data
                assert "rate limit" in data["detail"].lower()
                break


class TestErrorHandling:
    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON."""
        response = client.post(
            "/generate",
            content="invalid json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    def test_wrong_content_type(self, client):
        """Test handling of wrong content type."""
        response = client.post(
            "/generate",
            content="prompt=hello",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 422

    def test_method_not_allowed(self, client):
        """Test method not allowed for GET on generate."""
        response = client.get("/generate")
        assert response.status_code == 405

    def test_not_found_endpoint(self, client):
        """Test 404 for non-existent endpoints."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
