"""
Locust user classes for SUT load testing.

Defines HttpUser subclasses that implement the async webhook pattern
for testing the SUT with callback-based responses.
"""

import time
import logging
from typing import Optional, Any, Union

import gevent
from locust import HttpUser, task, between

from locust_async_chat.config import LoadTestConfig, get_config
from locust_async_chat.infrastructure import CallbackRegistry, get_registry
from locust_async_chat.providers.langsmith import (
    LangSmithExampleProvider,
    get_provider,
    TestExample,
)
from locust_async_chat.providers.ai import (
    AIMessage,
    AIMessageProvider,
    get_ai_provider,
)
from locust_async_chat.users import UserPool, TestUser, get_user_pool
from locust.exception import StopUser

from locust_async_chat.models import (
    CallbackPayload,
    LoginResponseDevice,
    LoginResponseUser,
    LoginResponseConversation,
    LoginResponseSource,
    MessagePayload,
    parse_conversation_id,
    parse_correlation_id,
)

logger = logging.getLogger(__name__)


class SutAsyncUser(HttpUser):
    """
    Locust user that sends requests to SUT and waits for webhook callbacks.

    This user class implements the async webhook pattern where:
    1. Send POST request to SUT with callback URL
    2. Wait for SUT to call our webhook with the response
    3. Measure end-to-end latency from request to callback

    Locust's built-in stats will show the submit latency (POST response time).
    Custom async stats (via events.request.fire) will show end-to-end latency.

    Example locustfile.py:
        from locust_async_chat.user import SutAsyncUser

        # SutAsyncUser is auto-configured via on_start
    """

    wait_time = between(1, 5)
    abstract = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.config: Optional[LoadTestConfig] = None
        self.registry: Optional[CallbackRegistry] = None
        self.provider: Optional[LangSmithExampleProvider] = None
        self.ai_provider: Optional[AIMessageProvider] = None
        self.user_pool: Optional[UserPool] = None
        self.test_user: Optional[TestUser] = None
        self.conversation_id: Optional[str] = None
        self.login_user: Optional[LoginResponseUser] = None
        self.login_conversation: Optional[LoginResponseConversation] = None
        self.login_source: Optional[LoginResponseSource] = None
        self.last_assistant_response: Optional[str] = None
        self.message_count: int = 0
        self.message_limit: int = 0

    def on_start(self) -> None:
        self.config = get_config()
        self.registry = get_registry()
        self.user_pool = get_user_pool()

        # Initialize provider based on config
        if self.config.message_provider == "ai":
            self.ai_provider = get_ai_provider()
            if self.ai_provider:
                self.ai_provider.initialize()
        else:
            self.provider = get_provider(self.config.langsmith_dataset_name)

        errors = self.config.validate()
        if errors:
            logger.error(f"Invalid configuration: {errors}")
            raise ValueError(f"Invalid configuration: {errors}")

        if self.user_pool is not None:
            self.test_user = self.user_pool.acquire()

        if self.config.login_enabled:
            self._login()
        else:
            import uuid

            self.conversation_id = str(uuid.uuid4())

        # For testing login only, set message limit to 0
        self.message_limit = 1000
        self.message_count = 0

        user_id_str = (
            self.login_user.user_id
            if self.login_user and self.login_user.user_id
            else (f"test_user_{self.test_user.index}" if self.test_user else "none")
        )
        provider_info = (
            f"AI Provider ({self.ai_provider.count if self.ai_provider else 0} topics)"
            if self.config.message_provider == "ai"
            else f"LangSmith ({self.provider.count if self.provider else 0} examples)"
        )
        logger.info(
            f"User started - SUT: {self.config.sut_submit_url}, "
            f"conversation_id: {self.conversation_id}, "
            f"test_user: {self.test_user.surname if self.test_user else 'none'}, "
            f"email: {self.test_user.email if self.test_user else 'none'}, "
            f"user_id: {user_id_str}, "
            f"Provider: {provider_info}, "
            f"message_limit: {self.message_limit}"
        )

    def _login(self) -> None:
        if self.config is None:
            raise StopUser("Config not initialized")

        if self.test_user is not None:
            login_payload = self.test_user.to_login_payload()
        else:
            from locust_async_chat.models.login import LoginRequestPayload

            login_payload = LoginRequestPayload()

        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.config.sut_auth_header:
            headers["Authorization"] = self.config.sut_auth_header

        retryable_statuses = (429, 503)
        max_attempts = self.config.login_retry_max + 1

        try:
            for attempt in range(max_attempts):
                with self.client.post(
                    self.config.sut_login_url,
                    json=login_payload.to_dict(),
                    headers=headers,
                    name="login",
                    timeout=self.config.sut_login_timeout_s,
                    catch_response=True,
                ) as response:
                    if response.status_code in (200, 201):
                        try:
                            login_data = response.json()
                        except Exception as e:
                            response.failure(f"Login response not JSON: {e}")
                            raise StopUser(f"Login response not JSON: {e}")

                        conversation_id = parse_conversation_id(login_data)
                        if not conversation_id:
                            logger.error(login_data)
                            response.failure("Login response missing conversation_id")
                            raise StopUser("Login response missing conversation_id")

                        self.conversation_id = conversation_id
                        self.login_user = LoginResponseUser.from_dict(login_data)
                        self.login_conversation = LoginResponseConversation.from_dict(
                            login_data.get("conversations", {})[0]
                        )
                        self.login_source = LoginResponseSource.from_dict(
                            login_data.get("source", {})
                        )
                        response.success()
                        return

                    if (
                        response.status_code in retryable_statuses
                        and attempt < max_attempts - 1
                    ):
                        backoff_s = self.config.login_retry_backoff_base_s**attempt
                        logger.warning(
                            "Login rate limited (%s), retry %s/%s in %.1fs",
                            response.status_code,
                            attempt + 1,
                            self.config.login_retry_max,
                            backoff_s,
                        )
                        time.sleep(backoff_s)
                        continue

                    response.failure(f"Login failed: {response.status_code}")
                    raise StopUser(f"Login failed: {response.status_code}")

        except StopUser:
            raise
        except Exception as e:
            logger.error(f"Login request failed: {e}")
            raise StopUser(f"Login request failed: {e}")

    def on_stop(self) -> None:
        """Called when a simulated user stops."""
        logger.debug("User stopped")

    @task
    def submit_and_wait(self) -> None:
        """
        Main task: submit a question to SUT and wait for webhook callback.

        Flow:
        1. Get next message (from LangSmith or AI provider)
        2. Build request payload with callback URL
        3. Register in callback registry
        4. POST to SUT (Locust records submit latency)
        5. Wait for callback via AsyncResult
        6. Store assistant response for next AI-generated message
        7. Fire custom e2e latency event
        """
        if self.message_count >= self.message_limit:
            if not getattr(self, "_limit_logged", False):
                logger.info(
                    "User reached message limit (%s/%s), idling",
                    self.message_count,
                    self.message_limit,
                )
                self._limit_logged = True
            return

        if self.config is None or self.registry is None:
            logger.error("User not properly initialized")
            return

        if self.conversation_id is None or self.login_user is None:
            logger.error("User not logged in")
            return

        # Get next message (same interface for both providers: .question, .expected_agent, .metadata)
        example: Union[AIMessage, TestExample]
        if self.config.message_provider == "ai":
            if self.ai_provider is None:
                logger.error("AI provider not initialized")
                return
            try:
                example = self.ai_provider.next_message(
                    conversation_id=self.conversation_id,
                    assistant_response=self.last_assistant_response,
                )
            except Exception as e:
                logger.error("AI message generation failed: %s", e, exc_info=True)
                return
            if not example.question or not example.question.strip():
                logger.error(
                    "AI provider returned empty message for conversation %s, skipping",
                    self.conversation_id,
                )
                return
            topic = getattr(example, "topic", None) or (example.metadata or {}).get(
                "topic", "?"
            )
            user_label = (
                self.login_user.email
                if self.login_user and self.login_user.email
                else ""
            ) or (
                f"user_{self.test_user.index}"
                if self.test_user
                else self.conversation_id or "?"
            )
            logger.info("Test user %s → topic: %s", user_label, topic)
            self.last_assistant_response = None
        else:
            if self.provider is None:
                logger.error("LangSmith provider not initialized")
                return
            example = self.provider.next()

        # Same payload as LangSmith: only the query text (example.question) changes
        if self.login_conversation is None or self.login_source is None:
            # In non-login mode, initialize minimal conversation/source so we can still submit messages
            if getattr(self.config, "login_enabled", True) is False:
                if self.login_user is None:
                    # Minimal fallback user for non-login mode
                    user_id = (
                        f"user-{self.test_user.index}"
                        if getattr(self, "test_user", None) is not None
                        else "anonymous"
                    )
                    self.login_user = LoginResponseUser(
                        user_id=user_id,
                        external_id="",
                        given_name="",
                        surname="",
                        email="",
                        avatar_url="",
                        locale="en-US",
                        locale_origin="apiRequest",
                        signed_up_at="",
                        metadata={},
                        authenticated=True,
                        to_be_retained=True,
                    )
                if self.login_conversation is None:
                    conv_id = self.conversation_id or ""
                    self.login_conversation = LoginResponseConversation(id=conv_id)
                if self.login_source is None:
                    self.login_source = LoginResponseSource(
                        source_type="api:conversations",
                        integration_id="loadtest",
                        device=LoginResponseDevice(
                            guid="",
                            integration_id="loadtest",
                            device_type="web",
                            info={},
                        ),
                    )
            else:
                logger.error("Login conversation or source not initialized")
                return
        payload = MessagePayload(
            conversation=self.login_conversation,
            user=self.login_user,
            source=self.login_source,
            text=example.question,
        )
        body = payload.to_dict()

        submit_url = self.config.sut_submit_url
        start_perf = time.perf_counter()
        correlation_id: Optional[str] = None

        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.config.sut_auth_header:
            headers["Authorization"] = self.config.sut_auth_header

        try:
            with self.client.post(
                submit_url,
                json=body,
                headers=headers,
                name="submit",
                catch_response=True,
            ) as response:
                if response.status_code not in (200, 201, 202):
                    resp_text = ""
                    try:
                        resp_text = response.text[:500] if response.text else ""
                    except Exception:
                        pass
                    fail_msg = f"Submit failed: {response.status_code}"
                    logger.error(
                        "%s | url=%s | response_body=%s | message_preview=%s",
                        fail_msg,
                        submit_url,
                        resp_text,
                        (example.question or "")[:100],
                    )
                    response.failure(fail_msg)
                    return

                try:
                    response_data = response.json()
                except Exception as e:
                    resp_text = ""
                    try:
                        resp_text = response.text[:500] if response.text else ""
                    except Exception:
                        pass
                    fail_msg = f"Submit response not JSON: {e}"
                    logger.error(
                        "%s | status=%s | response_body=%s",
                        fail_msg,
                        response.status_code,
                        resp_text,
                    )
                    response.failure(fail_msg)
                    return

                correlation_id = parse_correlation_id(response_data)
                if not correlation_id:
                    logger.error(
                        "Submit response missing correlationID | status=%s | response_keys=%s | message_preview=%s",
                        response.status_code,
                        (
                            list(response_data.keys())
                            if isinstance(response_data, dict)
                            else type(response_data).__name__
                        ),
                        (example.question or "")[:100],
                    )
                    response.failure("Submit response missing correlationID")
                    return

                response.success()

        except Exception as e:
            logger.error(
                "Submit request exception: %s | url=%s | message_preview=%s",
                e,
                submit_url,
                (example.question or "")[:100],
                exc_info=True,
            )
            self._fire_e2e_failure(
                request_id=correlation_id or "unknown",
                start_perf=start_perf,
                exception=e,
            )
            return

        pending = self.registry.register(
            request_id=correlation_id,
            conversation_id=self.conversation_id,
            turn_id=1,
            question=example.question,
            expected_agent=example.expected_agent,
            metadata=example.metadata,
        )
        pending.start_perf = start_perf

        try:
            callback_data = pending.async_result.get(
                timeout=self.config.callback_timeout_s
            )

            if not callback_data:
                raise ValueError("Empty callback data received")

            e2e_ms = (time.perf_counter() - start_perf) * 1000

            callback = CallbackPayload.from_dict(callback_data)

            # Store assistant response for AI provider to use in next message
            if self.config.message_provider == "ai" and callback.response_text:
                self.last_assistant_response = callback.response_text

            self._fire_e2e_success(
                request_id=correlation_id,
                e2e_ms=e2e_ms,
                callback=callback,
            )

        except gevent.Timeout:
            self._fire_e2e_failure(
                request_id=correlation_id,
                start_perf=start_perf,
                exception=TimeoutError(
                    f"Callback timeout after {self.config.callback_timeout_s}s"
                ),
            )

        except Exception as e:
            logger.error(f"Error waiting for callback: {e}")
            self._fire_e2e_failure(
                request_id=correlation_id,
                start_perf=start_perf,
                exception=e,
            )

        finally:
            self.registry.remove(correlation_id)
            self.message_count += 1

    def _fire_e2e_success(
        self,
        request_id: str,
        e2e_ms: float,
        callback: CallbackPayload,
    ) -> None:
        """Fire a successful end-to-end request event."""
        response_length = len(callback.response_text) if callback.response_text else 0

        context = {
            "request_id": request_id,
            "conversation_id": callback.conversation_id,
            "author_type": callback.author_type,
        }
        if self.test_user:
            context["email"] = self.test_user.email
        if self.login_user and self.login_user.user_id:
            context["user_id"] = self.login_user.user_id
        elif self.test_user:
            context["user_id"] = f"test_user_{self.test_user.index}"

        self.environment.events.request.fire(
            request_type="ASYNC",
            name="e2e",
            response_time=e2e_ms,
            response_length=response_length,
            exception=None,
            context=context,
        )

    def _fire_e2e_failure(
        self,
        request_id: str,
        start_perf: float,
        exception: Exception,
    ) -> None:
        """Fire a failed end-to-end request event."""
        e2e_ms = (time.perf_counter() - start_perf) * 1000

        context = {"request_id": request_id}
        if self.conversation_id:
            context["conversation_id"] = self.conversation_id
        if self.test_user:
            context["email"] = self.test_user.email
        if self.login_user and self.login_user.user_id:
            context["user_id"] = self.login_user.user_id
        elif self.test_user:
            context["user_id"] = f"test_user_{self.test_user.index}"

        self.environment.events.request.fire(
            request_type="ASYNC",
            name="e2e",
            response_time=e2e_ms,
            response_length=0,
            exception=exception,
            context=context,
        )
