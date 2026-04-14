"""
Tests that verify UI parameter changes propagate correctly through
the config → user pool → user generation pipeline.

These simulate what happens when on_test_start re-applies config
from the Locust web UI.
"""

import os
from unittest.mock import patch

from locust_async_chat.config.config import LoadTestConfig
from locust_async_chat.users.user_pool import UserPool


class TestConfigReapplyFlow:
    """Simulate the on_test_start flow: rebuild config, reset pool, acquire users."""

    def test_user_pool_reset_still_uses_original_config(self):
        """Demonstrates the current behavior: pool.reset() does NOT pick up new config values."""
        config1 = LoadTestConfig(
            sut_login_url="https://example.com/login",
            sut_submit_url="https://example.com/messages",
            user_given_name="John",
            user_surname_prefix="Doe",
        )
        pool = UserPool(config1)
        u1 = pool.acquire()
        assert u1.given_name == "John"
        assert u1.surname == "Doe1"

        # Simulate UI change: new config with different user name
        _config2 = LoadTestConfig(  # noqa: F841
            sut_login_url="https://example.com/login",
            sut_submit_url="https://example.com/messages",
            user_given_name="Alice",
            user_surname_prefix="Test",
        )

        # Current on_test_start only calls pool.reset(), not pool = UserPool(_config2)
        pool.reset()
        u2 = pool.acquire()

        # BUG: pool still uses config1, so user has old name
        assert u2.given_name == "John"  # This SHOULD be "Alice" after UI change
        assert u2.surname == "Doe1"  # This SHOULD be "Test1"

    def test_new_pool_with_new_config_picks_up_changes(self):
        """Shows the fix: creating a new UserPool with updated config works correctly."""
        config1 = LoadTestConfig(
            sut_login_url="https://example.com/login",
            sut_submit_url="https://example.com/messages",
            user_given_name="John",
            user_surname_prefix="Doe",
        )
        pool = UserPool(config1)
        pool.acquire()

        config2 = LoadTestConfig(
            sut_login_url="https://example.com/login",
            sut_submit_url="https://example.com/messages",
            user_given_name="Alice",
            user_surname_prefix="Test",
        )

        # Fix: create new pool with new config
        pool = UserPool(config2)
        u = pool.acquire()
        assert u.given_name == "Alice"
        assert u.surname == "Test1"
        assert u.email == "alice.test1@locust.com"

    def test_wait_time_updates_from_options(self):
        """Verify wait_time config values change when options override them."""
        env = {
            "LOADTEST_SUT_LOGIN_URL": "https://example.com/login",
            "LOADTEST_SUT_SUBMIT_URL": "https://example.com/messages",
            "LOADTEST_WAIT_TIME_MIN_S": "10",
            "LOADTEST_WAIT_TIME_MAX_S": "15",
        }

        class UIOptions:
            host = None
            callback_timeout = None
            langsmith_dataset = None
            message_provider = None
            topic_selection_strategy = None
            ai_sync_to_langsmith = False
            ai_langsmith_dataset = None
            wait_time_min = 5
            wait_time_max = 8
            user_given_name = None
            user_surname_prefix = None
            user_email_domain = None

        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env_and_options(UIOptions())

        assert config.wait_time_min_s == 5
        assert config.wait_time_max_s == 8

    def test_user_name_updates_from_options(self):
        """Verify user name config values change when options override them."""
        env = {
            "LOADTEST_SUT_LOGIN_URL": "https://example.com/login",
            "LOADTEST_SUT_SUBMIT_URL": "https://example.com/messages",
        }

        class UIOptions:
            host = None
            callback_timeout = None
            langsmith_dataset = None
            message_provider = None
            topic_selection_strategy = None
            ai_sync_to_langsmith = False
            ai_langsmith_dataset = None
            wait_time_min = None
            wait_time_max = None
            user_given_name = "Bob"
            user_surname_prefix = "Smith"
            user_email_domain = "test.io"

        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env_and_options(UIOptions())

        assert config.user_given_name == "Bob"
        assert config.user_surname_prefix == "Smith"
        assert config.user_email_domain == "test.io"

        # And verify the pool uses these values
        pool = UserPool(config)
        user = pool.acquire()
        assert user.given_name == "Bob"
        assert user.surname == "Smith1"
        assert user.email == "bob.smith1@test.io"
