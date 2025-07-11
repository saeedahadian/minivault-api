# MiniVault API

A lightweight, local REST API with real AI capabilities through Ollama integration, featuring thoughtful engineering and clean design.

## Features

- ✅ RESTful API with `POST /generate` endpoint
- 🤖 Local LLM integration via Ollama (with fallback mode)
- 🎨 User-friendly presets (creative, balanced, precise, code)
- 📝 Automatic JSONL logging with nanosecond precision
- 🚀 Real token-by-token streaming from LLM
- 🛡️ Built-in rate limiting
- 📊 Hidden endpoints for health, models, and presets
- 🎯 CLI testing tool with benchmarking
- ⚙️ Full configuration via environment variables
- 🔄 Per-request model selection with preset support
- 🎲 Dynamic model selection (automatic random model choice)
- 👤 Smart resume context for personal questions

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

### Setting up Local LLM (Optional)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (choose based on your hardware)
ollama pull llama3.1:8b    # 8GB RAM recommended
ollama pull mistral:7b     # Alternative option

# Ollama will auto-start, or run manually:
ollama serve
```

### Running the API

```bash
# Start with Ollama (default)
python app.py

# Start with stub responses (no LLM required)
LLM_PROVIDER=stub python app.py

# Use a specific model
LLM_MODEL=mistral:7b python app.py

# Use dynamic model selection (picks random available model)
LLM_MODEL=auto python app.py
# OR
python app.py  # (no LLM_MODEL specified)

# Or with auto-reload for development
uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`

### Basic Usage

#### Generate Response with Presets

```bash
# Creative writing
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a story about a robot", "preset": "creative"}'

# Precise factual response
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain photosynthesis", "preset": "precise"}'

# Code generation
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a Python function to sort a list", "preset": "code"}'
```

#### Stream Response (SSE)

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me a story", "stream": true, "preset": "creative"}'
```

#### List Available Presets

```bash
curl http://localhost:8000/presets
```

## CLI Tool

The included CLI tool makes testing easier with full v2.0 feature support:

```bash
# Make it executable
chmod +x cli.py

# Generate response with preset
./cli.py generate -p "Your prompt here" --preset creative

# Generate with specific model and parameters
./cli.py generate -p "Write code" --preset code --temperature 0.1

# Stream response with system prompt
./cli.py stream -p "Tell me about AI" --system "You are an expert"

# List available presets
./cli.py presets

# List available models
./cli.py models

# Check health status
./cli.py health

# Run benchmark with preset testing
./cli.py benchmark -c 50 --preset balanced

# Compare all presets with the same prompt
./cli.py compare-presets -p "Explain quantum computing"
```

### CLI Commands

- **generate**: Send a prompt and get a response with full parameter support
- **stream**: Stream response tokens using SSE with all v2.0 features  
- **health**: Check API health status and LLM availability
- **presets**: List all available preset configurations
- **models**: List available LLM models
- **benchmark**: Run performance tests with preset/model options
- **compare-presets**: Compare responses across all presets

## API Endpoints

### POST /generate
Generate a response for a given prompt. Supports both regular and streaming responses.

**Request:**
```json
{
  "prompt": "Your prompt text",
  "stream": false,              // Optional: set to true for SSE streaming
  "preset": "balanced",         // Optional: creative, balanced, precise, deterministic, code
  "model": "llama3.1:8b",       // Optional: override default model
  "temperature": 0.7,           // Optional: 0.0-2.0 (overrides preset)
  "top_p": 0.9,                // Optional: 0.0-1.0 (overrides preset)
  "max_tokens": 1000,          // Optional: 1-4000 (overrides preset)
  "system": "You are helpful"  // Optional: system prompt
}
```

**Available Presets:**
- **creative**: High temperature (0.9) for imaginative content
- **balanced**: Default, good for general use (0.7 temperature)
- **precise**: Lower temperature (0.3) for factual content  
- **deterministic**: Very low temperature (0.1) for consistent outputs
- **code**: Optimized for code generation (0.2 temperature)

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

### Hidden Endpoints

#### GET /health
Returns system health metrics including uptime, request count, and LLM status.

#### GET /models  
Lists all available models from the LLM provider.

#### GET /presets
Lists all available preset configurations with their parameters.

## Personal Resume Feature

MiniVault API includes a smart resume context feature that automatically enhances responses to personal questions about the API creator.

### How It Works

1. **Personal Question Detection**: The API automatically detects when questions are about Saeed personally using keywords like "you", "your background", "Saeed", "Digikala", etc.

