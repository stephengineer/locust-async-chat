# locust-async-chat: A Technical Overview

## Abstract

locust-async-chat is a load testing framework designed specifically for asynchronous conversational AI systems. Unlike traditional load testing tools that measure synchronous HTTP round-trip time, locust-async-chat measures true end-to-end latency for systems where a user message is accepted immediately (HTTP 202) and the actual AI response arrives later via webhook callback. locust-async-chat builds on Locust, an open-source load testing framework, and extends it with a webhook receiver, a request/response correlation registry, and pluggable message providers that can replay static datasets or generate dynamic multi-turn conversations using LLMs.

## 1. Problem Statement

### 1.1 The Async Chat Pattern

Modern conversational AI systems frequently adopt an asynchronous architecture:

1. A client sends a user message to the chat API
2. The API acknowledges the request immediately (HTTP 200/202) with a correlation ID
3. The AI agent processes the message -- potentially invoking tools, retrieving documents, or reasoning over multiple steps
4. When processing is complete, the system delivers the response via a webhook callback to a pre-registered URL

This pattern is common in production chat systems because AI agent processing time is unpredictable. A simple FAQ lookup might complete in under a second, while a complex multi-step agent workflow might take 30 seconds or more. The async pattern prevents HTTP timeouts and allows the system to manage backpressure gracefully.

### 1.2 The Load Testing Gap

Standard load testing tools (Locust, k6, JMeter, Artillery) are designed around the synchronous request/response model. They measure the time between sending a request and receiving the HTTP response. For an async chat system, this only captures the time to return `202 Accepted` -- typically a few milliseconds -- and tells you nothing about the actual end-to-end experience.

What we actually need to measure is the time from sending the user's message to receiving the AI's response via webhook. This requires:

- An HTTP server running alongside the load test to receive webhook callbacks
- A correlation mechanism to match each callback to the original request
- Latency recording that spans from the initial POST to the webhook arrival
- All of this running at scale under concurrent simulated users

locust-async-chat solves exactly this problem.

## 2. Design Decisions

### 2.1 Why Locust?

locust-async-chat builds on Locust rather than implementing a load testing framework from scratch. The key reasons:

- **Gevent-based concurrency**: Locust uses gevent green threads, which are lightweight, cooperative, and run in a single OS thread. This is a natural fit for our wait-for-callback pattern -- a green thread can block on an `AsyncResult` without consuming OS resources
- **Built-in web UI**: Locust provides a real-time web dashboard showing request rates, latency distributions, and failure counts. locust-async-chat hooks into the same event system to report end-to-end latency alongside HTTP latency
- **Extensible lifecycle**: Locust exposes lifecycle hooks (`init`, `test_start`, `quitting`) that locust-async-chat uses to start/stop the webhook server and manage configuration
- **Custom request types**: Locust's `events.request.fire()` API allows locust-async-chat to report `ASYNC/e2e` as a custom request type alongside the built-in HTTP metrics

### 2.2 Why gevent, Not asyncio?

Locust is built on gevent, and locust-async-chat stays within that model. The webhook Flask server, the callback registry, and all user simulations run as gevent greenlets in a single process. This avoids:

- The complexity of mixing asyncio and threading
- The need for inter-process communication between the load generator and the webhook receiver
- Event loop coordination between different async runtimes

The tradeoff is that locust-async-chat cannot use async libraries that require asyncio. In practice, this has not been a limitation -- the HTTP client (requests), Flask, and gevent WSGI server cover all needs.

### 2.3 Single-Process Architecture

The webhook server runs in the same process as Locust. This is a deliberate choice:

- **Simplicity**: No need for message queues or shared databases to correlate requests with callbacks
- **In-memory correlation**: The `CallbackRegistry` is a simple Python dictionary protected by a threading lock. When a webhook arrives, it resolves the corresponding `AsyncResult` in microseconds
- **Zero-copy**: The webhook payload is passed directly to the waiting green thread without serialization

The limitation is that the webhook server must be reachable from the SUT. In production deployments, this means the load test host needs a public or tunneled URL that the SUT can reach.

## 3. Architecture

### 3.1 Component Overview

