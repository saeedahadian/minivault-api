"""Async JSONL logger for MiniVault API."""
import json
import asyncio
from datetime import datetime
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
        async with aiofiles.open(self.log_path, mode='a') as f:
            while True:
                entry = await self._queue.get()
                if entry is None:  # Sentinel value
                    break
                await f.write(json.dumps(entry, default=str) + '\n')
                await f.flush()
    
    async def log(self, prompt: str, response: str, usage: Usage, processing_time_ms: float, ip_address: Optional[str] = None, stream: bool = False):
        """Log an API interaction with server-side processing time."""
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            prompt=prompt,
            response=response,
            usage=usage,
            processing_time_ms=processing_time_ms,
            ip_address=ip_address,
            stream=stream
        )
        await self._queue.put(entry.model_dump())