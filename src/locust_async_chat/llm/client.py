"""Unified LLM client for GPT and Claude on Azure Foundry."""

import logging
from typing import Any

from anthropic import AnthropicFoundry
from openai import OpenAI

from locust_async_chat.llm.config import LLMConfig, LLMResource

logger = logging.getLogger(__name__)


class LLMClient:
    """Routes chat requests to the correct SDK based on the active deployment's provider."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._clients: dict[str, Any] = {}  # keyed by resource base_url

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a chat request using the active deployment.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Override config temperature (optional).
            max_tokens: Override config max_tokens (optional).

        Returns:
            Response text string.
        """
        resource = self.config.resolve_resource(self.config.deployment)
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        if resource.provider == "claude":
            return self._call_claude(messages, resource, temp, tokens)
        return self._call_gpt(messages, resource, temp, tokens)

    def _get_or_create_gpt_client(self, resource: LLMResource) -> OpenAI:
        key = resource.full_base_url
        if key not in self._clients:
            self._clients[key] = OpenAI(
                api_key=resource.api_key,
                base_url=resource.full_base_url,
                max_retries=0,
            )
        client: OpenAI = self._clients[key]
        return client

    def _get_or_create_claude_client(self, resource: LLMResource) -> AnthropicFoundry:
        key = resource.full_base_url
        if key not in self._clients:
            self._clients[key] = AnthropicFoundry(
                api_key=resource.api_key,
                base_url=resource.full_base_url,
            )
        client: AnthropicFoundry = self._clients[key]
        return client

    def _call_gpt(
        self,
        messages: list[dict[str, Any]],
        resource: LLMResource,
        temperature: float,
        max_tokens: int,
    ) -> str:
        client = self._get_or_create_gpt_client(resource)
        response = client.chat.completions.create(
            model=self.config.deployment,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_completion_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def _call_claude(
        self,
        messages: list[dict[str, Any]],
        resource: LLMResource,
        temperature: float,
        max_tokens: int,
    ) -> str:
        client = self._get_or_create_claude_client(resource)

        # Claude uses a separate 'system' param, not a system message in the list
        system_text = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": self.config.deployment,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_text:
            kwargs["system"] = system_text

        message = client.messages.create(**kwargs)
        return str(message.content[0].text)
