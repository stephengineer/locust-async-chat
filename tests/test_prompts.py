from locust_async_chat.providers.ai.conversation_context import Message
from locust_async_chat.providers.ai.prompts import format_conversation_history


class TestFormatConversationHistory:
    def test_formats_user_and_assistant(self):
        messages = [
            Message(role="user", content="What services do you offer?"),
            Message(role="assistant", content="We offer haircuts and coloring."),
        ]
        result = format_conversation_history(messages)
        assert result == (
            "Customer: What services do you offer?\n"
            "Chatbot: We offer haircuts and coloring."
        )

    def test_empty_list(self):
        assert format_conversation_history([]) == ""

    def test_single_message(self):
        messages = [Message(role="user", content="Hello")]
        assert format_conversation_history(messages) == "Customer: Hello"

    def test_unknown_role_uses_role_name(self):
        messages = [Message(role="system", content="System message")]
        # role != "user" so it falls into the else branch → "Chatbot"
        assert format_conversation_history(messages) == "Chatbot: System message"
