"""
Locust load test entry point for SUT testing.

This file is the main entry point for running Locust load tests.
It sets up the environment, configures CLI arguments, and starts
the webhook server alongside the load test.
"""

import argparse
import logging
import sys
import time

from locust import events, between

from locust_async_chat.config import (
    LoadTestConfig,
    add_locust_cli_arguments,
    set_config,
)
from locust_async_chat.infrastructure import (
    CallbackRegistry,
    set_registry,
    start_server,
    stop_server,
)
from locust_async_chat.providers.langsmith import (
    LangSmithExampleProvider,
    LangSmithExampleWriter,
    set_provider,
)
from locust_async_chat.providers.ai import (
    AIMessageProvider,
    TopicManager,
    MessageGenerator,
    set_ai_provider,
)
from locust_async_chat.users import UserPool, set_user_pool, SutAsyncUser
from locust_async_chat.llm import LLMClient, load_llm_config, set_llm_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("locust_async_chat")


# Global instances
_config: LoadTestConfig | None = None
_registry: CallbackRegistry | None = None
_provider: LangSmithExampleProvider | None = None
_ai_provider: AIMessageProvider | None = None
_user_pool: UserPool | None = None
_llm_client: LLMClient | None = None


def _init_llm_client(parsed_options: object) -> None:
    """Initialize or re-initialize the LLM client from env + CLI overrides."""
    global _llm_client
    llm_config = load_llm_config()
    llm_deployment = getattr(parsed_options, "llm_deployment", None)
    if llm_deployment:
        llm_config.deployment = llm_deployment
    llm_temp = getattr(parsed_options, "llm_temperature", None)
    if llm_temp is not None:
        llm_config.temperature = float(llm_temp)
    if llm_config.all_deployments():
        _llm_client = LLMClient(llm_config)
        set_llm_client(_llm_client)
        logger.info(
            "LLM client initialized (deployment=%s, provider=%s)",
            llm_config.deployment,
            (
                llm_config.resolve_resource(llm_config.deployment).provider
                if llm_config.deployment
                else "none"
            ),
        )


def _init_message_provider(config: LoadTestConfig) -> None:
    """Initialize or re-initialize the message provider from config (used at init and when test starts from UI)."""
    global _provider, _ai_provider
    if config.message_provider == "ai":
        on_message_generated = None
        if config.ai_sync_to_langsmith:
            try:
                _langsmith_writer = LangSmithExampleWriter(
                    dataset_name=config.ai_langsmith_dataset_name,
                )

                def on_message_generated(q: str, m: dict) -> None:
                    _langsmith_writer.add_example(q, metadata=m)

                logger.info(
                    "AI→LangSmith sync enabled: dataset per topic '%s_{topic}' (create if not exists)",
                    config.ai_langsmith_dataset_name,
                )
            except Exception as e:
                logger.warning(
                    "AI→LangSmith sync disabled (failed to init writer): %s", e
                )
        if _llm_client is None:
            raise RuntimeError("LLM client not initialized; cannot use AI provider")
        topic_manager = TopicManager(selection_strategy=config.topic_selection_strategy)
        message_generator = MessageGenerator(client=_llm_client)
        _ai_provider = AIMessageProvider(
            topic_manager=topic_manager,
            message_generator=message_generator,
            on_message_generated=on_message_generated,
        )
        _ai_provider.initialize()
        set_ai_provider(_ai_provider)
        _provider = None
        llm_cfg = _llm_client.config if _llm_client else None
        logger.info(
            "AI Message Provider initialized with %s topics (deployment: %s)",
            len(topic_manager.topics),
            llm_cfg.deployment if llm_cfg else "none",
        )
    else:
        try:
            _provider = LangSmithExampleProvider(
                config.langsmith_dataset_name,
                question_mode=config.langsmith_question_mode,
            )
            count = _provider.load()
            set_provider(_provider)
            _ai_provider = None
            logger.info(
                "Loaded %s examples from LangSmith dataset '%s'",
                count,
                config.langsmith_dataset_name,
            )
        except Exception as e:
            logger.error("Failed to load dataset: %s", e)
            raise


@events.init_command_line_parser.add_listener
def on_init_parser(parser: argparse.ArgumentParser) -> None:
    """Add custom CLI arguments for load testing."""
    add_locust_cli_arguments(parser)