```
+--------------------------------------------------------------------+
|                        Locust Process                               |
|                                                                     |
|  +-----------------+    +------------------+    +----------------+  |
|  | LoadTestConfig  |    | UserPool         |    | MessageProvider|  |
|  | (env + CLI)     |    | (Doe1, Doe2...)  |    | (LangSmith/AI) |  |
|  +-----------------+    +------------------+    +----------------+  |
|                                                                     |
|  +--------------------------------------------------------------+  |
|  |                    SutAsyncUser (per greenlet)                |  |
|  |                                                               |  |
|  |  1. Login -> get conversation_id                              |  |
|  |  2. Get question from MessageProvider                         |  |
|  |  3. Build MessagePayload                                      |  |
|  |  4. Register in CallbackRegistry                              |  |
|  |  5. POST to SUT                                               |  |
|  |  6. Block on AsyncResult.get(timeout)                         |  |
|  |  7. Record e2e latency                                        |  |
|  +--------------------------------------------------------------+  |
|                                                                     |
|  +--------------------------------------------------------------+  |
|  |                    CallbackRegistry                           |  |
|  |                                                               |  |
|  |  { "corr-id-1": PendingRequest(AsyncResult), ... }           |  |
|  |                                                               |  |
|  |  register(id) -> PendingRequest                               |  |
|  |  resolve(id, payload) -> sets AsyncResult, wakes greenlet     |  |
|  |  expire_old_entries() -> TTL cleanup                          |  |
|  +--------------------------------------------------------------+  |
|                                                                     |
|  +--------------------------------------------------------------+  |
|  |                   WebhookServer (Flask + gevent WSGI)         |  |
|  |                                                               |  |
|  |  POST /webhooks/chat-complete -> parse correlationID          |  |
|  |                                -> registry.resolve(id, data)  |  |
|  |  GET  /health -> {"status": "ok", "pending": N}              |  |
|  +--------------------------------------------------------------+  |
+--------------------------------------------------------------------+
```

### 3.2 The Callback Registry

The `CallbackRegistry` is the central coordination mechanism. It is a thread-safe dictionary mapping correlation IDs to `PendingRequest` objects, each containing a gevent `AsyncResult`.

**Registration (Locust user greenlet):**
```python
pending = registry.register(request_id="corr-123", question="Book an appointment")
# pending.async_result is an unresolved gevent.AsyncResult
```

**Resolution (webhook server greenlet):**
```python
registry.resolve(request_id="corr-123", payload={...})
# This calls pending.async_result.set(payload), which immediately wakes
# the blocked green thread
```

**Waiting (Locust user greenlet):**
```python
callback_data = pending.async_result.get(timeout=90)
# Green thread yields here; gevent schedules other greenlets
# When resolve() is called, this returns instantly
```

The registry also runs a background cleanup greenlet that expires entries older than 2x the configured timeout. This prevents memory leaks when the SUT fails to deliver callbacks.

### 3.3 The Webhook Server

A lightweight Flask application served by gevent's WSGI server. It runs in a background greenlet and handles:

- **Payload parsing**: Extracts the `correlationID` from the callback JSON
- **Switchboard filtering**: Optionally filters callbacks by switchboard name (configurable via `--sut-switchboard-name`), useful when the SUT sends callbacks for multiple bot types
- **Content type filtering**: Ignores non-text content types and echo-back messages from user authors
- **HMAC signature verification**: Optional webhook authentication via `X-Webhook-Signature` header

### 3.4 User Simulation Lifecycle

Each `SutAsyncUser` (a Locust `HttpUser` subclass) follows this lifecycle:

1. **on_start**: Acquire a test user from the `UserPool`, log in to the SUT, store the conversation ID and user profile
2. **submit_and_wait** (repeated task): Get a question, POST it, wait for the webhook callback, record metrics
3. **on_stop**: Cleanup

The `UserPool` generates test users with sequential surnames (Doe1, Doe2, ...) and is thread-safe for concurrent acquisition.

## 4. Message Providers

locust-async-chat uses a strategy pattern for message generation. Both providers implement the `MessageProvider` protocol (`next()` and `count` property).

### 4.1 LangSmith Dataset Provider

Loads questions from a LangSmith dataset at startup. Questions are shuffled and served in round-robin order. Each example includes:

- `question`: The user message to send
- `expected_answer`: For evaluation (not used during load testing)
- `expected_agent`: Expected agent handler name
- `metadata`: Arbitrary metadata (topic, version, etc.)

This provider is deterministic and good for repeatable benchmarks.

### 4.2 AI Message Provider

Generates dynamic, multi-turn conversations using an LLM. The architecture:

```
TopicManager -> selects a topic (e.g., "appointment_booking")
     |
     v
MessageGenerator -> generates initial message from topic
     |
     v
ConversationContext -> stores message history per conversation
     |
     v
MessageGenerator -> generates follow-up based on history + SUT response
```

**Topic management**: 8 predefined topics (appointment booking, service inquiry, pricing, cancellation, technical support, product recommendation, account management, feedback). Topics are selected via `random` or `round_robin` strategy.

**Multi-turn flow**: After the SUT responds, the AI provider feeds the response back to the LLM to generate a contextually appropriate follow-up. This creates realistic conversation flows rather than isolated one-shot questions.

**LLM client**: A unified client that routes requests to OpenAI or Anthropic SDKs based on deployment configuration. Supports multiple Azure Foundry resources with automatic routing by deployment name.

**LangSmith sync**: Optionally writes generated questions back to LangSmith (one dataset per topic) for later use as static benchmarks.

## 5. Configuration System

locust-async-chat uses a layered configuration approach:

