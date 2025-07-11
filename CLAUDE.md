# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Philosophy Memories

- Always update DEVELOPMENT.md with key insights about the interaction that we have together while coding. This is going to be visible by those who evaluate my project and it is important to show them my valuable contribution during the process and indicate that this has not been a one-way interaction.
- Always be aware of README.md while making changes. This should be concise and not bloated and yet updated with the most recent changes that we made. Under no circumstances we should leave it outdated. That's horrible!

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

# With environment variables
LLM_MODEL=llama3.1:8b python app.py
LLM_PROVIDER=stub python app.py  # Use stub responses (no LLM required)
```

### Local LLM Setup (Ollama)
```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1:8b      # Recommended for 8GB RAM
ollama pull mistral:7b       # Alternative model
ollama pull codellama:7b     # For code generation

# Start Ollama service (if not auto-started)
ollama serve

# List available models
ollama list
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
- **llm_client.py**: Async client for Ollama integration with streaming support
- **config.py**: Configuration management with environment variable support

### Key Design Patterns
- **Functional Programming**: Prefer functional approaches, clean separation of concerns
- **Async/Await**: All I/O operations are async for better performance
- **Unified Endpoint**: Single `/generate` endpoint handles both streaming and non-streaming via `stream` parameter
- **SSE Streaming**: Standards-compliant Server-Sent Events format, not NDJSON
- **Queue-based Logging**: Non-blocking logging using asyncio queues
- **Graceful Shutdown**: Proper cleanup via lifespan context manager

### API Design
- **Single Endpoint**: `POST /generate` with optional `stream: true` parameter
- **Hidden Endpoints**: 
  - `GET /health` - System metrics and LLM status
  - `GET /models` - List available models
- **Request Format**: 
  ```json
  {
    "prompt": "text",
    "stream": false,
    "model": "llama3.1:8b",      // optional
    "temperature": 0.7,           // optional (0.0-2.0)
    "top_p": 0.9,                // optional (0.0-1.0)
    "max_tokens": 1000,          // optional (1-4000)
    "system": "You are helpful"  // optional system prompt
  }
  ```
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

### LLM Integration Features
- **Local LLM Support**: Full integration with Ollama for privacy-first AI
- **Fallback Mode**: Gracefully degrades to stub responses when LLM unavailable
- **Per-Request Model Selection**: Specify different models for each request
- **Advanced Parameters**: Full control over temperature, top_p, max_tokens
- **True Streaming**: Real token-by-token streaming from LLM
- **Environment Configuration**: All settings configurable via env vars

### Configuration Options
```bash
# LLM Settings
LLM_PROVIDER=ollama          # ollama, openai, stub
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.9
LLM_MAX_TOKENS=1000
LLM_TIMEOUT=30.0
LLM_SYSTEM_PROMPT="You are a helpful assistant"

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
API_RATE_LIMIT=10
API_RATE_LIMIT_WINDOW=60
```

### Easter Eggs & Features
- Try prompt: "What model are you?" for a meta-response
- Hidden endpoints for model management
- AI collaboration acknowledgment in startup message
- Real token counting from LLM responses

### File Structure Context
- `tests/`: Comprehensive test suite with fixtures
- `logs/`: JSONL log files (created automatically)
- `.envrc`: direnv configuration for auto-environment setup
- `.pre-commit-config.yaml`: Code quality automation configuration
```