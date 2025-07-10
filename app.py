"""MiniVault API - A lightweight prompt/response API with AI-assisted development."""
import json
import time
import asyncio
import signal
from datetime import datetime
from typing import Dict, Optional
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import StreamingResponse
import uvicorn

from models import GenerateRequest, GenerateResponse, HealthStatus, StreamToken, Usage
from logger import AsyncLogger


# Global state
logger = AsyncLogger()
start_time = datetime.utcnow()
request_count = 0
rate_limit_store: Dict[str, deque] = {}

# Stubbed responses with easter eggs
RESPONSES = {
    "default": "This is a generated response from MiniVault API.",
    "hello": "Hello! I'm MiniVault, your friendly local AI API.",
    "what model are you?": "I'm MiniVault v1.0, built with Claude's assistance through AI pair programming!",
    "test": "Test successful! MiniVault is working perfectly.",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    print("🚀 MiniVault API v1.0 starting up...")
    print("🤖 Developed with AI pair programming assistance")
    await logger.start()
    
    yield
    
    print("\n⏹️  Shutting down gracefully...")
    await logger.stop()


app = FastAPI(
    title="MiniVault API",
    description="A lightweight local REST API for prompt/response generation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Hide docs for a cleaner API
    redoc_url=None
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


def get_response(prompt: str) -> str:
    """Get response for a given prompt."""
    # Check for easter eggs
    if prompt.lower() in RESPONSES:
        return RESPONSES[prompt.lower()]
    
    # Generate a "smart" response based on prompt length
    if len(prompt) < 10:
        return "Your prompt is quite short. Try asking something more detailed!"
    elif len(prompt) > 100:
        return "That's a thoughtful prompt! Here's my comprehensive response to your detailed query."
    else:
        return RESPONSES["default"]


def create_usage(prompt: str, response: str) -> Usage:
    """Create usage tracking object."""
    prompt_tokens = count_tokens(prompt)
    completion_tokens = count_tokens(response)
    return Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens
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
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Generate response
    response_text = get_response(request.prompt)
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
        stream=request.stream
    )
    
    if request.stream:
        # Return SSE stream
        async def sse_generator():
            """Generate SSE events."""
            tokens = response_text.split()
            for i, token in enumerate(tokens):
                if i > 0:
                    token = " " + token
                event_data = {
                    "token": token,
                    "index": i,
                    "usage": usage.model_dump() if i == len(tokens) - 1 else None
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
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    else:
        # Return regular JSON response
        return GenerateResponse(
            response=response_text,
            usage=usage
        )




@app.get("/health", response_model=HealthStatus, include_in_schema=False)
async def health():
    """Hidden health check endpoint with system stats."""
    uptime = (datetime.utcnow() - start_time).total_seconds()
    
    return HealthStatus(
        uptime_seconds=uptime,
        total_requests=request_count
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)