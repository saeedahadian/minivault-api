import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import app
from logger import AsyncLogger


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def temp_log_file():
    """Temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".jsonl", delete=False) as f:
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def mock_time():
    """Mock time.perf_counter for consistent timing."""
    call_count = 0

    def counter():
        nonlocal call_count
        result = 0.0 if call_count % 2 == 0 else 0.1
        call_count += 1
        return result

    with patch("time.perf_counter", side_effect=counter):
        yield


@pytest.fixture
async def async_logger(temp_log_file):
    """Async logger instance with temp file."""
    logger = AsyncLogger(temp_log_file)
    await logger.start()
    yield logger
    await logger.stop()


# Remove custom event_loop fixture to avoid deprecation warning
# pytest-asyncio will provide the event loop automatically
