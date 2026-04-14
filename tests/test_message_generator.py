from unittest.mock import MagicMock

from locust_async_chat.providers.ai.message_generator import MessageGenerator


class TestMessageGeneratorWithLLMClient:
    def _make_mock_client(self, response_text="Generated message"):
        client = MagicMock()
        client.chat.return_value = response_text
        return client

    def test_generate_initial_message(self):
        mock_client = self._make_mock_client("I'd like to book an appointment.")
        gen = MessageGenerator(client=mock_client)

        result = gen.generate_initial_message("booking", "Booking appointments")

        assert result == "I'd like to book an appointment."
        mock_client.chat.assert_called_once()
        call_args = mock_client.chat.call_args
        messages = call_args[0][0]
        assert any(
            "booking" in m["content"].lower() for m in messages if m["role"] == "user"
        )

    def test_generate_follow_up_message(self):
        mock_client = self._make_mock_client("Thank you for the info.")
        gen = MessageGenerator(client=mock_client)

        result = gen.generate_follow_up_message(
            topic_description="Booking appointments",
            conversation_history=[],
            assistant_response="We have slots available.",
        )

        assert result == "Thank you for the info."
        mock_client.chat.assert_called_once()

    def test_fallback_on_initial_message_error(self):
        mock_client = MagicMock()
        mock_client.chat.side_effect = RuntimeError("API error")
        gen = MessageGenerator(client=mock_client)

        result = gen.generate_initial_message("pricing", "Questions about pricing")

        assert "pricing" in result.lower()

    def test_fallback_on_follow_up_error(self):
        mock_client = MagicMock()
        mock_client.chat.side_effect = RuntimeError("API error")
        gen = MessageGenerator(client=mock_client)

        result = gen.generate_follow_up_message(
            topic_description="Pricing",
            conversation_history=[],
            assistant_response="Our prices start at $50.",
        )

        assert isinstance(result, str)
        assert len(result) > 0
