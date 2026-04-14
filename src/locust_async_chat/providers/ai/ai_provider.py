"""
AI Message Provider for generating conversational messages using LLM.

Provides an interface compatible with LangSmithExampleProvider but generates
messages dynamically based on topics and conversation context.
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from locust_async_chat.providers.ai.topic_manager import TopicManager
from locust_async_chat.providers.ai.message_generator import MessageGenerator
from locust_async_chat.providers.ai.conversation_context import (
    ConversationContextManager,
    ConversationContext,
)

logger = logging.getLogger(__name__)


@dataclass
class AIMessage:
    """
    Represents an AI-generated message.

    Compatible with TestExample interface for easy integration.
    """

    question: str  # The generated message
    expected_answer: str = ""  # Not used for AI provider
    expected_agent: str = ""  # Not used for AI provider
    metadata: dict[str, Any] = field(default_factory=dict)
    example_id: str = ""  # Not used for AI provider
    topic: Optional[str] = None


class AIMessageProvider:
    """
    Provides AI-generated conversational messages for load testing.

    Generates messages based on topics and conversation context,
    maintaining conversation flow per user/conversation.

    Example usage:
        provider = AIMessageProvider()
        provider.initialize()

        # Get next message for a conversation
        message = provider.next_message(conversation_id="conv-123")
        print(message.question)
    """

    def __init__(
        self,
        topic_manager: Optional[TopicManager] = None,
        message_generator: Optional[MessageGenerator] = None,
        on_message_generated: Optional[Callable[[str, dict[str, Any]], None]] = None,
    ):
        """
        Initialize AI message provider.

        Args:
            topic_manager: Custom TopicManager (default: creates new one)
            message_generator: Custom MessageGenerator (default: creates new one)
            on_message_generated: Optional callback (question, metadata) when a message is generated (e.g. to sync to LangSmith)
        """
        self.topic_manager = topic_manager or TopicManager()
        if message_generator is None:
            raise ValueError("message_generator is required")
        self.message_generator = message_generator
        self.context_manager = ConversationContextManager()
        self.on_message_generated = on_message_generated
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the provider (load topics, etc.)."""
        with self._lock:
            if self._initialized:
                return

            logger.info(
                f"AI Message Provider initialized with {len(self.topic_manager.topics)} topics"
            )
            self._initialized = True

    def next_message(
        self,
        conversation_id: str,
        assistant_response: Optional[str] = None,
    ) -> AIMessage:
        """
        Get the next message for a conversation.

        Args:
            conversation_id: Unique conversation identifier
            assistant_response: The SUT's response (for follow-up messages)

        Returns:
            AIMessage instance with generated question
        """
        if not self._initialized:
            self.initialize()

        context = self.context_manager.get_or_create_context(conversation_id)

        # First message: select topic and generate initial message
        if context.is_first_message():
            topic = self.topic_manager.select_topic()
            context.set_topic(topic.name, topic.description)

            message_text = self.message_generator.generate_initial_message(
                topic_name=topic.name,
                topic_description=topic.description,
            )

            context.add_user_message(message_text)

            meta: dict[str, Any] = {
                "topic": topic.name,
                "topic_category": topic.category,
            }
            if self.on_message_generated:
                self.on_message_generated(message_text, meta)
            return AIMessage(
                question=message_text,
                topic=topic.name,
                metadata=meta,
            )

        # Follow-up message: generate based on conversation history
        if assistant_response:
            context.add_assistant_message(assistant_response)

        # Get conversation history (last 10 messages for context)
        history = context.get_conversation_history(max_messages=10)

        message_text = self.message_generator.generate_follow_up_message(
            topic_description=context.topic_description or "",
            conversation_history=history,
            assistant_response=assistant_response or "",
        )

        context.add_user_message(message_text)

        meta = {"topic": context.topic, "turn_count": context.turn_count}
        if self.on_message_generated:
            self.on_message_generated(message_text, meta)
        return AIMessage(
            question=message_text,
            topic=context.topic,
            metadata=meta,
        )

    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context for a conversation."""
        return self.context_manager.get_context(conversation_id)

    def clear_context(self, conversation_id: str) -> None:
        """Clear conversation context."""
        self.context_manager.remove_context(conversation_id)

    def clear_all_contexts(self) -> None:
        """Clear all conversation contexts."""
        self.context_manager.clear()

    # Compatibility methods for LangSmithExampleProvider interface
    def next(self) -> AIMessage:
        """
        Get next message (compatibility method).

        Note: This doesn't use conversation context. Use next_message() instead.
        """
        # For compatibility, create a temporary conversation ID
        import uuid

        temp_id = str(uuid.uuid4())
        return self.next_message(conversation_id=temp_id)

    @property
    def count(self) -> int:
        """Return number of available topics (for compatibility)."""
        return len(self.topic_manager.topics)


# Global AI provider instance
_ai_provider: Optional[AIMessageProvider] = None


def get_ai_provider() -> Optional[AIMessageProvider]:
    """Get the global AI provider instance."""
    return _ai_provider


def set_ai_provider(provider: Optional[AIMessageProvider]) -> None:
    """Set or clear the global AI provider instance (pass None to clear)."""
    global _ai_provider
    _ai_provider = provider
