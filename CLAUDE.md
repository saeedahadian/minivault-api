# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Preferred: Auto-setup with direnv
direnv allow  # Creates venv and installs dependencies automatically

# Manual setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the Application
```bash
python app.py                    # Basic server
uvicorn app:app --reload         # Development with auto-reload
```

### Testing
```bash
pytest tests/ -v                # Run all tests
pytest tests/test_api.py -v     # Specific test file
pytest tests/ --cov=. --cov-report=html  # With coverage
```

### CLI Tool
```bash
chmod +x cli.py
./cli.py generate -p "Your prompt"    # Generate response
./cli.py stream -p "Tell me a story"  # Stream response
./cli.py health                       # Check health
./cli.py benchmark -c 100             # Run benchmark
```

### Code Quality
```bash
black .                         # Format code
isort .                         # Sort imports
flake8 .                        # Lint code
pre-commit install              # Install pre-commit hooks
pre-commit run --all-files      # Run all hooks
```

## Architecture Overview

### Core Components
- **app.py**: Main FastAPI application with unified `/generate` endpoint
- **models.py**: Pydantic models with full type hints for request/response validation
- **logger.py**: Async JSONL logger with queue-based non-blocking writes
- **cli.py**: Rich CLI tool for testing and benchmarking

### Key Design Patterns
- **Functional Programming**: Prefer functional approaches, clean separation of concerns
- **Async/Await**: All I/O operations are async for better performance
- **Unified Endpoint**: Single `/generate` endpoint handles both streaming and non-streaming via `stream` parameter
- **SSE Streaming**: Standards-compliant Server-Sent Events format, not NDJSON
- **Queue-based Logging**: Non-blocking logging using asyncio queues
- **Graceful Shutdown**: Proper cleanup via lifespan context manager

### API Design
- **Single Endpoint**: `POST /generate` with optional `stream: true` parameter
- **Hidden Health**: `GET /health` endpoint (not in docs) for system metrics
- **Request Format**: `{"prompt": "text", "stream": false}`
- **Response Format**: Includes usage tracking (token counts) and timestamps
- **Rate Limiting**: 10 requests per minute per IP using sliding window

### Code Quality Standards
- **Black**: 88-character line length formatting
- **isort**: Import sorting with Black profile
- **flake8**: Linting with relaxed rules (E203, W503 ignored)
- **Type Hints**: Full type annotations throughout codebase
- **Pre-commit**: Automated code quality checks before commits

### Testing Strategy
- **pytest**: Main testing framework with async support
- **Test Isolation**: Temporary files for logger tests, mocked dependencies
- **Comprehensive Coverage**: API endpoints, models, logger, streaming SSE, rate limiting
- **Fixtures**: Shared test utilities in `conftest.py`

### Development Philosophy
- **Simplicity First**: Clean, readable code without over-engineering
- **Production Patterns**: Professional patterns scaled appropriately for local use
- **AI-Assisted Development**: Built through human-AI collaboration
- **Standards Compliance**: Uses established web standards (SSE, REST principles)

### Easter Eggs & Features
- Try prompt: "What model are you?" for a meta-response
- Hidden `/health` endpoint with system metrics
- AI collaboration acknowledgment in startup message
- Token counting simulates real AI API behavior

### File Structure Context
- `tests/`: Comprehensive test suite with fixtures
- `logs/`: JSONL log files (created automatically)
- `.envrc`: direnv configuration for auto-environment setup
- `.pre-commit-config.yaml`: Code quality automation configuration