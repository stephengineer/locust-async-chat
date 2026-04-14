"""
Base interface for message providers.

All message providers should implement this interface for consistency.
"""

from abc import ABC, abstractmethod
from typing import Protocol


class MessageProvider(Protocol):
    """
    Protocol for message providers.

    This allows both LangSmithExampleProvider and AIMessageProvider
    to be used interchangeably.
    """

    def next(self):
        """Get the next message/example."""
        ...

    @property
    def count(self) -> int:
        """Get the count of available messages/topics."""
        ...


class BaseMessageProvider(ABC):
    """
    Abstract base class for message providers.

    Provides a common interface that all providers should implement.
    """

    @abstractmethod
    def next(self):
        """Get the next message/example."""
        pass

    @property
    @abstractmethod
    def count(self) -> int:
        """Get the count of available messages/topics."""
        pass
