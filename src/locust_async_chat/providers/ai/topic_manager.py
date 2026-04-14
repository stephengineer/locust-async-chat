"""
Topic management for AI message generation.

Manages predefined topics and topic selection strategies.
"""

import random
import threading
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Topic:
    """Represents a conversation topic."""

    name: str
    description: str
    category: str = "general"


class TopicManager:
    """
    Manages conversation topics for AI message generation.

    Supports both predefined topics and LLM-generated topics.
    """

    # Predefined topics
    DEFAULT_TOPICS = [
        Topic(
            name="appointment_booking",
            description="Booking or rescheduling appointments",
            category="booking",
        ),
        Topic(
            name="service_inquiry",
            description="Asking about services offered",
            category="information",
        ),
        Topic(
            name="pricing_question",
            description="Questions about pricing and packages",
            category="sales",
        ),
        Topic(
            name="cancellation_request",
            description="Requesting to cancel a service or appointment",
            category="booking",
        ),
        Topic(
            name="technical_support",
            description="Technical issues or troubleshooting",
            category="support",
        ),
        Topic(
            name="product_recommendation",
            description="Asking for product or service recommendations",
            category="sales",
        ),
        Topic(
            name="account_management",
            description="Managing account settings or preferences",
            category="account",
        ),
        Topic(
            name="feedback_complaint",
            description="Providing feedback or filing complaints",
            category="support",
        ),
    ]

    def __init__(
        self,
        predefined_topics: Optional[List[Topic]] = None,
        selection_strategy: str = "random",
        seed: Optional[int] = None,
    ):
        """
        Initialize topic manager.

        Args:
            predefined_topics: List of predefined topics (default: DEFAULT_TOPICS)
            selection_strategy: "random" or "round_robin" (default: "random")
            seed: Random seed for reproducible selection
        """
        self.topics = predefined_topics or self.DEFAULT_TOPICS
        self.selection_strategy = selection_strategy
        self._current_index = 0
        self._random = random.Random(seed)
        self._lock = threading.Lock()

    def select_topic(self) -> Topic:
        """
        Select a topic based on the configured strategy.
        Thread-safe for concurrent use by multiple Locust users.

        Returns:
            Selected Topic instance
        """
        if not self.topics:
            raise ValueError("No topics available")

        with self._lock:
            if self.selection_strategy == "round_robin":
                topic = self.topics[self._current_index]
                self._current_index = (self._current_index + 1) % len(self.topics)
                return topic
            return self._random.choice(self.topics)

    def add_topic(self, topic: Topic) -> None:
        """Add a custom topic to the list."""
        self.topics.append(topic)

    def get_topic_by_name(self, name: str) -> Optional[Topic]:
        """Get a topic by name."""
        for topic in self.topics:
            if topic.name == name:
                return topic
        return None
