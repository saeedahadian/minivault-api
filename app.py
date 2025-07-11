"""MiniVault API - A lightweight prompt/response API with AI-assisted development."""

import json
import time
import asyncio
import signal
from datetime import datetime, timezone
from typing import Dict, Optional, AsyncGenerator
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import StreamingResponse
import uvicorn

from models import GenerateRequest, GenerateResponse, HealthStatus, StreamToken, Usage, ModelInfo, ModelsResponse, PresetInfo, PresetsResponse, PresetType
from logger import AsyncLogger
from config import get_config, PRESET_CONFIGS, DEFAULT_PRESET
from llm_client import LLMClient, LLMConfig, LLMError


# Global state
logger = AsyncLogger()
start_time = datetime.now(timezone.utc)
request_count = 0
rate_limit_store: Dict[str, deque] = {}
llm_client: Optional[LLMClient] = None

# Fallback responses for when LLM is unavailable
FALLBACK_RESPONSES = {
    "default": "This is a fallback response from MiniVault API. LLM is currently unavailable.",
    "hello": "Hello! I'm MiniVault, your friendly local AI API. (Fallback mode)",
    "what model are you?": "I'm MiniVault v1.1, built with Claude's assistance through AI pair programming! (Fallback mode)",
    "test": "Test successful! MiniVault is working in fallback mode.",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global llm_client
    
    print("🚀 MiniVault API v2.0 starting up...")
    print("🤖 Developed with AI pair programming assistance")
    
    config = get_config()
    
    # Initialize logger
    await logger.start()
    
    # Initialize LLM client
    if config.llm.provider == "ollama":
        llm_config = LLMConfig(
            base_url=config.llm.base_url,
            model=config.llm.model,
            temperature=config.llm.temperature,
            top_p=config.llm.top_p,
            max_tokens=config.llm.max_tokens,
            timeout=config.llm.timeout
        )
        llm_client = LLMClient(llm_config)
        await llm_client.start()
        
        # Check LLM health
        health = await llm_client.health_check()
        if health["status"] == "healthy":
            print(f"✅ LLM ready with {len(health['models'])} models available")
        else:
            print(f"⚠️  LLM not available: {health['error']}")
            print("   Continuing with fallback responses...")
    else:
        print("📝 Running with stub responses")

    yield

    print("\n⏹️  Shutting down gracefully...")
    if llm_client:
        await llm_client.stop()
    await logger.stop()


app = FastAPI(
    title="MiniVault API",
    description="A lightweight local REST API for prompt/response generation with LLM integration",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None,  # Hide docs for a cleaner API
    redoc_url=None,
)


def check_rate_limit(ip: str, limit: int = 10, window: int = 60) -> bool:
    """Simple in-memory rate limiter."""
    now = time.time()
    if ip not in rate_limit_store:
        rate_limit_store[ip] = deque()

    # Remove old entries
    while rate_limit_store[ip] and rate_limit_store[ip][0] < now - window:
        rate_limit_store[ip].popleft()

    if len(rate_limit_store[ip]) >= limit:
        return False

    rate_limit_store[ip].append(now)
    return True


def count_tokens(text: str) -> int:
    """Simple token counting (approximation using word count)."""
    return len(text.split())


async def get_response(
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    system: Optional[str] = None,
    stream: bool = False
) -> str:
    """Get response for a given prompt using LLM or fallback."""
    global llm_client
    
    # Try LLM first
    if llm_client:
        try:
            response = await llm_client.generate(
                prompt=prompt,
                model=model,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                system=system,
                stream=stream
            )
            return response
        except LLMError as e:
            print(f"LLM error: {e}")
            # Fall through to fallback
    
    # Fallback to stub responses
    if prompt.lower() in FALLBACK_RESPONSES:
        return FALLBACK_RESPONSES[prompt.lower()]

    # Generate a "smart" fallback response based on prompt length
    if len(prompt) < 10:
        return "Your prompt is quite short. Try asking something more detailed! (Fallback mode)"
    elif len(prompt) > 100:
        return "That's a thoughtful prompt! Here's my comprehensive response to your detailed query. (Fallback mode)"
    else:
        return FALLBACK_RESPONSES["default"]


def create_usage(prompt: str, response: str) -> Usage:
    """Create usage tracking object."""
    prompt_tokens = count_tokens(prompt)
    completion_tokens = count_tokens(response)
    return Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )


