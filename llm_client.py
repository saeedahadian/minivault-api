"""LLM Client for local model integration with Ollama."""

import asyncio
import json
import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp
from aiohttp import ClientError, ClientTimeout

logger = logging.getLogger(__name__)


def clean_response(text: str, include_thinking: bool = False) -> str:
    """Remove <think> tags and their content from response text.

    This removes the model's internal reasoning process that appears
    in <think>...</think> tags, providing clean user-facing responses.

    Args:
        text: Raw response text from the model
        include_thinking: If True, preserves <think> tags; if False, removes them
    """
    if not text or include_thinking:
        return text

    # Remove <think>...</think> blocks including nested content
    # Using re.DOTALL to match newlines within think blocks
    pattern = r"<think>.*?</think>"
    cleaned = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)

    # Clean up any extra whitespace that might be left
    cleaned = re.sub(r"\n\s*\n", "\n\n", cleaned)  # Multiple newlines to double
    cleaned = cleaned.strip()

    return cleaned


@dataclass
class LLMConfig:
    """Configuration for LLM client."""

    base_url: str = "http://localhost:11434"
    model: Optional[str] = None  # None means use random available model
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 1000
    timeout: float = 30.0
    include_thinking: bool = False


class LLMError(Exception):
    """Base exception for LLM client errors."""

    pass


class LLMClient:
    """Async client for interacting with local LLMs via Ollama API."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._timeout = ClientTimeout(total=config.timeout)

        # Model caching for dynamic selection
        self._cached_models: List[str] = []
        self._models_cache_time: float = 0
        self._models_cache_ttl: float = 60.0  # Cache for 60 seconds

    async def start(self) -> None:
        """Initialize the HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=self._timeout)

    async def stop(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def health_check(self) -> Dict[str, Any]:
        """Check if Ollama is running and accessible."""
        try:
            if not self.session:
                await self.start()

            async with self.session.get(f"{self.config.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "models": [model["name"] for model in data.get("models", [])],
                    }
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_models(self) -> List[str]:
        """List available models."""
        try:
            if not self.session:
                await self.start()

            async with self.session.get(f"{self.config.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return [model["name"] for model in data.get("models", [])]
                else:
                    raise LLMError(f"Failed to list models: HTTP {response.status}")
        except ClientError as e:
            raise LLMError(f"Failed to connect to Ollama: {e}")

    async def get_random_available_model(self) -> Optional[str]:
        """Get a random model from available models, with caching."""
        current_time = time.time()

        # Check if cache is still valid
        if (
            current_time - self._models_cache_time
        ) < self._models_cache_ttl and self._cached_models:
            selected_model = random.choice(self._cached_models)
            logger.debug(f"Using cached model list, selected: {selected_model}")
            return selected_model

        # Refresh cache
        try:
            models = await self.list_models()
            if models:
                self._cached_models = models
                self._models_cache_time = current_time
                selected_model = random.choice(models)
                logger.info(
                    f"No model specified, selected random model: {selected_model}"
                )
                return selected_model
            else:
                logger.warning("No models available for dynamic selection")
                return None
        except LLMError as e:
            logger.warning(f"Failed to get available models for dynamic selection: {e}")
            return None

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        """Generate a response for the given prompt."""
        if stream:
            # For streaming, collect all tokens
            tokens = []
            async for token in self.generate_stream(
                prompt, model, temperature, top_p, max_tokens, system
            ):
                tokens.append(token)
            return "".join(tokens)

        try:
            if not self.session:
                await self.start()

            # Determine which model to use
            selected_model = model or self.config.model
            if not selected_model:
                # No model specified, try to get a random one
                selected_model = await self.get_random_available_model()
                if not selected_model:
                    raise LLMError("No models available for generation")

            payload = {
                "model": selected_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": top_p or self.config.top_p,
                    "num_predict": max_tokens or self.config.max_tokens,
                },
            }

            if system:
                payload["system"] = system

            async with self.session.post(
                f"{self.config.base_url}/api/generate", json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    raw_response = data.get("response", "")
                    return clean_response(raw_response, self.config.include_thinking)
                else:
                    error_text = await response.text()
                    raise LLMError(
                        f"Generation failed: HTTP {response.status} - {error_text}"
                    )

        except ClientError as e:
            raise LLMError(f"Failed to connect to Ollama: {e}")

    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response for the given prompt."""
        try:
            if not self.session:
                await self.start()

            # Determine which model to use
            selected_model = model or self.config.model
            if not selected_model:
                # No model specified, try to get a random one
                selected_model = await self.get_random_available_model()
                if not selected_model:
                    raise LLMError("No models available for generation")

            payload = {
                "model": selected_model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": top_p or self.config.top_p,
                    "num_predict": max_tokens or self.config.max_tokens,
                },
            }

            if system:
                payload["system"] = system

            async with self.session.post(
                f"{self.config.base_url}/api/generate", json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMError(
                        f"Generation failed: HTTP {response.status} - {error_text}"
                    )

                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            if "response" in data:
                                raw_token = data["response"]
                                cleaned_token = clean_response(
                                    raw_token, self.config.include_thinking
                                )
                                if (
                                    cleaned_token
                                ):  # Only yield if there's content after cleaning
                                    yield cleaned_token
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON line: {line}")
                            continue

        except ClientError as e:
            raise LLMError(f"Failed to connect to Ollama: {e}")

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            if not self.session:
                await self.start()

            payload = {"name": model_name}

            async with self.session.post(
                f"{self.config.base_url}/api/pull", json=payload
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode("utf-8"))
                                if data.get("status") == "success":
                                    return True
                            except json.JSONDecodeError:
                                continue
                return False
        except ClientError as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
