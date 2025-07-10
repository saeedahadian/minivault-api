"""Pydantic models for MiniVault API."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    """Request model for prompt generation."""

    prompt: str = Field(..., min_length=1, description="Input prompt for generation")
    stream: bool = Field(False, description="Whether to stream the response using SSE")


class Usage(BaseModel):
    """Token usage tracking model."""

    prompt_tokens: int = Field(..., ge=0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        ..., ge=0, description="Number of tokens in the completion"
    )
    total_tokens: int = Field(..., ge=0, description="Total tokens used")


class GenerateResponse(BaseModel):
    """Response model for generated text."""

    response: str = Field(..., description="Generated response text")
    usage: Usage = Field(..., description="Token usage information")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StreamToken(BaseModel):
    """Model for streaming response tokens."""

    token: str
    index: int
    usage: Optional[Usage] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = "healthy"
    uptime_seconds: float
    total_requests: int
    version: str = "1.0.0"
    ai_assisted: bool = True


class LogEntry(BaseModel):
    """Model for JSONL log entries."""

    timestamp: datetime
    prompt: str
    response: str
    usage: Usage
    processing_time_ms: float
    ip_address: Optional[str] = None
    stream: bool = False