@app.post("/generate")
async def generate(request: GenerateRequest, req: Request):
    """Generate a response for the given prompt. Supports streaming via SSE."""
    # Start timing the entire request
    start_time = time.perf_counter()

    global request_count
    request_count += 1

    # Rate limiting
    client_ip = req.client.host if req.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )

    # Apply preset values if specified
    temperature = request.temperature
    top_p = request.top_p
    max_tokens = request.max_tokens
    
    if request.preset:
        preset_config = PRESET_CONFIGS[request.preset]
        # Preset values are defaults, explicit values override them
        if temperature is None:
            temperature = preset_config["temperature"]
        if top_p is None:
            top_p = preset_config["top_p"]
        if max_tokens is None:
            max_tokens = preset_config["max_tokens"]
    
    # Generate response
    response_text = await get_response(
        prompt=request.prompt,
        model=request.model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        system=request.system,
        stream=request.stream
    )
    usage = create_usage(request.prompt, response_text)

    # Calculate server-side processing time (excludes logging and network response)
    processing_time_ms = (time.perf_counter() - start_time) * 1000

    # Log the interaction
    await logger.log(
        prompt=request.prompt,
        response=response_text,
        usage=usage,
        processing_time_ms=processing_time_ms,
        ip_address=client_ip,
        stream=request.stream,
    )

    if request.stream:
        # Return SSE stream
        async def sse_generator():
            """Generate SSE events."""
            if llm_client:
                try:
                    # Stream directly from LLM
                    token_count = 0
                    async for token in llm_client.generate_stream(
                        prompt=request.prompt,
                        model=request.model,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        system=request.system
                    ):
                        event_data = {
                            "token": token,
                            "index": token_count,
                            "usage": None,
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                        token_count += 1
                    
                    # Send final usage
                    final_usage = create_usage(request.prompt, response_text)
                    event_data = {
                        "token": "",
                        "index": token_count,
                        "usage": final_usage.model_dump(),
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    
                except LLMError:
                    # Fall back to simulated streaming
                    tokens = response_text.split()
                    for i, token in enumerate(tokens):
                        if i > 0:
                            token = " " + token
                        event_data = {
                            "token": token,
                            "index": i,
                            "usage": usage.model_dump() if i == len(tokens) - 1 else None,
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                        await asyncio.sleep(0.05)  # 50ms delay between tokens
            else:
                # Simulate streaming for fallback
                tokens = response_text.split()
                for i, token in enumerate(tokens):
                    if i > 0:
                        token = " " + token
                    event_data = {
                        "token": token,
                        "index": i,
                        "usage": usage.model_dump() if i == len(tokens) - 1 else None,
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    await asyncio.sleep(0.05)  # 50ms delay between tokens

            # Send completion event
            yield f"data: [DONE]\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
    else:
        # Return regular JSON response
        return GenerateResponse(response=response_text, usage=usage)


@app.get("/health", response_model=HealthStatus, include_in_schema=False)
async def health():
    """Hidden health check endpoint with system stats."""
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    # Get LLM status
    llm_status = None
    if llm_client:
        llm_status = await llm_client.health_check()

    return HealthStatus(
        uptime_seconds=uptime,
        total_requests=request_count,
        llm_status=llm_status
    )


@app.get("/models", response_model=ModelsResponse, include_in_schema=False)
async def list_models():
    """List available models."""
    if not llm_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not available"
        )
    
    try:
        model_names = await llm_client.list_models()
        models = [ModelInfo(name=name) for name in model_names]
        return ModelsResponse(models=models)
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to list models: {str(e)}"
        )


@app.get("/presets", response_model=PresetsResponse, include_in_schema=False)
async def list_presets():
    """List available preset configurations."""
    presets = []
    for preset_type, config in PRESET_CONFIGS.items():
        presets.append(PresetInfo(
            name=preset_type,
            description=config["description"],
            temperature=config["temperature"],
            top_p=config["top_p"],
            max_tokens=config["max_tokens"]
        ))
    
    return PresetsResponse(presets=presets, default=DEFAULT_PRESET)


if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "app:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload
    )
