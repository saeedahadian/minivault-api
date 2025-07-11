"""Async JSONL logger for MiniVault API."""

import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import aiofiles
from models import LogEntry, Usage


class AsyncLogger:
    """Asynchronous logger for API interactions."""

    def __init__(self, log_path: str = "logs/log.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(exist_ok=True)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the logger background task."""
        self._task = asyncio.create_task(self._writer())

    async def stop(self):
        """Stop the logger gracefully."""
        if self._task:
            await self._queue.put(None)  # Sentinel value
            await self._task

    async def _writer(self):
        """Background task to write logs."""
        async with aiofiles.open(self.log_path, mode="a") as f:
            while True:
                entry = await self._queue.get()
                if entry is None:  # Sentinel value
                    break
                await f.write(json.dumps(entry, default=str) + "\n")
                await f.flush()

    async def log(
        self,
        prompt: str,
        response: str,
        usage: Usage,
        processing_time_ms: float,
        ip_address: Optional[str] = None,
        stream: bool = False,
        # Enhanced logging parameters
        preset_used: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature_used: Optional[float] = None,
        top_p_used: Optional[float] = None,
        max_tokens_used: Optional[int] = None,
        system_prompt: Optional[str] = None,
        llm_provider: str = "stub",
        fallback_used: bool = False,
    ):
        """Log an API interaction with comprehensive request details."""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            prompt=prompt,
            response=response,
            usage=usage,
            processing_time_ms=processing_time_ms,
            ip_address=ip_address,
            stream=stream,
            preset_used=preset_used,
            model_name=model_name,
            temperature_used=temperature_used,
            top_p_used=top_p_used,
            max_tokens_used=max_tokens_used,
            system_prompt=system_prompt,
            llm_provider=llm_provider,
            fallback_used=fallback_used,
        )
        await self._queue.put(entry.model_dump())
