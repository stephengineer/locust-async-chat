"""
LangSmith dataset writer for syncing AI-generated questions to a dataset.

When using the AI provider, optionally ensure a dataset exists per topic (create if not)
and append each generated question as an example with topic metadata.
"""

import logging
import re
import threading
from typing import Any, Optional

from langsmith import Client

logger = logging.getLogger(__name__)

DEFAULT_AI_DATASET_DESCRIPTION = "AI-generated load test questions (topic, question)"

# Safe for LangSmith dataset names (alphanumeric, underscore, hyphen)
_TOPIC_SAFE_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _topic_to_safe_suffix(topic: str) -> str:
    """Convert topic to a safe suffix for dataset name (e.g. 'appointment_booking' -> 'appointment_booking')."""
    if not topic or not str(topic).strip():
        return "unknown"
    return _TOPIC_SAFE_RE.sub("_", str(topic).strip()).strip("_") or "unknown"


class LangSmithExampleWriter:
    """
    Ensures a LangSmith dataset exists per topic and appends examples (e.g. AI-generated questions).

    Dataset name is derived from the base name and topic: "{base_name}_{topic}".
    Thread-safe for use from multiple Locust users.
    """

    def __init__(self, dataset_name: str, description: Optional[str] = None):
        """
        Args:
            dataset_name: Base name for datasets; actual name per topic is "{dataset_name}_{topic}".
            description: Optional description used when creating a new dataset.
        """
        self.dataset_name = dataset_name
        self.description = description or DEFAULT_AI_DATASET_DESCRIPTION
        self._client: Optional[Client] = None
        self._dataset_ids: dict[str, str] = {}
        self._lock = threading.Lock()

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = Client()
        return self._client

    def _full_dataset_name(self, topic: str) -> str:
        suffix = _topic_to_safe_suffix(topic)
        return f"{self.dataset_name}_{suffix}"

    def ensure_dataset(self, full_name: Optional[str] = None) -> str:
        """
        Ensure a dataset exists in LangSmith; create it if not.
        If full_name is None, uses self.dataset_name (single dataset).
        Returns the dataset ID (cached per full_name).
        """
        name = full_name or self.dataset_name
        with self._lock:
            if name in self._dataset_ids:
                return self._dataset_ids[name]
            client = self._get_client()
            datasets = list(client.list_datasets(dataset_name=name))
            if not datasets:
                logger.info("Dataset '%s' not found in LangSmith; creating...", name)
                dataset = client.create_dataset(
                    dataset_name=name,
                    description=self.description,
                )
                self._dataset_ids[name] = str(dataset.id)
                logger.info(
                    "Created dataset '%s' (ID: %s)", name, self._dataset_ids[name]
                )
            else:
                self._dataset_ids[name] = str(datasets[0].id)
                logger.debug(
                    "Using existing dataset '%s' (ID: %s)",
                    name,
                    self._dataset_ids[name],
                )
            return self._dataset_ids[name]

    def add_example(
        self,
        question: str,
        metadata: Optional[dict[str, Any]] = None,
        outputs: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Append an example to the dataset for the topic in metadata.
        Dataset name is {base_name}_{topic}. inputs: {"question": question}; metadata preserved.
        """
        if not question or not question.strip():
            return
        try:
            topic = (metadata or {}).get("topic", "unknown")
            full_name = self._full_dataset_name(topic)
            dataset_id = self.ensure_dataset(full_name)
            client = self._get_client()
            inputs = {"question": question.strip()}
            meta = dict(metadata or {})
            meta = {str(k): v for k, v in meta.items()}
            client.create_example(
                inputs=inputs,
                outputs=outputs or {},
                metadata=meta,
                dataset_id=dataset_id,
            )
            logger.debug("Synced question to LangSmith dataset '%s'", full_name)
        except Exception as e:
            logger.warning("Failed to sync question to LangSmith: %s", e)
