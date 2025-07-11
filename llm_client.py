"""LLM Client for local model integration with Ollama."""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, List, Optional, Any
from dataclasses import dataclass

import aiohttp
from aiohttp import ClientTimeout, ClientError


logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM client."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 1000
    timeout: float = 30.0


class LLMError(Exception):
    """Base exception for LLM client errors."""
    pass


class LLMClient:
    """Async client for interacting with local LLMs via Ollama API."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._timeout = ClientTimeout(total=config.timeout)
    
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
                        "models": [model["name"] for model in data.get("models", [])]
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
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
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        stream: bool = False
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
            
            payload = {
                "model": model or self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": top_p or self.config.top_p,
                    "num_predict": max_tokens or self.config.max_tokens,
                }
            }
            
            if system:
                payload["system"] = system
            
            async with self.session.post(
                f"{self.config.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("response", "")
                else:
                    error_text = await response.text()
                    raise LLMError(f"Generation failed: HTTP {response.status} - {error_text}")
                    
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
            
            payload = {
                "model": model or self.config.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature or self.config.temperature,
                    "top_p": top_p or self.config.top_p,
                    "num_predict": max_tokens or self.config.max_tokens,
                }
            }
            
            if system:
                payload["system"] = system
            
            async with self.session.post(
                f"{self.config.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMError(f"Generation failed: HTTP {response.status} - {error_text}")
                
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'response' in data:
                                yield data['response']
                            if data.get('done', False):
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
                f"{self.config.base_url}/api/pull",
                json=payload
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                if data.get('status') == 'success':
                                    return True
                            except json.JSONDecodeError:
                                continue
                return False
        except ClientError as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False