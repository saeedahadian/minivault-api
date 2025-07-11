"""Configuration management for MiniVault API."""

import os
from typing import Optional, Dict
from dataclasses import dataclass

from models import PresetType


@dataclass
class LLMSettings:
    """LLM-specific configuration."""
    provider: str = "ollama"  # ollama, openai, stub
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 1000
    timeout: float = 30.0
    api_key: Optional[str] = None  # For OpenAI API
    system_prompt: Optional[str] = None


@dataclass
class APISettings:
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    rate_limit: int = 10
    rate_limit_window: int = 60
    log_level: str = "INFO"


@dataclass
class AppConfig:
    """Main application configuration."""
    llm: LLMSettings
    api: APISettings
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        llm_settings = LLMSettings(
            provider=os.getenv("LLM_PROVIDER", "ollama"),
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
            model=os.getenv("LLM_MODEL", "llama3.1:8b"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            top_p=float(os.getenv("LLM_TOP_P", "0.9")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
            timeout=float(os.getenv("LLM_TIMEOUT", "30.0")),
            api_key=os.getenv("LLM_API_KEY"),
            system_prompt=os.getenv("LLM_SYSTEM_PROMPT")
        )
        
        api_settings = APISettings(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            reload=os.getenv("API_RELOAD", "true").lower() == "true",
            rate_limit=int(os.getenv("API_RATE_LIMIT", "10")),
            rate_limit_window=int(os.getenv("API_RATE_LIMIT_WINDOW", "60")),
            log_level=os.getenv("API_LOG_LEVEL", "INFO")
        )
        
        return cls(llm=llm_settings, api=api_settings)


# Global configuration instance
config = AppConfig.from_env()


def get_config() -> AppConfig:
    """Get the current configuration."""
    return config


# Preset configurations
PRESET_CONFIGS: Dict[PresetType, Dict[str, any]] = {
    PresetType.creative: {
        "description": "For creative writing, stories, and imaginative content",
        "temperature": 0.9,
        "top_p": 0.95,
        "max_tokens": 2000,
    },
    PresetType.balanced: {
        "description": "General purpose, balanced between creativity and accuracy",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 1000,
    },
    PresetType.precise: {
        "description": "For factual, analytical, and accurate responses",
        "temperature": 0.3,
        "top_p": 0.8,
        "max_tokens": 1000,
    },
    PresetType.deterministic: {
        "description": "For consistent, reproducible outputs",
        "temperature": 0.1,
        "top_p": 0.5,
        "max_tokens": 500,
    },
    PresetType.code: {
        "description": "Optimized for code generation and technical content",
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 1500,
    },
}

DEFAULT_PRESET = PresetType.balanced