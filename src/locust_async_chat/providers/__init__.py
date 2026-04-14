"""
Message providers for load testing.

Provides interfaces for generating messages from various sources:
- LangSmith dataset provider
- AI-generated message provider
"""

from locust_async_chat.providers.base import MessageProvider
from locust_async_chat.providers.langsmith import (
    LangSmithExampleProvider,
    get_provider,
    set_provider,
)
from locust_async_chat.providers.ai import (
    AIMessageProvider,
    get_ai_provider,
    set_ai_provider,
)

__all__ = [
    "MessageProvider",
    "LangSmithExampleProvider",
    "AIMessageProvider",
    "get_provider",
    "set_provider",
    "get_ai_provider",
    "set_ai_provider",
]
