import asyncio
import json
from datetime import datetime
from pathlib import Path

import pytest

from logger import AsyncLogger
from models import Usage


@pytest.mark.asyncio
async def test_logger_start_stop(temp_log_file):
    """Test logger start and stop functionality."""
    logger = AsyncLogger(temp_log_file)
    await logger.start()
    assert logger._queue is not None
    assert logger._task is not None
    await logger.stop()
    assert logger._task.done()


@pytest.mark.asyncio
async def test_logger_creates_directory(temp_log_file):
    """Test logger creates directory if it doesn't exist."""
    log_path = Path(temp_log_file).parent / "new_dir" / "test.jsonl"
    logger = AsyncLogger(str(log_path))
    await logger.start()

    usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
    await logger.log("test", "response", usage, 100.0)

    await logger.stop()
    assert log_path.exists()
    log_path.unlink()
    log_path.parent.rmdir()


@pytest.mark.asyncio
async def test_logger_writes_json_line(temp_log_file):
    """Test logger writes proper JSONL format."""
    logger = AsyncLogger(temp_log_file)
    await logger.start()

    usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
    await logger.log("Hello", "Hi there", usage, 100.0, "127.0.0.1", True)

    await logger.stop()

    with open(temp_log_file, "r") as f:
        line = f.readline().strip()
        data = json.loads(line)

        assert data["prompt"] == "Hello"
        assert data["response"] == "Hi there"
        assert data["usage"]["total_tokens"] == 15
        assert data["processing_time_ms"] == 100.0
        assert data["ip_address"] == "127.0.0.1"
        assert data["stream"] is True


@pytest.mark.asyncio
async def test_logger_multiple_entries(temp_log_file):
    """Test logger handles multiple log entries."""
    logger = AsyncLogger(temp_log_file)
    await logger.start()

    usage1 = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
    usage2 = Usage(prompt_tokens=8, completion_tokens=12, total_tokens=20)

    await logger.log("First", "Response 1", usage1, 100.0)
    await logger.log("Second", "Response 2", usage2, 150.0)

    await logger.stop()

    with open(temp_log_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2

        data1 = json.loads(lines[0])
        data2 = json.loads(lines[1])

        assert data1["prompt"] == "First"
        assert data2["prompt"] == "Second"
        assert data1["usage"]["total_tokens"] == 15
        assert data2["usage"]["total_tokens"] == 20


@pytest.mark.asyncio
async def test_logger_handles_special_characters(temp_log_file):
    """Test logger handles special characters in JSON."""
    logger = AsyncLogger(temp_log_file)
    await logger.start()

    usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
    await logger.log('Hello "world"', "Hi\nthere", usage, 100.0)

    await logger.stop()

    with open(temp_log_file, "r") as f:
        line = f.readline().strip()
        data = json.loads(line)

        assert data["prompt"] == 'Hello "world"'
        assert data["response"] == "Hi\nthere"


@pytest.mark.asyncio
async def test_logger_graceful_shutdown(temp_log_file):
    """Test logger processes all queued items before shutdown."""
    logger = AsyncLogger(temp_log_file)
    await logger.start()

    usage = Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15)

    # Add multiple items quickly
    for i in range(5):
        await logger.log(f"Prompt {i}", f"Response {i}", usage, 100.0)

    await logger.stop()

    with open(temp_log_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 5

        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["prompt"] == f"Prompt {i}"
