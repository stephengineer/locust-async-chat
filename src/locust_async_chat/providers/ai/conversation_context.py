"""
Conversation context tracking for AI message generation.

Maintains conversation history per user/conversation.
"""

import threading
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Message:
    """Represents a message in the conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationContext:
    """
    Tracks conversation history for a user/conversation.

    Maintains message history and topic information.
    """

    conversation_id: str
    topic: Optional[str] = None
    topic_description: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    turn_count: int = 0

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self.messages.append(Message(role="user", content=content))
        self.turn_count += 1

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant (SUT) message to the conversation."""
        self.messages.append(Message(role="assistant", content=content))

    def set_topic(self, topic_name: str, topic_description: str) -> None:
        """Set the conversation topic."""
        self.topic = topic_name
        self.topic_description = topic_description

    def get_conversation_history(
        self, max_messages: Optional[int] = None
    ) -> List[Message]:
        """
        Get conversation history.

        Args:
            max_messages: Maximum number of recent messages to return (None = all)

        Returns:
            List of messages in chronological order
        """
        if max_messages is None:
            return self.messages.copy()
        return self.messages[-max_messages:] if max_messages > 0 else []

    def is_first_message(self) -> bool:
        """Check if this is the first user message."""
        return self.turn_count == 0


class ConversationContextManager:
    """
    Manages conversation contexts for multiple users/conversations.

    Thread-safe storage of conversation contexts.
    """

    def __init__(self) -> None:
        """Initialize the context manager."""
        self._contexts: dict[str, ConversationContext] = {}
        self._lock = threading.Lock()

    def get_or_create_context(self, conversation_id: str) -> ConversationContext:
        """
        Get existing context or create a new one.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            ConversationContext instance
        """
        with self._lock:
            if conversation_id not in self._contexts:
                self._contexts[conversation_id] = ConversationContext(
                    conversation_id=conversation_id
                )
            return self._contexts[conversation_id]

    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get context by conversation ID."""
        with self._lock:
            return self._contexts.get(conversation_id)

    def remove_context(self, conversation_id: str) -> None:
        """Remove a conversation context."""
        with self._lock:
            self._contexts.pop(conversation_id, None)

    def clear(self) -> None:
        """Clear all contexts."""
        with self._lock:
            self._contexts.clear()
