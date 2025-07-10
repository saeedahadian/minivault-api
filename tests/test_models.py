import pytest
from pydantic import ValidationError
from datetime import datetime

from models import GenerateRequest, GenerateResponse, Usage, LogEntry, StreamToken


class TestGenerateRequest:
    def test_valid_request(self):
        """Test valid request creation."""
        request = GenerateRequest(prompt="Hello world")
        assert request.prompt == "Hello world"
        assert request.stream is False

    def test_empty_prompt_fails(self):
        """Test that empty prompt fails validation."""
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="")

    def test_stream_parameter(self):
        """Test stream parameter handling."""
        request = GenerateRequest(prompt="Hello", stream=True)
        assert request.stream is True


class TestGenerateResponse:
    def test_valid_response(self):
        """Test valid response creation."""
        usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        response = GenerateResponse(
            response="Hello world", usage=usage, generated_at=datetime.now()
        )
        assert response.response == "Hello world"
        assert response.usage.total_tokens == 15

    def test_response_serialization(self):
        """Test response can be serialized to JSON."""
        usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        response = GenerateResponse(
            response="Hello world", usage=usage, generated_at=datetime.now()
        )
        data = response.model_dump()
        assert "response" in data
        assert "usage" in data
        assert "generated_at" in data


class TestUsage:
    def test_usage_calculation(self):
        """Test usage token calculation."""
        usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        assert usage.prompt_tokens == 5
        assert usage.completion_tokens == 10
        assert usage.total_tokens == 15

    def test_usage_negative_tokens_fails(self):
        """Test that negative tokens fail validation."""
        with pytest.raises(ValidationError):
            Usage(prompt_tokens=-1, completion_tokens=10, total_tokens=9)


class TestLogEntry:
    def test_log_entry_creation(self):
        """Test log entry creation."""
        usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        entry = LogEntry(
            timestamp=datetime.now(),
            prompt="Hello",
            response="Hi there",
            usage=usage,
            processing_time_ms=100.0,
            ip_address="127.0.0.1",
            stream=False,
        )
        assert entry.prompt == "Hello"
        assert entry.processing_time_ms == 100.0
        assert entry.stream is False

    def test_log_entry_serialization(self):
        """Test log entry serializes properly."""
        usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        entry = LogEntry(
            timestamp=datetime.now(),
            prompt="Hello",
            response="Hi there",
            usage=usage,
            processing_time_ms=100.0,
            ip_address="127.0.0.1",
            stream=False,
        )
        data = entry.model_dump()
        assert "timestamp" in data
        assert "processing_time_ms" in data


class TestStreamToken:
    def test_stream_token_creation(self):
        """Test stream token creation."""
        token = StreamToken(token="Hello", index=0)
        assert token.token == "Hello"
        assert token.index == 0
        assert token.usage is None

    def test_stream_token_with_usage(self):
        """Test stream token with usage."""
        usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        token = StreamToken(token="world", index=1, usage=usage)
        assert token.usage.total_tokens == 15
