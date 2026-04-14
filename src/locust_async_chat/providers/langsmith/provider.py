"""
LangSmith dataset provider for load testing.

Loads examples from a LangSmith dataset and provides them to Locust users
in a round-robin or random fashion.
"""

import random
import threading
from dataclasses import dataclass
from typing import Optional, Iterator

from langsmith import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)


@dataclass
class TestExample:
    """
    A test example from the LangSmith dataset.

    Attributes:
        question: The user's question to send to SUT
        expected_answer: Expected answer for evaluation
        expected_agent: Expected agent name (e.g., "customer_support_agent")
        metadata: Additional metadata (topic, version, etc.)
        example_id: LangSmith example ID
    """

    question: str
    expected_answer: str = ""
    expected_agent: str = ""
    metadata: dict = None  # type: ignore
    example_id: str = ""

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class LangSmithExampleProvider:
    """
    Provides test examples from a LangSmith dataset.

    Loads all examples once at initialization and provides them
    via next() in round-robin or random order.

    Example usage:
        provider = LangSmithExampleProvider("Benchmark")
        provider.load()

        # Get examples one at a time
        example = provider.next()
        print(example.question)

        # Or iterate
        for example in provider:
            print(example.question)
    """

    def __init__(
        self,
        dataset_name: str,
        question_mode: str = "first",
        shuffle: bool = True,
        seed: Optional[int] = None,
    ):
        """
        Initialize the example provider.

        Args:
            dataset_name: Name of the LangSmith dataset to load
            question_mode: How to handle list inputs - "first" or "all"
            shuffle: Whether to shuffle examples (default: True)
            seed: Random seed for reproducible shuffling
        """
        self.dataset_name = dataset_name
        self.question_mode = question_mode
        self.shuffle = shuffle
        self.seed = seed
        self._examples: list[TestExample] = []
        self._index = 0
        self._lock = threading.Lock()
        self._loaded = False

    def load(self) -> int:
        """
        Load examples from LangSmith dataset.

        Returns:
            Number of examples loaded

        Raises:
            ValueError: If dataset not found
        """
        client = Client()

        # Find dataset
        datasets = list(client.list_datasets(dataset_name=self.dataset_name))
        if not datasets:
            raise ValueError(f"Dataset '{self.dataset_name}' not found in LangSmith")

        dataset = datasets[0]

        # Load all examples
        examples = list(client.list_examples(dataset_id=dataset.id))

        self._examples = []
        for example in examples:
            inputs = example.inputs or {}
            outputs = example.outputs or {}
            metadata = example.metadata or {}

            raw_question = inputs.get("question", "")
            questions: list[str] = []
            if isinstance(raw_question, list):
                if self.question_mode == "all":
                    questions = [str(q) for q in raw_question if q]
                else:
                    questions = [str(raw_question[0])] if raw_question else []
            else:
                if raw_question:
                    questions = [str(raw_question)]

            for q in questions:
                self._examples.append(
                    TestExample(
                        question=q,
                        expected_answer=outputs.get("answer", ""),
                        expected_agent=outputs.get("agent", metadata.get("agent", "")),
                        metadata=metadata,
                        example_id=str(example.id) if example.id else "",
                    )
                )

        # Shuffle if requested
        if self.shuffle:
            rng = random.Random(self.seed)
            rng.shuffle(self._examples)

        self._loaded = True
        self._index = 0

        return len(self._examples)

    def next(self) -> TestExample:
        """
        Get the next example in round-robin order.

        Returns:
            TestExample

        Raises:
            RuntimeError: If provider not loaded or no examples available
        """
        if not self._loaded:
            raise RuntimeError("Provider not loaded. Call load() first.")

        if not self._examples:
            raise RuntimeError("No examples available in dataset")

        with self._lock:
            example = self._examples[self._index]
            self._index = (self._index + 1) % len(self._examples)

        return example

    def random(self) -> TestExample:
        """
        Get a random example.

        Returns:
            TestExample

        Raises:
            RuntimeError: If provider not loaded or no examples available
        """
        if not self._loaded:
            raise RuntimeError("Provider not loaded. Call load() first.")

        if not self._examples:
            raise RuntimeError("No examples available in dataset")

        return random.choice(self._examples)

    def get_by_index(self, index: int) -> TestExample:
        """
        Get example at a specific index.

        Args:
            index: Index of the example

        Returns:
            TestExample

        Raises:
            RuntimeError: If provider not loaded
            IndexError: If index out of bounds
        """
        if not self._loaded:
            raise RuntimeError("Provider not loaded. Call load() first.")

        return self._examples[index]

    def __len__(self) -> int:
        """Return the number of examples."""
        return len(self._examples)

    def __iter__(self) -> Iterator[TestExample]:
        """Iterate over all examples."""
        return iter(self._examples)

    def __getitem__(self, index: int) -> TestExample:
        """Get example by index."""
        return self._examples[index]

    @property
    def is_loaded(self) -> bool:
        """Check if examples have been loaded."""
        return self._loaded

    @property
    def count(self) -> int:
        """Get the number of examples."""
        return len(self._examples)

    def reset_index(self) -> None:
        """Reset the round-robin index to the beginning."""
        with self._lock:
            self._index = 0


# Global provider instance (lazy-loaded)
_provider: Optional[LangSmithExampleProvider] = None


def get_provider(dataset_name: str = "Benchmark") -> LangSmithExampleProvider:
    """
    Get the global provider instance.

    Args:
        dataset_name: Name of the LangSmith dataset

    Returns:
        LangSmithExampleProvider instance
    """
    global _provider
    if _provider is None or _provider.dataset_name != dataset_name:
        _provider = LangSmithExampleProvider(dataset_name)
    return _provider


def set_provider(provider: LangSmithExampleProvider) -> None:
    """
    Set the global provider instance.

    Args:
        provider: LangSmithExampleProvider instance to use globally
    """
    global _provider
    _provider = provider
