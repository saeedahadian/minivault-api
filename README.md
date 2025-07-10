# MiniVault API

A lightweight, local REST API that simulates prompt/response generation with thoughtful engineering and clean design.

## Features

- ✅ RESTful API with `POST /generate` endpoint
- 📝 Automatic JSONL logging with nanosecond precision
- 🚀 Token-by-token streaming support
- 🛡️ Built-in rate limiting
- 📊 Hidden health metrics endpoint
- 🎯 CLI testing tool with benchmarking
- 🤖 AI-assisted development practices

## Quick Start

### Installation

```bash
# Clone the repository
cd minivault-api

# Option 1: Automatic environment setup with direnv (recommended)
# Install direnv if not already installed
brew install direnv  # On macOS
# Add direnv hook to your shell config (see https://direnv.net/docs/hook.html)
direnv allow  # This will auto-create venv and install dependencies

# Option 2: Manual setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pre-commit install
```

### Running the API

```bash
# Start the server
python app.py

# Or with auto-reload for development
uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`

### Basic Usage

#### Generate Response

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, MiniVault!"}'
```

#### Stream Response (SSE)

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me a story", "stream": true}'
```

## CLI Tool

The included CLI tool makes testing easier:

```bash
# Make it executable
chmod +x cli.py

# Generate response
./cli.py generate -p "Your prompt here"

# Stream response
./cli.py stream -p "Tell me about AI"

# Check health status
./cli.py health

# Run benchmark
./cli.py benchmark -c 100
```

## API Endpoints

### POST /generate
Generate a response for a given prompt. Supports both regular and streaming responses.

**Request:**
```json
{
  "prompt": "Your prompt text",
  "stream": false  // Optional: set to true for SSE streaming
}
```

**Response (Regular):**
```json
{
  "response": "Generated response text",
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 10,
    "total_tokens": 15
  },
  "generated_at": "2024-01-10T12:00:00"
}
```

**Response (Streaming):**
Server-Sent Events format:
```
data: {"token": "Hello", "index": 0}
data: {"token": " world", "index": 1, "usage": {...}}
data: [DONE]
```

### GET /health (Hidden)
Returns system health metrics including uptime, request count, and average response time.

## Design Choices

1. **FastAPI Framework**: Modern, fast, with automatic validation and documentation
2. **Unified Endpoint**: Single `/generate` endpoint handles both streaming and non-streaming
3. **SSE Streaming**: Standards-compliant Server-Sent Events instead of NDJSON
4. **Usage Tracking**: Token counting for prompt and completion (mimics real AI APIs)
5. **Async Everything**: Non-blocking I/O for better performance
6. **Queue-based Logging**: Ensures logging doesn't block request handling
7. **Graceful Shutdown**: Properly handles SIGTERM/SIGINT signals
8. **Code Quality**: Black formatting, pre-commit hooks, and linting integrated

## Testing

Run the test suite with pytest:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## Project Structure

```
minivault-api/
├── app.py              # Main FastAPI application
├── models.py           # Pydantic models with full type hints
├── logger.py           # Async JSONL logger implementation
├── cli.py              # Rich CLI tool for testing
├── requirements.txt    # Python dependencies
├── .envrc              # direnv configuration for auto-environment setup
├── .pre-commit-config.yaml # Code quality automation
├── tests/              # Comprehensive test suite
│   ├── conftest.py     # Shared test fixtures
│   ├── test_api.py     # API endpoint tests
│   ├── test_models.py  # Model validation tests
│   └── test_logger.py  # Logger tests
├── logs/              # Directory for JSONL logs
│   └── log.jsonl      # Append-only log file
├── DEVELOPMENT.md     # Development insights and AI collaboration notes
└── README.md          # This file
```

## Future Improvements

- Integration with local LLMs (Ollama, Hugging Face)
- Prometheus metrics export
- Request ID tracking for better debugging
- Configuration via environment variables
- More sophisticated token counting (using actual tokenizers)

## Notes

This API includes several easter eggs and thoughtful touches. Try sending "What model are you?" as a prompt! 🎉

---

Built with ❤️ and AI assistance