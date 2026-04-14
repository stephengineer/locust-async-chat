"""
Callback registry for request/response correlation.

Provides thread-safe storage for pending requests and their
corresponding webhook callbacks using gevent AsyncResult.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Any

import gevent
from gevent.event import AsyncResult


@dataclass
class PendingRequest:
    """
    Represents a pending request waiting for a webhook callback.

    Attributes:
        request_id: Unique identifier for the request
        start_perf: Performance counter at request start (for latency calculation)
        start_time: Wall clock time at request start
        async_result: Gevent AsyncResult for synchronization
        conversation_id: Conversation identifier
        turn_id: Turn number in conversation
        question: Original question from dataset
        expected_agent: Expected agent name (if known)
        metadata: Additional metadata from dataset
    """

    request_id: str
    start_perf: float
    start_time: float
    async_result: AsyncResult = field(default_factory=AsyncResult)
    conversation_id: str = ""
    turn_id: int = 1
    question: str = ""
    expected_agent: str = ""
    metadata: dict = field(default_factory=dict)


class CallbackRegistry:
    """
    Thread-safe registry for correlating requests with webhook callbacks.

    Uses gevent AsyncResult for efficient waiting and signaling between
    the Locust task thread and the webhook receiver thread.

    Example usage:
        registry = CallbackRegistry(timeout_s=30)

        # In Locust task:
        pending = registry.register(request_id="req-123", question="What is X?")
        # ... send HTTP request to SUT ...
        callback_data = pending.async_result.get(timeout=30)

        # In webhook handler:
        registry.resolve(request_id="req-123", payload={...})
    """

    def __init__(self, timeout_s: int = 30, cleanup_interval_s: int = 60):
        """
        Initialize the callback registry.

        Args:
            timeout_s: Default timeout for waiting on callbacks
            cleanup_interval_s: Interval for TTL cleanup of expired entries
        """
        self.timeout_s = timeout_s
        self.cleanup_interval_s = cleanup_interval_s
        self._store: dict[str, PendingRequest] = {}
        self._lock = threading.Lock()
        self._cleanup_greenlet: Optional[gevent.Greenlet] = None

    def start_cleanup(self) -> None:
        """Start the background cleanup greenlet for expired entries."""
        if self._cleanup_greenlet is None or self._cleanup_greenlet.dead:
            self._cleanup_greenlet = gevent.spawn(self._cleanup_loop)

    def stop_cleanup(self) -> None:
        """Stop the background cleanup greenlet."""
        if self._cleanup_greenlet is not None:
            self._cleanup_greenlet.kill()
            self._cleanup_greenlet = None

    def _cleanup_loop(self) -> None:
        """Background loop that periodically cleans up expired entries."""
        while True:
            try:
                gevent.sleep(self.cleanup_interval_s)
                self.expire_old_entries()
            except gevent.GreenletExit:
                break

    def register(
        self,
        request_id: str,
        conversation_id: str = "",
        turn_id: int = 1,
        question: str = "",
        expected_agent: str = "",
        metadata: Optional[dict] = None,
    ) -> PendingRequest:
        """
        Register a new pending request.

        Args:
            request_id: Unique identifier for the request
            conversation_id: Conversation identifier
            turn_id: Turn number in conversation
            question: Original question from dataset
            expected_agent: Expected agent name (if known)
            metadata: Additional metadata

        Returns:
            PendingRequest object with AsyncResult for waiting
        """
        pending = PendingRequest(
            request_id=request_id,
            start_perf=time.perf_counter(),
            start_time=time.time(),
            conversation_id=conversation_id,
            turn_id=turn_id,
            question=question,
            expected_agent=expected_agent,
            metadata=metadata or {},
        )

        with self._lock:
            self._store[request_id] = pending

        return pending

    def resolve(self, request_id: str, payload: dict) -> bool:
        """
        Resolve a pending request with the callback payload.

        Args:
            request_id: The request ID to resolve
            payload: The callback payload from SUT

        Returns:
            True if request was found and resolved, False otherwise
        """
        with self._lock:
            pending = self._store.get(request_id)
            if pending is None:
                return False

        # Signal the AsyncResult with the payload
        # This wakes up the waiting task
        pending.async_result.set(payload)
        return True

    def get(self, request_id: str) -> Optional[PendingRequest]:
        """
        Get a pending request by ID.

        Args:
            request_id: The request ID to look up

        Returns:
            PendingRequest if found, None otherwise
        """
        with self._lock:
            return self._store.get(request_id)

    def remove(self, request_id: str) -> bool:
        """
        Remove a request from the registry.

        Args:
            request_id: The request ID to remove

        Returns:
            True if request was found and removed, False otherwise
        """
        with self._lock:
            if request_id in self._store:
                del self._store[request_id]
                return True
            return False

    def expire_old_entries(self, max_age_s: Optional[int] = None) -> int:
        """
        Remove entries older than max_age_s seconds.

        Args:
            max_age_s: Maximum age in seconds (defaults to 2x timeout)

        Returns:
            Number of entries removed
        """
        if max_age_s is None:
            max_age_s = self.timeout_s * 2

        cutoff_time = time.time() - max_age_s
        removed = 0

        with self._lock:
            expired_ids = [
                req_id
                for req_id, pending in self._store.items()
                if pending.start_time < cutoff_time
            ]

            for req_id in expired_ids:
                # Signal timeout to any waiting tasks
                pending = self._store[req_id]
                if not pending.async_result.ready():
                    pending.async_result.set_exception(
                        TimeoutError(f"Callback timeout for request {req_id}")
                    )
                del self._store[req_id]
                removed += 1

        return removed

    def pending_count(self) -> int:
        """
        Get the number of pending requests.

        Returns:
            Number of requests waiting for callbacks
        """
        with self._lock:
            return len(self._store)

    def unresolved_count(self) -> int:
        """
        Get the number of requests that have not yet received a callback.

        Unlike pending_count which tracks entries in the store (removed by
        user tasks), this checks which AsyncResults are still not ready.

        Returns:
            Number of requests still waiting for callbacks
        """
        with self._lock:
            return sum(1 for p in self._store.values() if not p.async_result.ready())

    def clear(self) -> int:
        """
        Clear all pending requests.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._store)
            # Signal all pending requests as cancelled
            for pending in self._store.values():
                if not pending.async_result.ready():
                    pending.async_result.set_exception(
                        Exception("Registry cleared - request cancelled")
                    )
            self._store.clear()
            return count

    def wait_for_callback(
        self, request_id: str, timeout: Optional[float] = None
    ) -> Optional[Any]:
        """
        Wait for a callback to arrive for the given request.

        Args:
            request_id: The request ID to wait for
            timeout: Timeout in seconds (defaults to registry timeout)

        Returns:
            The callback payload if received, None if timeout or not found
        """
        if timeout is None:
            timeout = float(self.timeout_s)

        with self._lock:
            pending = self._store.get(request_id)

        if pending is None:
            return None

        try:
            result = pending.async_result.get(timeout=timeout)
            return result
        except gevent.Timeout:
            return None
        except Exception:
            return None

    def get_elapsed_time(self, request_id: str) -> Optional[float]:
        """
        Get elapsed time in milliseconds since request was registered.

        Args:
            request_id: The request ID

        Returns:
            Elapsed time in milliseconds, or None if not found
        """
        with self._lock:
            pending = self._store.get(request_id)

        if pending is None:
            return None

        return (time.perf_counter() - pending.start_perf) * 1000


# Global registry instance (lazy-loaded)
_registry: Optional[CallbackRegistry] = None


def get_registry() -> CallbackRegistry:
    """
    Get the global registry instance.

    Returns:
        CallbackRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = CallbackRegistry()
    return _registry


def set_registry(registry: CallbackRegistry) -> None:
    """
    Set the global registry instance.

    Args:
        registry: CallbackRegistry instance to use globally
    """
    global _registry
    _registry = registry
