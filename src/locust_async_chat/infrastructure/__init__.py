"""
Infrastructure components for load testing.

Provides core infrastructure for request/response correlation and webhook handling.
"""

from locust_async_chat.infrastructure.registry import (
    CallbackRegistry,
    PendingRequest,
    get_registry,
    set_registry,
)
from locust_async_chat.infrastructure.webhook_server import (
    WebhookServer,
    start_server,
    stop_server,
)

__all__ = [
    "CallbackRegistry",
    "PendingRequest",
    "get_registry",
    "set_registry",
    "WebhookServer",
    "start_server",
    "stop_server",
]