```
Environment Variables (.env)
        |
        v
    CLI Arguments (Locust --arg flags)
        |
        v
    Locust Web UI (runtime overrides)
        |
        v
    LoadTestConfig dataclass
```

The `LoadTestConfig` dataclass is the single source of truth at runtime. It is rebuilt from environment variables and CLI options each time a test starts from the UI, allowing operators to change settings (provider type, LLM deployment, wait times) between test runs without restarting the process.

CLI arguments are registered via Locust's `@events.init_command_line_parser` hook. This integrates them into Locust's own argument parser and web UI, so they appear alongside Locust's built-in options.

## 6. Metrics and Observability

locust-async-chat reports two categories of metrics through Locust's event system:

| Metric | Type | What it measures |
|--------|------|-----------------|
| `login` | HTTP | Time for the login POST to return |
| `submit` | HTTP | Time for the message POST to return (usually ~200ms) |
| `e2e` | ASYNC | Time from message POST to webhook callback (the real latency) |

The `e2e` metric is the primary indicator of SUT performance under load. It captures the full processing pipeline: message queuing, AI agent execution, tool calls, response generation, and webhook delivery.

All metrics appear in Locust's real-time web dashboard with percentile distributions, request rates, and failure tracking.

## 7. Extensibility

### 7.1 Adding a New Message Provider

Implement the `MessageProvider` protocol:

```python
class CustomProvider:
    def next(self) -> YourMessageType:
        # Return an object with .question, .expected_agent, .metadata
        ...

    @property
    def count(self) -> int:
        ...
```

The message object needs `question` (str), `expected_agent` (str), and `metadata` (dict) attributes.

### 7.2 Adapting to a Different SUT API

The SUT-specific logic is concentrated in three places:

1. **`models/login.py`**: Login request/response payload structure
2. **`models/message.py`**: Message payload builder (`to_dict()`)
3. **`infrastructure/webhook_server.py`**: Callback payload parsing and correlation ID extraction

To adapt locust-async-chat to a different SUT, modify these models to match your API's JSON schema. The core infrastructure (registry, user lifecycle, metrics) is SUT-agnostic.

### 7.3 Adding a New LLM Provider

The `LLMClient` routes by the `provider` field on each `LLMResource`. To add a new provider:

1. Add a provider key to `PROVIDER_PATH_SUFFIXES` in `llm/config.py`
2. Add a `_call_<provider>` method to `LLMClient` in `llm/client.py`
3. Configure it via `LLM_RESOURCE_N_PROVIDER=<key>` in `.env`

## 8. Deployment

### 8.1 Local

```bash
uv sync
cp .env.example .env  # fill in SUT URLs
uv run locust -f src/locust_async_chat/locustfile.py
```

### 8.2 Docker

```bash
docker build -t locust-async-chat .
docker run --rm --env-file .env -p 8089:8089 -p 44379:44379 locust-async-chat
```

Port 8089 serves the Locust web UI. Port 44379 receives webhook callbacks from the SUT.

### 8.3 Cloud Deployment

For cloud deployment, ensure:

- The webhook port (44379) is reachable from the SUT's network
- Environment variables are injected at runtime (never baked into the image)
- The SUT is configured to send callbacks to `http://<load-test-host>:44379/webhooks/chat-complete`

## 9. Limitations and Future Work

**Current limitations:**

- **Single-process webhook server**: The webhook server runs in the same Locust worker. In distributed Locust mode (multiple workers), each worker would need its own webhook server and the SUT would need to route callbacks to the correct worker
- **SUT-specific payload models**: The login, message, and callback models are tightly coupled to a specific API schema. Making these fully pluggable (e.g., via configuration-driven payload templates) would improve portability
- **No built-in response validation**: locust-async-chat measures latency but does not evaluate response quality. Integration with evaluation frameworks (e.g., comparing responses against expected answers from LangSmith datasets) is a natural extension

**Potential future directions:**

- Distributed webhook routing for multi-worker Locust deployments
- Configuration-driven payload templates to support arbitrary SUT APIs without code changes
- Response quality evaluation integrated into the metrics pipeline
- WebSocket and SSE transport support for streaming responses
- Conversation scenario scripting (branching flows, conditional messages)

## 10. Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Load testing | Locust 2.x | User simulation, metrics, web UI |
| Concurrency | gevent | Green threads, AsyncResult, WSGI |
| Webhook server | Flask + gevent WSGI | Receive SUT callbacks |
| LLM client | OpenAI SDK, Anthropic SDK | AI message generation |
| Dataset management | LangSmith | Static question datasets |
| Configuration | python-dotenv | Environment variable loading |
| Package management | uv + hatchling | Fast dependency resolution and builds |
| CI | GitHub Actions | Lint, type check, test, Docker build |
| Linting | ruff, black | Code style |
| Type checking | mypy | Static type analysis |
| Testing | pytest | 133 unit tests |
