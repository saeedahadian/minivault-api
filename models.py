"""Pydantic models for MiniVault API."""

from datetime import datetime, timezone
from typing import Optional, List, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class PresetType(str, Enum):
    """Available preset configurations for generation."""
    creative = "creative"
    balanced = "balanced"
    precise = "precise"
    deterministic = "deterministic"
    code = "code"


class GenerateRequest(BaseModel):
    """Request model for prompt generation."""

    prompt: str = Field(..., min_length=1, description="Input prompt for generation")
    stream: bool = Field(False, description="Whether to stream the response using SSE")
    preset: Optional[PresetType] = Field(None, description="Preset configuration for common use cases")
    model: Optional[str] = Field(None, description="Model to use for generation")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Top-p sampling")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="Maximum tokens to generate")
    system: Optional[str] = Field(None, description="System prompt for the model")


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
    version: str = "2.0.1"
    llm_status: Optional[dict] = None


class ModelInfo(BaseModel):
    """Model information response."""
    
    name: str
    size: Optional[str] = None
    modified: Optional[datetime] = None


class ModelsResponse(BaseModel):
    """Available models response."""
    
    models: List[ModelInfo]


class LogEntry(BaseModel):
    """Model for JSONL log entries."""
    
    model_config = {"protected_namespaces": ()}

    timestamp: datetime
    prompt: str
    response: str
    usage: Usage
    processing_time_ms: float
    ip_address: Optional[str] = None
    stream: bool = False
    
    # Enhanced logging for v2.0 features
    preset_used: Optional[PresetType] = None
    model_name: Optional[str] = None
    temperature_used: Optional[float] = None
    top_p_used: Optional[float] = None
    max_tokens_used: Optional[int] = None
    system_prompt: Optional[str] = None
    llm_provider: str = "stub"
    fallback_used: bool = False


class PresetInfo(BaseModel):
    """Information about a preset configuration."""
    
    name: PresetType
    description: str
    temperature: float
    top_p: float
    max_tokens: int


class PresetsResponse(BaseModel):
    """Response for listing available presets."""
    
    presets: List[PresetInfo]
    default: PresetType
