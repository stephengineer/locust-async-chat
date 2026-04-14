"""
Locust-based load testing module for asynchronous conversational AI agents.

This module provides load testing infrastructure for async AI systems,
including message providers, user management, webhook handling, and more.
SutAsyncUser is imported lazily so code that only needs config/users (no Locust)
doesn't trigger gevent monkey-patching (avoids RecursionError under pytest).
"""

# Export common interfaces for convenience
from locust_async_chat.config import LoadTestConfig, get_config, set_config

# Export providers
from locust_async_chat.providers import (
    MessageProvider,
    LangSmithExampleProvider,
    AIMessageProvider,
)

# Export infrastructure
from locust_async_chat.infrastructure import (
    CallbackRegistry,
    WebhookServer,
    start_server,
    stop_server,
)

# Export users (SutAsyncUser is lazy to avoid pulling in Locust/gevent)
from locust_async_chat.users import (
    UserPool,
    TestUser,
    get_user_pool,
    set_user_pool,
)

# Export models
from locust_async_chat.models import (
    CallbackPayload,
    LoginRequestPayload,
    LoginResponseUser,
    MessagePayload,
    parse_conversation_id,
    parse_correlation_id,
)


def __getattr__(name: str):
    if name == "SutAsyncUser":
        from locust_async_chat.users import SutAsyncUser

        return SutAsyncUser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# SutAsyncUser is available via lazy import: from locust_async_chat import SutAsyncUser
__all__ = [
    # Configuration
    "LoadTestConfig",
    "get_config",
    "set_config",
    # User classes
    "UserPool",
    "TestUser",
    "get_user_pool",
    "set_user_pool",
    # Providers
    "MessageProvider",
    "LangSmithExampleProvider",
    "AIMessageProvider",
    # Infrastructure
    "CallbackRegistry",
    "WebhookServer",
    "start_server",
    "stop_server",
    # Models
    "CallbackPayload",
    "LoginRequestPayload",
    "LoginResponseUser",
    "MessagePayload",
    "parse_conversation_id",
    "parse_correlation_id",
]
