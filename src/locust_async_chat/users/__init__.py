"""
User management for load testing.

Provides utilities for generating and managing test users, and Locust user classes.
SutAsyncUser is imported lazily so tests that only need UserPool don't trigger
gevent/Locust (avoids RecursionError with pytest + ssl monkey-patching).
"""

from locust_async_chat.users.user_pool import (
    UserPool,
    TestUser,
    get_user_pool,
    set_user_pool,
)


def __getattr__(name: str):
    if name == "SutAsyncUser":
        from locust_async_chat.users.user import SutAsyncUser

        return SutAsyncUser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# SutAsyncUser is available via lazy import: from locust_async_chat.users import SutAsyncUser
__all__ = [
    "UserPool",
    "TestUser",
    "get_user_pool",
    "set_user_pool",
]
