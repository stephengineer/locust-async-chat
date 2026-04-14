"""
AI Provider module for generating conversational messages using LLM.

This module provides:
- Topic management (predefined + LLM-generated)
- LLM-based message generation
- Conversation context tracking
- Main provider interface compatible with LangSmithExampleProvider
"""

from locust_async_chat.providers.ai.ai_provider import (
    AIMessage,
    AIMessageProvider,
    get_ai_provider,
    set_ai_provider,
)
from locust_async_chat.providers.ai.topic_manager import TopicManager
from locust_async_chat.providers.ai.message_generator import MessageGenerator
from locust_async_chat.providers.ai.conversation_context import ConversationContext

__all__ = [
    "AIMessage",
    "AIMessageProvider",
    "TopicManager",
    "MessageGenerator",
    "ConversationContext",
    "get_ai_provider",
    "set_ai_provider",
]
