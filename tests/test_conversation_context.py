from locust_async_chat.providers.ai.conversation_context import (
    ConversationContext,
    ConversationContextManager,
)


class TestConversationContext:
    def test_is_first_message_initially_true(self):
        ctx = ConversationContext(conversation_id="c1")
        assert ctx.is_first_message() is True

    def test_add_user_message_increments_turn(self):
        ctx = ConversationContext(conversation_id="c1")
        ctx.add_user_message("hello")
        assert ctx.turn_count == 1
        assert ctx.is_first_message() is False
        assert len(ctx.messages) == 1
        assert ctx.messages[0].role == "user"
        assert ctx.messages[0].content == "hello"

    def test_add_assistant_message_does_not_increment_turn(self):
        ctx = ConversationContext(conversation_id="c1")
        ctx.add_assistant_message("hi back")
        assert ctx.turn_count == 0
        assert len(ctx.messages) == 1
        assert ctx.messages[0].role == "assistant"

    def test_set_topic(self):
        ctx = ConversationContext(conversation_id="c1")
        ctx.set_topic("booking", "Booking appointments")
        assert ctx.topic == "booking"
        assert ctx.topic_description == "Booking appointments"

    def test_get_conversation_history_all(self):
        ctx = ConversationContext(conversation_id="c1")
        ctx.add_user_message("q1")
        ctx.add_assistant_message("a1")
        ctx.add_user_message("q2")

        history = ctx.get_conversation_history()
        assert len(history) == 3
        # Returns a copy, not the original list
        assert history is not ctx.messages

    def test_get_conversation_history_limited(self):
        ctx = ConversationContext(conversation_id="c1")
        ctx.add_user_message("q1")
        ctx.add_assistant_message("a1")
        ctx.add_user_message("q2")
        ctx.add_assistant_message("a2")

        history = ctx.get_conversation_history(max_messages=2)
        assert len(history) == 2
        assert history[0].content == "q2"
        assert history[1].content == "a2"

    def test_get_conversation_history_zero_returns_empty(self):
        ctx = ConversationContext(conversation_id="c1")
        ctx.add_user_message("q1")
        assert ctx.get_conversation_history(max_messages=0) == []


class TestConversationContextManager:
    def test_get_or_create_creates_new(self):
        mgr = ConversationContextManager()
        ctx = mgr.get_or_create_context("c1")
        assert ctx.conversation_id == "c1"

    def test_get_or_create_returns_existing(self):
        mgr = ConversationContextManager()
        ctx1 = mgr.get_or_create_context("c1")
        ctx1.add_user_message("hello")
        ctx2 = mgr.get_or_create_context("c1")
        assert ctx2 is ctx1
        assert len(ctx2.messages) == 1

    def test_get_context_returns_none_if_missing(self):
        mgr = ConversationContextManager()
        assert mgr.get_context("unknown") is None

    def test_remove_context(self):
        mgr = ConversationContextManager()
        mgr.get_or_create_context("c1")
        mgr.remove_context("c1")
        assert mgr.get_context("c1") is None

    def test_remove_nonexistent_does_not_raise(self):
        mgr = ConversationContextManager()
        mgr.remove_context("nope")  # should not raise

    def test_clear(self):
        mgr = ConversationContextManager()
        mgr.get_or_create_context("c1")
        mgr.get_or_create_context("c2")
        mgr.clear()
        assert mgr.get_context("c1") is None
        assert mgr.get_context("c2") is None
