"""Centralized LLM client module for GPT and Claude on Azure Foundry."""

from locust_async_chat.llm.config import LLMConfig, LLMResource, load_llm_config
from locust_async_chat.llm.client import LLMClient

__all__ = [
    "LLMClient",
    "LLMConfig",
    "LLMResource",
    "load_llm_config",
    "get_llm_client",
    "set_llm_client",
]

_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient | None:
    """Get the global LLM client instance."""
    return _llm_client


def set_llm_client(client: LLMClient) -> None:
    """Set the global LLM client instance."""
    global _llm_client
    _llm_client = client
