# CLAUDE.md

Development guide for AI coding assistants working on this repository.

## Project Overview

Locust-based load testing framework for asynchronous conversational AI agents. Sends chat messages to a System Under Test (SUT) and measures end-to-end latency by waiting for webhook callbacks rather than immediate HTTP responses.

## Commands

```bash
uv sync                                            # Install dependencies
uv run locust -f src/locust_async_chat/locustfile.py   # Run load test (web UI at :8089)
uv run ruff check src/                             # Lint
uv run black --check src/                          # Format check
uv run mypy src/                                   # Type check
uv run pytest                                      # Run all tests
uv run pytest tests/test_file.py::test_name -v     # Run single test
bash scripts/check.sh                              # Run all checks at once
```

## Architecture

### Core Flow

1. `SutAsyncUser` (users/user.py) logs in, acquires a test user, runs `submit_and_wait` in a loop
2. Each task gets a question from a `MessageProvider`, POSTs it to the SUT, registers a `PendingRequest` in the `CallbackRegistry`
3. SUT returns 202 + correlation ID, processes asynchronously
4. Flask webhook server (infrastructure/webhook_server.py) receives the callback, resolves the matching `AsyncResult`
5. Locust task wakes up, records end-to-end latency

### Key Modules (`src/locust_async_chat/`)

| Module | Purpose |
|--------|---------|
| `locustfile.py` | Entry point. Lifecycle hooks for config, webhook server, cleanup |
| `config/` | `LoadTestConfig` dataclass. Layered: env vars -> CLI args -> defaults |
| `users/` | `SutAsyncUser` (HttpUser subclass) + `UserPool` (thread-safe user generation) |
| `infrastructure/` | `CallbackRegistry` (gevent AsyncResult correlation) + Flask webhook server |
| `providers/` | Strategy pattern: `LangSmithExampleProvider` or `AIMessageProvider` |
| `models/` | Dataclasses for messages, callbacks, login payloads, response parsers |
| `llm/` | Multi-resource LLM client supporting OpenAI and Anthropic providers |

### Concurrency Model

Pure gevent green threads -- no async/await. The webhook Flask server, user simulation, and registry cleanup all run as gevent greenlets. Threading locks protect shared state in the registry.

## Docker

```bash
docker build -t locust-async-chat:local .
docker run --rm --env-file .env -p 8089:8089 -p 44379:44379 locust-async-chat:local
```

## Configuration

Copy `.env.example` to `.env` and fill in required values. Key env vars: `LOADTEST_SUT_AUTH_HEADER`, `LOADTEST_SUT_LOGIN_URL`, `LOADTEST_SUT_SUBMIT_URL`. All settings are also configurable via Locust CLI args (see `config/config.py`).
