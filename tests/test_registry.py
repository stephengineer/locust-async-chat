import time

import gevent
from gevent.event import AsyncResult

from locust_async_chat.infrastructure.registry import CallbackRegistry


class TestCallbackRegistryBasics:
    def test_register_creates_pending_request(self):
        reg = CallbackRegistry(timeout_s=10)
        pending = reg.register("req-1", conversation_id="conv-1", question="hi?")

        assert pending.request_id == "req-1"
        assert pending.conversation_id == "conv-1"
        assert pending.question == "hi?"
        assert isinstance(pending.async_result, AsyncResult)

    def test_get_returns_registered_request(self):
        reg = CallbackRegistry()
        reg.register("req-1")
        assert reg.get("req-1") is not None
        assert reg.get("req-1").request_id == "req-1"

    def test_get_returns_none_for_unknown(self):
        reg = CallbackRegistry()
        assert reg.get("unknown") is None

    def test_pending_count(self):
        reg = CallbackRegistry()
        assert reg.pending_count() == 0
        reg.register("req-1")
        reg.register("req-2")
        assert reg.pending_count() == 2


class TestCallbackRegistryResolve:
    def test_resolve_sets_async_result(self):
        reg = CallbackRegistry()
        pending = reg.register("req-1")
        payload = {"text": "response"}

        assert reg.resolve("req-1", payload) is True
        assert pending.async_result.ready()
        assert pending.async_result.get() == payload

    def test_resolve_unknown_returns_false(self):
        reg = CallbackRegistry()
        assert reg.resolve("unknown", {}) is False

    def test_unresolved_count(self):
        reg = CallbackRegistry()
        reg.register("req-1")
        reg.register("req-2")
        assert reg.unresolved_count() == 2

        reg.resolve("req-1", {"data": "ok"})
        assert reg.unresolved_count() == 1


class TestCallbackRegistryRemove:
    def test_remove_existing(self):
        reg = CallbackRegistry()
        reg.register("req-1")
        assert reg.remove("req-1") is True
        assert reg.get("req-1") is None
        assert reg.pending_count() == 0

    def test_remove_unknown(self):
        reg = CallbackRegistry()
        assert reg.remove("unknown") is False


class TestCallbackRegistryExpire:
    def test_expire_removes_old_entries(self):
        reg = CallbackRegistry(timeout_s=1)
        pending = reg.register("req-old")
        # Backdate the start_time so it's expired
        pending.start_time = time.time() - 100

        removed = reg.expire_old_entries(max_age_s=5)
        assert removed == 1
        assert reg.pending_count() == 0

    def test_expire_keeps_recent_entries(self):
        reg = CallbackRegistry(timeout_s=60)
        reg.register("req-new")

        removed = reg.expire_old_entries(max_age_s=60)
        assert removed == 0
        assert reg.pending_count() == 1

    def test_expire_signals_timeout_to_waiters(self):
        reg = CallbackRegistry(timeout_s=1)
        pending = reg.register("req-1")
        pending.start_time = time.time() - 100

        reg.expire_old_entries(max_age_s=5)
        assert pending.async_result.ready()


class TestCallbackRegistryClear:
    def test_clear_removes_all(self):
        reg = CallbackRegistry()
        reg.register("req-1")
        reg.register("req-2")

        count = reg.clear()
        assert count == 2
        assert reg.pending_count() == 0

    def test_clear_signals_exception_to_waiters(self):
        reg = CallbackRegistry()
        pending = reg.register("req-1")
        reg.clear()

        assert pending.async_result.ready()


class TestCallbackRegistryElapsedTime:
    def test_returns_elapsed_ms(self):
        reg = CallbackRegistry()
        reg.register("req-1")
        # Even immediately, elapsed should be a small positive number
        elapsed = reg.get_elapsed_time("req-1")
        assert elapsed is not None
        assert elapsed >= 0

    def test_returns_none_for_unknown(self):
        reg = CallbackRegistry()
        assert reg.get_elapsed_time("unknown") is None


class TestCallbackRegistryWaitForCallback:
    def test_wait_returns_payload_when_resolved(self):
        reg = CallbackRegistry(timeout_s=5)
        reg.register("req-1")

        def resolver():
            gevent.sleep(0.05)
            reg.resolve("req-1", {"text": "done"})

        gevent.spawn(resolver)
        result = reg.wait_for_callback("req-1", timeout=2.0)
        assert result == {"text": "done"}

    def test_wait_returns_none_for_unknown(self):
        reg = CallbackRegistry()
        assert reg.wait_for_callback("unknown", timeout=0.1) is None

    def test_wait_returns_none_on_timeout(self):
        reg = CallbackRegistry(timeout_s=1)
        reg.register("req-1")
        result = reg.wait_for_callback("req-1", timeout=0.1)
        assert result is None