2. **Smart Context Injection**: For personal questions, the API automatically adds resume content as context to provide informed responses.

3. **Dual Mode Support**: Works with both LLM and fallback modes.

### Configuration

Create a `resume.txt` file in the project root or set environment variables:

```bash
# Option 1: Resume file (recommended)
echo "Your resume content here..." > resume.txt

# Option 2: Environment variable
export LLM_RESUME_CONTENT="Your resume content here..."

# Option 3: Custom file path
export LLM_RESUME_FILE="/path/to/your/resume.txt"
```

### Example Usage

```bash
# These questions will get resume context:
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me about your experience at Digikala"}'

curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What technologies do you work with?"}'

# Regular questions work normally:
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing"}'
```

## Design Choices

1. **FastAPI Framework**: Modern, fast, with automatic validation and documentation
2. **Unified Endpoint**: Single `/generate` endpoint handles both streaming and non-streaming
3. **SSE Streaming**: Standards-compliant Server-Sent Events instead of NDJSON
4. **Usage Tracking**: Token counting for prompt and completion (mimics real AI APIs)
5. **Async Everything**: Non-blocking I/O for better performance
6. **Queue-based Logging**: Ensures logging doesn't block request handling
7. **Graceful Shutdown**: Properly handles SIGTERM/SIGINT signals
8. **Code Quality**: Black formatting, pre-commit hooks, and linting integrated
9. **Dynamic Model Selection**: Automatically picks from available models when none specified

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

## Configuration

All settings can be configured via environment variables:

```bash
# LLM Settings
LLM_PROVIDER=ollama              # Options: ollama, stub
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b           # Default model (or "auto" for random selection)
LLM_TEMPERATURE=0.7             # Generation temperature
LLM_MAX_TOKENS=1000             # Maximum tokens to generate
LLM_RESUME_FILE=resume.txt       # Resume file for personal questions
LLM_RESUME_CONTENT="..."         # Or direct resume content
LLM_INCLUDE_THINKING=false       # Include model's thinking process in responses

# API Settings  
API_HOST=0.0.0.0
API_PORT=8000
API_RATE_LIMIT=10               # Requests per minute
```

## Project Structure

```
minivault-api/
├── app.py              # Main FastAPI application
├── models.py           # Pydantic models with full type hints
├── logger.py           # Async JSONL logger implementation
├── llm_client.py       # Ollama integration client
├── config.py           # Configuration management
├── cli.py              # Rich CLI tool for testing
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Python project configuration
├── .envrc              # direnv configuration for auto-environment setup
├── .pre-commit-config.yaml # Code quality automation
├── tests/              # Comprehensive test suite
│   ├── conftest.py     # Shared test fixtures
│   ├── test_api.py     # API endpoint tests
│   ├── test_models.py  # Model validation tests
│   └── test_logger.py  # Logger tests
├── logs/              # Directory for JSONL logs
│   └── log.jsonl      # Append-only log file
├── CLAUDE.md          # AI assistant context and guidelines
├── DEVELOPMENT.md     # Development insights and AI collaboration notes
└── README.md          # This file
```

## Version History

### v2.0.1 (Current)
- ✅ Enhanced logging with comprehensive request analytics
- ✅ Optimized streaming API (removed unnecessary null fields)
- ✅ Improved bandwidth efficiency

### v2.0.0
- ✅ User-friendly presets for common use cases
- ✅ Preset discovery endpoint  
- ✅ Preset override capability
- ✅ Major API enhancement: full LLM integration
- ⚠️  **Breaking**: New dependencies (aiohttp), new request schema

### v1.1.0
- ✅ Full Ollama integration for local LLM support
- ✅ Graceful fallback when LLM unavailable  
- ✅ Per-request model selection
- ✅ Advanced generation parameters
- ✅ Environment-based configuration
- ✅ Real token counting from LLM

### v1.0.0
- Initial release with stub responses
- SSE streaming support
- Rate limiting and logging
- Hidden health endpoint

## Future Improvements

- OpenAI API compatibility mode
- Prometheus metrics export
- Request ID tracking for better debugging
- Model performance benchmarking
- Support for more LLM providers (LLaMA.cpp, Hugging Face)

## Development Story

Curious about how this API was built through human-AI collaboration? Check out our [development journey and design insights](DEVELOPMENT.md) to see the collaborative process behind MiniVault API.

## Notes

This API includes several easter eggs and thoughtful touches. Try sending "Who are you?" as a prompt! 🎉

---

Built with ❤️ and AI assistance