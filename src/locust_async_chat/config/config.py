"""
Configuration management for Locust load testing.

Loads configuration from environment variables with support for
Locust CLI argument overrides.
"""

import argparse
import os
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv(override=True)

DEFAULT_DATASET_NAME = "Benchmark"
DEFAULT_CALLBACK_BIND_PORT = 44379
DEFAULT_CALLBACK_TIMEOUT_S = 90
DEFAULT_LOGIN_TIMEOUT_S = 10
DEFAULT_LOGIN_RETRY_MAX = 5
DEFAULT_LOGIN_RETRY_BACKOFF_BASE_S = 2

DEFAULT_LOGIN_ENABLED = True
DEFAULT_WAIT_TIME_MIN_S = 5
DEFAULT_WAIT_TIME_MAX_S = 10
DEFAULT_USER_GIVEN_NAME = "John"
DEFAULT_USER_SURNAME_PREFIX = "Doe"
DEFAULT_USER_EMAIL_DOMAIN = "locust.com"
DEFAULT_USER_LOCALE = "en-US"

# AI Provider defaults
DEFAULT_MESSAGE_PROVIDER = "langsmith"  # "langsmith" or "ai"
DEFAULT_TOPIC_SELECTION_STRATEGY = "random"  # "random" or "round_robin"
DEFAULT_LANGSMITH_QUESTION_MODE = "first"  # "first" or "all"


