from unittest.mock import MagicMock, patch

from locust_async_chat.llm.config import LLMResource, LLMConfig
from locust_async_chat.llm.client import LLMClient


def _gpt_resource():
    return LLMResource(
        base_url="https://res-a.openai.azure.com",
        api_key="key-a",
        provider="gpt",
        deployments=["gpt-5.4"],
    )


def _claude_resource():
    return LLMResource(
        base_url="https://res-b.openai.azure.com",
        api_key="key-b",
        provider="claude",
        deployments=["claude-sonnet-4-6"],
    )


class TestLLMClientGPT:
    @patch("locust_async_chat.llm.client.OpenAI")
    def test_chat_routes_to_gpt(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Paris"
        mock_client.chat.completions.create.return_value = mock_response

        config = LLMConfig(
            resources=[_gpt_resource()],
            deployment="gpt-5.4",
        )
        client = LLMClient(config)
        result = client.chat([{"role": "user", "content": "Capital of France?"}])

        assert result == "Paris"
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-5.4"

    @patch("locust_async_chat.llm.client.OpenAI")
    def test_gpt_client_cached(self, mock_openai_cls):
        config = LLMConfig(resources=[_gpt_resource()], deployment="gpt-5.4")
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "answer"
        mock_openai_cls.return_value.chat.completions.create.return_value = (
            mock_response
        )

        client.chat([{"role": "user", "content": "q1"}])
        client.chat([{"role": "user", "content": "q2"}])

        assert mock_openai_cls.call_count == 1

    @patch("locust_async_chat.llm.client.OpenAI")
    def test_gpt_passes_temperature_and_max_tokens(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "answer"
        mock_client.chat.completions.create.return_value = mock_response

        config = LLMConfig(
            resources=[_gpt_resource()],
            deployment="gpt-5.4",
            temperature=0.5,
            max_tokens=512,
        )
        client = LLMClient(config)
        client.chat(
            [{"role": "user", "content": "hi"}],
            temperature=0.9,
            max_tokens=100,
        )

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["max_completion_tokens"] == 100


class TestLLMClientClaude:
    @patch("locust_async_chat.llm.client.AnthropicFoundry")
    def test_chat_routes_to_claude(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock()]
        mock_message.content[0].text = "Paris"
        mock_client.messages.create.return_value = mock_message

        config = LLMConfig(
            resources=[_claude_resource()],
            deployment="claude-sonnet-4-6",
        )
        client = LLMClient(config)
        result = client.chat([{"role": "user", "content": "Capital of France?"}])

        assert result == "Paris"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    @patch("locust_async_chat.llm.client.AnthropicFoundry")
    def test_claude_strips_system_message(self, mock_anthropic_cls):
        """Claude API doesn't accept system role in messages list; it uses a separate param."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock()]
        mock_message.content[0].text = "answer"
        mock_client.messages.create.return_value = mock_message

        config = LLMConfig(
            resources=[_claude_resource()],
            deployment="claude-sonnet-4-6",
        )
        client = LLMClient(config)
        client.chat(
            [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "hi"},
            ]
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are helpful."
        assert all(m["role"] != "system" for m in call_kwargs["messages"])


class TestLLMClientDeploymentSwitch:
    @patch("locust_async_chat.llm.client.AnthropicFoundry")
    @patch("locust_async_chat.llm.client.OpenAI")
    def test_switch_deployment_changes_provider(
        self, mock_openai_cls, mock_anthropic_cls
    ):
        mock_gpt_client = MagicMock()
        mock_openai_cls.return_value = mock_gpt_client
        mock_gpt_response = MagicMock()
        mock_gpt_response.choices = [MagicMock()]
        mock_gpt_response.choices[0].message.content = "gpt answer"
        mock_gpt_client.chat.completions.create.return_value = mock_gpt_response

        mock_claude_client = MagicMock()
        mock_anthropic_cls.return_value = mock_claude_client
        mock_claude_message = MagicMock()
        mock_claude_message.content = [MagicMock()]
        mock_claude_message.content[0].text = "claude answer"
        mock_claude_client.messages.create.return_value = mock_claude_message

        config = LLMConfig(
            resources=[_gpt_resource(), _claude_resource()],
            deployment="gpt-5.4",
        )
        client = LLMClient(config)

        result1 = client.chat([{"role": "user", "content": "q"}])
        assert result1 == "gpt answer"

        config.deployment = "claude-sonnet-4-6"
        result2 = client.chat([{"role": "user", "content": "q"}])
        assert result2 == "claude answer"
