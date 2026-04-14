"""LLM-based message generation for conversational load testing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from locust_async_chat.llm.client import LLMClient

from locust_async_chat.providers.ai.prompts import (
    INITIAL_MESSAGE_PROMPT_TEMPLATE,
    FOLLOW_UP_MESSAGE_PROMPT_TEMPLATE,
    format_conversation_history,
)

logger = logging.getLogger(__name__)


class MessageGenerator:
    """Generates conversational messages using an LLMClient.

    Supports both initial messages (from topic) and follow-up messages
    (based on conversation history).
    """

    def __init__(self, client: LLMClient) -> None:
        """Initialize message generator.

        Args:
            client: An LLMClient instance with a chat(messages, **kwargs) -> str method.
        """
        self.client = client

    def generate_initial_message(self, topic_name: str, topic_description: str) -> str:
        """Generate the first message in a conversation based on topic.

        Args:
            topic_name: Name of the conversation topic
            topic_description: Description of the topic

        Returns:
            Generated user message string
        """
        prompt = INITIAL_MESSAGE_PROMPT_TEMPLATE.format(
            topic_name=topic_name,
            topic_description=topic_description,
        )

        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
            message = self.client.chat(messages)
            logger.debug(
                f"Generated initial message for topic '{topic_name}': {message}"
            )
            return message

        except Exception as e:
            logger.error(f"Failed to generate initial message: {e}")
            return f"I'd like to know more about {topic_description.lower()}."

    def generate_follow_up_message(
        self,
        topic_description: str,
        conversation_history: list,
        assistant_response: str,
    ) -> str:
        """Generate a follow-up message based on conversation history.

        Args:
            topic_description: Description of the conversation topic
            conversation_history: List of previous messages
            assistant_response: The most recent assistant (SUT) response

        Returns:
            Generated user message string
        """
        history_str = format_conversation_history(conversation_history)

        prompt = FOLLOW_UP_MESSAGE_PROMPT_TEMPLATE.format(
            topic_description=topic_description,
            conversation_history=history_str,
            assistant_response=assistant_response,
        )

        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
            message = self.client.chat(messages)
            logger.debug(f"Generated follow-up message: {message}")
            return message

        except Exception as e:
            logger.error(f"Failed to generate follow-up message: {e}")
            return "Thank you, that helps."