def _derive_host_from_submit_url(sut_submit_url: str) -> str:
    if not sut_submit_url:
        return ""

    parsed = urlsplit(sut_submit_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    return ""


@dataclass
class LoadTestConfig:
    sut_login_url: str
    sut_submit_url: str
    sut_auth_header: str = ""
    sut_login_timeout_s: int = DEFAULT_LOGIN_TIMEOUT_S
    login_retry_max: int = DEFAULT_LOGIN_RETRY_MAX
    login_retry_backoff_base_s: float = DEFAULT_LOGIN_RETRY_BACKOFF_BASE_S
    login_enabled: bool = DEFAULT_LOGIN_ENABLED
    wait_time_min_s: int = DEFAULT_WAIT_TIME_MIN_S
    wait_time_max_s: int = DEFAULT_WAIT_TIME_MAX_S
    user_given_name: str = DEFAULT_USER_GIVEN_NAME
    user_surname_prefix: str = DEFAULT_USER_SURNAME_PREFIX
    user_email_domain: str = DEFAULT_USER_EMAIL_DOMAIN
    user_locale: str = DEFAULT_USER_LOCALE
    callback_bind_port: int = DEFAULT_CALLBACK_BIND_PORT
    callback_timeout_s: int = DEFAULT_CALLBACK_TIMEOUT_S
    langsmith_dataset_name: str = DEFAULT_DATASET_NAME
    langsmith_question_mode: str = DEFAULT_LANGSMITH_QUESTION_MODE  # "first" or "all"
    # AI Provider settings
    message_provider: str = DEFAULT_MESSAGE_PROVIDER  # "langsmith" or "ai"
    topic_selection_strategy: str = DEFAULT_TOPIC_SELECTION_STRATEGY
    # AI → LangSmith sync: when True, ensure dataset exists and save each generated question
    ai_sync_to_langsmith: bool = False
    ai_langsmith_dataset_name: str = "AI Loadtest"
    sut_switchboard_name: str = (
        ""  # Filter callbacks by switchboard name (empty = no filter)
    )
    _parsed_options: Optional[object] = field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> "LoadTestConfig":
        login_enabled_str = os.getenv("LOADTEST_LOGIN_ENABLED", "true")
        login_enabled = login_enabled_str.lower() in ("true", "1", "yes")

        return cls(
            sut_login_url=os.getenv("LOADTEST_SUT_LOGIN_URL", ""),
            sut_submit_url=os.getenv("LOADTEST_SUT_SUBMIT_URL", ""),
            sut_auth_header=os.getenv("LOADTEST_SUT_AUTH_HEADER", ""),
            sut_login_timeout_s=int(
                os.getenv("LOADTEST_SUT_LOGIN_TIMEOUT_S", str(DEFAULT_LOGIN_TIMEOUT_S))
            ),
            login_retry_max=int(
                os.getenv("LOADTEST_LOGIN_RETRY_MAX", str(DEFAULT_LOGIN_RETRY_MAX))
            ),
            login_retry_backoff_base_s=float(
                os.getenv(
                    "LOADTEST_LOGIN_RETRY_BACKOFF_BASE_S",
                    str(DEFAULT_LOGIN_RETRY_BACKOFF_BASE_S),
                )
            ),
            login_enabled=login_enabled,
            wait_time_min_s=int(
                os.getenv("LOADTEST_WAIT_TIME_MIN_S", str(DEFAULT_WAIT_TIME_MIN_S))
            ),
            wait_time_max_s=int(
                os.getenv("LOADTEST_WAIT_TIME_MAX_S", str(DEFAULT_WAIT_TIME_MAX_S))
            ),
            user_given_name=os.getenv(
                "LOADTEST_USER_GIVEN_NAME", DEFAULT_USER_GIVEN_NAME
            ),
            user_surname_prefix=os.getenv(
                "LOADTEST_USER_SURNAME_PREFIX", DEFAULT_USER_SURNAME_PREFIX
            ),
            user_email_domain=os.getenv(
                "LOADTEST_USER_EMAIL_DOMAIN", DEFAULT_USER_EMAIL_DOMAIN
            ),
            user_locale=os.getenv("LOADTEST_USER_LOCALE", DEFAULT_USER_LOCALE),
            callback_bind_port=int(
                os.getenv(
                    "LOADTEST_CALLBACK_BIND_PORT", str(DEFAULT_CALLBACK_BIND_PORT)
                )
            ),
            callback_timeout_s=int(
                os.getenv(
                    "LOADTEST_CALLBACK_TIMEOUT_S", str(DEFAULT_CALLBACK_TIMEOUT_S)
                )
            ),
            langsmith_dataset_name=os.getenv(
                "LOADTEST_LANGSMITH_DATASET", DEFAULT_DATASET_NAME
            ),
            langsmith_question_mode=os.getenv(
                "LOADTEST_LANGSMITH_QUESTION_MODE", DEFAULT_LANGSMITH_QUESTION_MODE
            ).lower(),
            message_provider=os.getenv(
                "LOADTEST_MESSAGE_PROVIDER", DEFAULT_MESSAGE_PROVIDER
            ).lower(),
            topic_selection_strategy=os.getenv(
                "LOADTEST_TOPIC_SELECTION_STRATEGY", DEFAULT_TOPIC_SELECTION_STRATEGY
            ),
            ai_sync_to_langsmith=os.getenv(
                "LOADTEST_AI_SYNC_TO_LANGSMITH", "false"
            ).lower()
            in ("true", "1", "yes"),
            ai_langsmith_dataset_name=os.getenv(
                "LOADTEST_AI_LANGSMITH_DATASET", "AI Loadtest"
            ),
            sut_switchboard_name=os.getenv("LOADTEST_SUT_SWITCHBOARD_NAME", ""),
        )

    @classmethod
    def from_env_and_options(
        cls, parsed_options: Optional[object] = None
    ) -> "LoadTestConfig":
        config = cls.from_env()
        config._parsed_options = parsed_options

        if parsed_options is not None:
            if hasattr(parsed_options, "host") and parsed_options.host:
                config.sut_submit_url = parsed_options.host
            if (
                hasattr(parsed_options, "callback_timeout")
                and parsed_options.callback_timeout
            ):
                config.callback_timeout_s = parsed_options.callback_timeout
            if (
                hasattr(parsed_options, "langsmith_dataset")
                and parsed_options.langsmith_dataset
            ):
                config.langsmith_dataset_name = parsed_options.langsmith_dataset
            if (
                hasattr(parsed_options, "langsmith_question_mode")
                and parsed_options.langsmith_question_mode
            ):
                config.langsmith_question_mode = parsed_options.langsmith_question_mode
            if (
                hasattr(parsed_options, "message_provider")
                and parsed_options.message_provider
            ):
                config.message_provider = parsed_options.message_provider.lower()
            if (
                hasattr(parsed_options, "topic_selection_strategy")
                and parsed_options.topic_selection_strategy
            ):
                config.topic_selection_strategy = (
                    parsed_options.topic_selection_strategy
                )
            if hasattr(parsed_options, "ai_sync_to_langsmith"):
                config.ai_sync_to_langsmith = bool(
                    getattr(parsed_options, "ai_sync_to_langsmith", False)
                )
            _ai_ds = getattr(parsed_options, "ai_langsmith_dataset", None)
            if _ai_ds is not None and str(_ai_ds).strip():
                config.ai_langsmith_dataset_name = (
                    str(_ai_ds).strip() or config.ai_langsmith_dataset_name
                )
            if (
                hasattr(parsed_options, "wait_time_min")
                and parsed_options.wait_time_min is not None
            ):
                config.wait_time_min_s = parsed_options.wait_time_min
            if (
                hasattr(parsed_options, "wait_time_max")
                and parsed_options.wait_time_max is not None
            ):
                config.wait_time_max_s = parsed_options.wait_time_max
            if (
                hasattr(parsed_options, "user_given_name")
                and parsed_options.user_given_name
            ):
                config.user_given_name = parsed_options.user_given_name
            if (
                hasattr(parsed_options, "user_surname_prefix")
                and parsed_options.user_surname_prefix
            ):
                config.user_surname_prefix = parsed_options.user_surname_prefix
            if (
                hasattr(parsed_options, "user_email_domain")
                and parsed_options.user_email_domain
            ):
                config.user_email_domain = parsed_options.user_email_domain
            if (
                hasattr(parsed_options, "sut_switchboard_name")
                and parsed_options.sut_switchboard_name
            ):
                config.sut_switchboard_name = parsed_options.sut_switchboard_name

        return config

    def validate(self) -> list[str]:
        errors = []

        if self.login_enabled and not self.sut_login_url:
            errors.append("sut_login_url is required when login_enabled=True")

        if not self.sut_submit_url:
            errors.append("submit target is required (set Locust Host)")

        if self.login_enabled and self.sut_login_timeout_s <= 0:
            errors.append("sut_login_timeout_s must be positive")
        if self.login_enabled and self.login_retry_max < 0:
            errors.append("login_retry_max must be >= 0")
        if self.login_enabled and self.login_retry_backoff_base_s <= 0:
            errors.append("login_retry_backoff_base_s must be positive")

        if self.callback_timeout_s <= 0:
            errors.append("callback_timeout_s must be positive")

        return errors


def _fetch_langsmith_dataset_names() -> list[str]:
    """Fetch all dataset names from LangSmith for CLI choices."""
    try:
        from langsmith import Client

        client = Client()
        return sorted(ds.name for ds in client.list_datasets())
    except Exception:
        return []


def add_locust_cli_arguments(parser: argparse.ArgumentParser) -> None:
    default_submit_url = os.getenv("LOADTEST_SUT_SUBMIT_URL", "")
    default_host = _derive_host_from_submit_url(default_submit_url)
    if default_host:
        parser.set_defaults(host=default_host)

    # General
    parser.add_argument(
        "--callback-timeout",
        type=int,
        default=DEFAULT_CALLBACK_TIMEOUT_S,
        help="Timeout (s) to wait for webhook callback",
        env_var="LOADTEST_CALLBACK_TIMEOUT_S",
    )
    parser.add_argument(
        "--wait-time-min",
        type=int,
        default=DEFAULT_WAIT_TIME_MIN_S,
        help="Min seconds between tasks per user",
        env_var="LOADTEST_WAIT_TIME_MIN_S",
    )
    parser.add_argument(
        "--wait-time-max",
        type=int,
        default=DEFAULT_WAIT_TIME_MAX_S,
        help="Max seconds between tasks per user",
        env_var="LOADTEST_WAIT_TIME_MAX_S",
    )
    # User
    parser.add_argument(
        "--user-given-name",
        type=str,
        default=DEFAULT_USER_GIVEN_NAME,
        help="Given name for test users",
        env_var="LOADTEST_USER_GIVEN_NAME",
    )
    parser.add_argument(
        "--user-surname-prefix",
        type=str,
        default=DEFAULT_USER_SURNAME_PREFIX,
        help="Surname prefix (suffixed with number)",
        env_var="LOADTEST_USER_SURNAME_PREFIX",
    )
    parser.add_argument(
        "--user-email-domain",
        type=str,
        default=DEFAULT_USER_EMAIL_DOMAIN,
        help="Email domain for test users",
        env_var="LOADTEST_USER_EMAIL_DOMAIN",
    )
    # SUT
    parser.add_argument(
        "--sut-switchboard-name",
        type=str,
        default=os.getenv("LOADTEST_SUT_SWITCHBOARD_NAME", ""),
        help="Filter webhook callbacks by switchboard name (empty = accept all)",
        env_var="LOADTEST_SUT_SWITCHBOARD_NAME",
    )
    # Message Provider
    parser.add_argument(
        "--message-provider",
        type=str,
        choices=["langsmith", "ai"],
        default=DEFAULT_MESSAGE_PROVIDER,
        help="Message source: 'langsmith' (dataset) or 'ai' (LLM)",
        env_var="LOADTEST_MESSAGE_PROVIDER",
    )
    # LangSmith provider
    langsmith_dataset_choices = _fetch_langsmith_dataset_names()
    parser.add_argument(
        "--langsmith-dataset",
        type=str,
        choices=langsmith_dataset_choices or None,
        default=DEFAULT_DATASET_NAME,
        help="[LangSmith] Dataset name for test data",
        env_var="LOADTEST_LANGSMITH_DATASET",
    )
    parser.add_argument(
        "--langsmith-question-mode",
        type=str,
        choices=["first", "all"],
        default=DEFAULT_LANGSMITH_QUESTION_MODE,
        help="[LangSmith] When input is a list: 'first' item only or 'all' items",
        env_var="LOADTEST_LANGSMITH_QUESTION_MODE",
    )
    # AI provider
    from locust_async_chat.llm.config import load_llm_config

    llm_config = load_llm_config()
    deployment_choices = llm_config.all_deployments() or None

    parser.add_argument(
        "--llm-deployment",
        type=str,
        choices=deployment_choices,
        default=os.getenv("LLM_DEPLOYMENT", ""),
        help="[AI] LLM deployment to use",
        env_var="LLM_DEPLOYMENT",
    )
    parser.add_argument(
        "--llm-temperature",
        type=float,
        default=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        help="[AI] Temperature for LLM calls (0.0-2.0)",
        env_var="LLM_TEMPERATURE",
    )
    parser.add_argument(
        "--topic-selection-strategy",
        type=str,
        choices=["random", "round_robin"],
        default=DEFAULT_TOPIC_SELECTION_STRATEGY,
        help="[AI] Topic selection strategy",
        env_var="LOADTEST_TOPIC_SELECTION_STRATEGY",
    )


_config: Optional[LoadTestConfig] = None


def get_config() -> LoadTestConfig:
    global _config
    if _config is None:
        _config = LoadTestConfig.from_env()
    return _config


def set_config(config: LoadTestConfig) -> None:
    global _config
    _config = config
