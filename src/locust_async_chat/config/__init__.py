"""
Configuration management for load testing.

Provides LoadTestConfig dataclass and configuration loading utilities.
"""

from locust_async_chat.config.config import (
    LoadTestConfig,
    get_config,
    set_config,
    add_locust_cli_arguments,
    DEFAULT_CALLBACK_BIND_PORT,
    DEFAULT_CALLBACK_TIMEOUT_S,
    DEFAULT_LOGIN_TIMEOUT_S,
    DEFAULT_LOGIN_ENABLED,
    DEFAULT_WAIT_TIME_MIN_S,
    DEFAULT_WAIT_TIME_MAX_S,
    DEFAULT_USER_GIVEN_NAME,
    DEFAULT_USER_SURNAME_PREFIX,
    DEFAULT_USER_EMAIL_DOMAIN,
    DEFAULT_USER_LOCALE,
    DEFAULT_DATASET_NAME,
    DEFAULT_MESSAGE_PROVIDER,
    DEFAULT_TOPIC_SELECTION_STRATEGY,
    DEFAULT_LANGSMITH_QUESTION_MODE,
    _derive_host_from_submit_url,
)

__all__ = [
    "LoadTestConfig",
    "get_config",
    "set_config",
    "add_locust_cli_arguments",
    "DEFAULT_CALLBACK_BIND_PORT",
    "DEFAULT_CALLBACK_TIMEOUT_S",
    "DEFAULT_LOGIN_TIMEOUT_S",
    "DEFAULT_LOGIN_ENABLED",
    "DEFAULT_WAIT_TIME_MIN_S",
    "DEFAULT_WAIT_TIME_MAX_S",
    "DEFAULT_USER_GIVEN_NAME",
    "DEFAULT_USER_SURNAME_PREFIX",
    "DEFAULT_USER_EMAIL_DOMAIN",
    "DEFAULT_USER_LOCALE",
    "DEFAULT_DATASET_NAME",
    "DEFAULT_MESSAGE_PROVIDER",
    "DEFAULT_TOPIC_SELECTION_STRATEGY",
    "DEFAULT_LANGSMITH_QUESTION_MODE",
    "_derive_host_from_submit_url",
]