@events.init.add_listener
def on_init(environment: object, **kwargs: object) -> None:
    global _config, _registry, _provider, _user_pool

    logger.info("Initializing load test environment...")

    parsed_options = getattr(environment, "parsed_options", None)

    _config = LoadTestConfig.from_env_and_options(parsed_options)

    errors = _config.validate()
    if errors:
        logger.error(f"Configuration errors: {errors}")
        logger.error("Please set required environment variables or CLI arguments:")
        if _config.login_enabled:
            logger.error("  LOADTEST_SUT_LOGIN_URL")
        logger.error("  Locust Host field (or LOADTEST_SUT_SUBMIT_URL)")
        sys.exit(1)

    set_config(_config)
    logger.info(f"Config: Login enabled = {_config.login_enabled}")
    if _config.login_enabled:
        logger.info(f"Config: Login URL = {_config.sut_login_url}")
    logger.info(f"Config: Submit URL = {_config.sut_submit_url}")
    logger.info(f"Config: Webhook port = {_config.callback_bind_port}")
    logger.info(f"Config: Dataset = {_config.langsmith_dataset_name}")

    SutAsyncUser.wait_time = between(_config.wait_time_min_s, _config.wait_time_max_s)

    _user_pool = UserPool(_config)
    set_user_pool(_user_pool)
    logger.info("User pool initialized")

    # Initialize registry
    _registry = CallbackRegistry(timeout_s=_config.callback_timeout_s)
    _registry.start_cleanup()
    set_registry(_registry)
    logger.info("Callback registry initialized")

    # Initialize LLM client
    _init_llm_client(parsed_options)

    # Initialize message provider based on config
    try:
        _init_message_provider(_config)
    except Exception:
        logger.error(
            "Make sure LANGSMITH_API_KEY is set and dataset exists when using LangSmith"
        )
        sys.exit(1)

    # Start webhook server
    try:
        start_server(
            host="0.0.0.0",
            port=_config.callback_bind_port,
            registry=_registry,
            switchboard_name=_config.sut_switchboard_name,
        )
        logger.info(f"Webhook server started on 0.0.0.0:{_config.callback_bind_port}")
    except Exception as e:
        logger.error(f"Failed to start webhook server: {e}")
        sys.exit(1)


@events.test_start.add_listener
def on_test_start(environment: object, **kwargs: object) -> None:
    """Re-apply config from UI/parsed_options and re-init provider, then reset user pool."""
    global _config, _user_pool

    parsed = getattr(environment, "parsed_options", None)
    if parsed is not None:
        _config = LoadTestConfig.from_env_and_options(parsed)
        set_config(_config)

        # Re-init LLM client if deployment changed from UI
        _init_llm_client(parsed)

        # Update SutAsyncUser.wait_time with new config values
        SutAsyncUser.wait_time = between(
            _config.wait_time_min_s, _config.wait_time_max_s
        )

        try:
            _init_message_provider(_config)
            logger.info(
                "Config and message provider updated from UI (provider=%s, wait_time=%s-%ss)",
                _config.message_provider,
                _config.wait_time_min_s,
                _config.wait_time_max_s,
            )
        except Exception as e:
            logger.warning("Could not re-init message provider from UI options: %s", e)

    # Recreate user pool with updated config so UI changes to
    # user_given_name, user_surname_prefix, etc. take effect.
    if _config is not None:
        _user_pool = UserPool(_config)
        set_user_pool(_user_pool)
        logger.info("User pool recreated for new test run")


@events.quitting.add_listener
def on_quitting(environment: object, **kwargs: object) -> None:
    global _registry, _config

    logger.info("Shutting down load test environment...")

    if _registry is not None:
        _registry.stop_cleanup()

        timeout = _config.callback_timeout_s if _config else 30
        deadline = time.time() + timeout
        unresolved = _registry.unresolved_count()

        if unresolved > 0:
            logger.info(
                f"Waiting up to {timeout}s for {unresolved} pending callbacks..."
            )

        while _registry.unresolved_count() > 0 and time.time() < deadline:
            time.sleep(0.5)
            remaining = _registry.unresolved_count()
            if remaining != unresolved:
                logger.info(f"  {remaining} callbacks still pending...")
                unresolved = remaining

        still_unresolved = _registry.unresolved_count()
        if still_unresolved > 0:
            logger.warning(f"Timed out waiting for {still_unresolved} callbacks")

        _registry.clear()

    stop_server()
    logger.info("Webhook server stopped")

    logger.info("Load test environment shut down")


@events.request.add_listener
def on_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    exception: Exception | None,
    context: dict | None,
    **kwargs: object,
) -> None:
    """
    Custom request event listener for logging and debugging.
    """
    if request_type == "ASYNC":
        status = "FAIL" if exception else "OK"
        request_id = context.get("request_id", "unknown") if context else "unknown"
        conversation_id = (
            context.get("conversation_id", "unknown") if context else "unknown"
        )
        email = context.get("email", "unknown") if context else "unknown"
        user_id = context.get("user_id", "unknown") if context else "unknown"
        logger.debug(
            f"[{status}] {request_type}/{name} - {response_time:.0f}ms - "
            f"request_id: {request_id}, conversation_id: {conversation_id}, "
            f"email: {email}, user_id: {user_id}"
        )


# Export user classes for Locust
# Locust will discover these and show them in the UI
__all__ = [
    "SutAsyncUser",
]
