import os
from unittest.mock import patch

from locust_async_chat.config.config import (
    LoadTestConfig,
    _derive_host_from_submit_url,
)


class TestDeriveHostFromSubmitUrl:
    def test_extracts_scheme_and_netloc_with_path(self):
        url = "https://api.example.com/api/v1/chat/messages"
        assert (
            _derive_host_from_submit_url(url)
            == "https://api.example.com/api/v1/chat/messages"
        )

    def test_simple_url(self):
        url = "https://api.example.com"
        assert _derive_host_from_submit_url(url) == "https://api.example.com"

    def test_returns_empty_for_empty_input(self):
        assert _derive_host_from_submit_url("") == ""

    def test_returns_empty_for_path_only(self):
        assert _derive_host_from_submit_url("/just/a/path") == ""


class TestLoadTestConfigValidate:
    def test_valid_config_returns_no_errors(self, default_config):
        assert default_config.validate() == []

    def test_missing_login_url_when_enabled(self):
        config = LoadTestConfig(
            sut_login_url="",
            sut_submit_url="https://example.com/messages",
            login_enabled=True,
        )
        errors = config.validate()
        assert any("sut_login_url" in e for e in errors)

    def test_missing_submit_url(self, default_config):
        default_config.sut_submit_url = ""
        errors = default_config.validate()
        assert any("submit target" in e for e in errors)

    def test_negative_login_timeout(self, default_config):
        default_config.sut_login_timeout_s = -1
        errors = default_config.validate()
        assert any("sut_login_timeout_s" in e for e in errors)

    def test_negative_retry_max(self, default_config):
        default_config.login_retry_max = -1
        errors = default_config.validate()
        assert any("login_retry_max" in e for e in errors)

    def test_negative_backoff(self, default_config):
        default_config.login_retry_backoff_base_s = 0
        errors = default_config.validate()
        assert any("login_retry_backoff_base_s" in e for e in errors)

    def test_negative_callback_timeout(self, default_config):
        default_config.callback_timeout_s = 0
        errors = default_config.validate()
        assert any("callback_timeout_s" in e for e in errors)

    def test_login_disabled_skips_login_checks(self):
        config = LoadTestConfig(
            sut_login_url="",
            sut_submit_url="https://example.com/messages",
            login_enabled=False,
        )
        errors = config.validate()
        assert not any("sut_login_url" in e for e in errors)
        assert not any("sut_login_timeout_s" in e for e in errors)


class TestLoadTestConfigFromEnv:
    def test_reads_env_vars(self):
        env = {
            "LOADTEST_SUT_LOGIN_URL": "https://login.test",
            "LOADTEST_SUT_SUBMIT_URL": "https://submit.test",
            "LOADTEST_SUT_AUTH_HEADER": "Bearer xyz",
            "LOADTEST_CALLBACK_TIMEOUT_S": "120",
            "LOADTEST_MESSAGE_PROVIDER": "AI",
            "LOADTEST_LOGIN_ENABLED": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()

        assert config.sut_login_url == "https://login.test"
        assert config.sut_submit_url == "https://submit.test"
        assert config.sut_auth_header == "Bearer xyz"
        assert config.callback_timeout_s == 120
        assert config.message_provider == "ai"
        assert config.login_enabled is False

    def test_defaults_when_env_empty(self):
        env = {
            "LOADTEST_SUT_LOGIN_URL": "",
            "LOADTEST_SUT_SUBMIT_URL": "",
            "LOADTEST_SUT_AUTH_HEADER": "",
        }
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env()
        assert config.sut_login_url == ""
        assert config.callback_timeout_s == 90


class TestLoadTestConfigFromEnvAndOptions:
    def test_cli_options_override_env(self):
        env = {
            "LOADTEST_SUT_LOGIN_URL": "https://login.test",
            "LOADTEST_SUT_SUBMIT_URL": "https://submit.test",
        }

        class Options:
            host = "https://override.test"
            callback_timeout = 200
            message_provider = "AI"
            langsmith_dataset = None
            topic_selection_strategy = None
            ai_sync_to_langsmith = False
            ai_langsmith_dataset = None
            wait_time_min = None
            wait_time_max = None
            user_given_name = None
            user_surname_prefix = None
            user_email_domain = None

        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env_and_options(Options())

        assert config.sut_submit_url == "https://override.test"
        assert config.callback_timeout_s == 200
        assert config.message_provider == "ai"

    def test_none_options_keep_env_values(self):
        env = {
            "LOADTEST_SUT_LOGIN_URL": "https://login.test",
            "LOADTEST_SUT_SUBMIT_URL": "https://submit.test",
            "LOADTEST_CALLBACK_TIMEOUT_S": "60",
        }
        with patch.dict(os.environ, env, clear=False):
            config = LoadTestConfig.from_env_and_options(None)
        assert config.callback_timeout_s == 60
