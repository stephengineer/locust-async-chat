import os
from unittest.mock import patch

import pytest

from locust_async_chat.llm.config import LLMResource, LLMConfig, load_llm_config


@pytest.fixture()
def _no_dotenv():
    """Prevent load_dotenv from loading the real .env during tests."""
    with patch("dotenv.load_dotenv"):
        yield


class TestLLMResource:
    def test_fields(self):
        r = LLMResource(
            base_url="https://res.openai.azure.com",
            api_key="key-1",
            provider="gpt",
            deployments=["gpt-5.4", "gpt-4o-mini"],
        )
        assert r.base_url == "https://res.openai.azure.com"
        assert r.provider == "gpt"
        assert r.deployments == ["gpt-5.4", "gpt-4o-mini"]

    def test_full_base_url_gpt(self):
        r = LLMResource(
            base_url="https://res.openai.azure.com",
            api_key="k",
            provider="gpt",
            deployments=[],
        )
        assert r.full_base_url == "https://res.openai.azure.com/openai/v1/"

    def test_full_base_url_claude(self):
        r = LLMResource(
            base_url="https://res.openai.azure.com",
            api_key="k",
            provider="claude",
            deployments=[],
        )
        assert r.full_base_url == "https://res.openai.azure.com/anthropic"

    def test_full_base_url_strips_trailing_slash(self):
        r = LLMResource(
            base_url="https://res.openai.azure.com/",
            api_key="k",
            provider="gpt",
            deployments=[],
        )
        assert r.full_base_url == "https://res.openai.azure.com/openai/v1/"


class TestLLMConfig:
    def _make_config(self, **kwargs):
        defaults = {
            "resources": [
                LLMResource(
                    base_url="https://res-a.openai.azure.com",
                    api_key="key-a",
                    provider="gpt",
                    deployments=["gpt-5.4", "gpt-4o-mini"],
                ),
                LLMResource(
                    base_url="https://res-b.openai.azure.com",
                    api_key="key-b",
                    provider="claude",
                    deployments=["claude-sonnet-4-6"],
                ),
            ],
            "deployment": "gpt-5.4",
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        defaults.update(kwargs)
        return LLMConfig(**defaults)

    def test_resolve_resource_gpt(self):
        cfg = self._make_config()
        r = cfg.resolve_resource("gpt-5.4")
        assert r.provider == "gpt"
        assert r.api_key == "key-a"

    def test_resolve_resource_claude(self):
        cfg = self._make_config()
        r = cfg.resolve_resource("claude-sonnet-4-6")
        assert r.provider == "claude"

    def test_resolve_resource_not_found(self):
        cfg = self._make_config()
        try:
            cfg.resolve_resource("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "nonexistent" in str(e)

    def test_all_deployments(self):
        cfg = self._make_config()
        deps = cfg.all_deployments()
        assert deps == ["gpt-5.4", "gpt-4o-mini", "claude-sonnet-4-6"]

    def test_all_deployments_empty(self):
        cfg = self._make_config(resources=[])
        assert cfg.all_deployments() == []


@pytest.mark.usefixtures("_no_dotenv")
class TestLoadLLMConfig:
    def test_loads_single_resource(self):
        env = {
            "LLM_RESOURCE_1_BASE_URL": "https://res.openai.azure.com",
            "LLM_RESOURCE_1_API_KEY": "key-1",
            "LLM_RESOURCE_1_PROVIDER": "gpt",
            "LLM_RESOURCE_1_DEPLOYMENTS": "gpt-5.4,gpt-4o-mini",
            "LLM_DEPLOYMENT": "gpt-5.4",
            "LLM_TEMPERATURE": "0.9",
            "LLM_MAX_TOKENS": "1024",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = load_llm_config()
        assert len(cfg.resources) == 1
        assert cfg.resources[0].deployments == ["gpt-5.4", "gpt-4o-mini"]
        assert cfg.deployment == "gpt-5.4"
        assert cfg.temperature == 0.9
        assert cfg.max_tokens == 1024

    def test_loads_multiple_resources(self):
        env = {
            "LLM_RESOURCE_1_BASE_URL": "https://res-a.openai.azure.com",
            "LLM_RESOURCE_1_API_KEY": "key-a",
            "LLM_RESOURCE_1_PROVIDER": "gpt",
            "LLM_RESOURCE_1_DEPLOYMENTS": "gpt-5.4",
            "LLM_RESOURCE_2_BASE_URL": "https://res-b.openai.azure.com",
            "LLM_RESOURCE_2_API_KEY": "key-b",
            "LLM_RESOURCE_2_PROVIDER": "claude",
            "LLM_RESOURCE_2_DEPLOYMENTS": "claude-sonnet-4-6,claude-haiku",
            "LLM_DEPLOYMENT": "claude-sonnet-4-6",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = load_llm_config()
        assert len(cfg.resources) == 2
        assert cfg.all_deployments() == ["gpt-5.4", "claude-sonnet-4-6", "claude-haiku"]

    def test_skips_resource_with_empty_base_url(self):
        env = {
            "LLM_RESOURCE_1_BASE_URL": "https://res.openai.azure.com",
            "LLM_RESOURCE_1_API_KEY": "key-1",
            "LLM_RESOURCE_1_PROVIDER": "gpt",
            "LLM_RESOURCE_1_DEPLOYMENTS": "gpt-5.4",
            "LLM_RESOURCE_2_BASE_URL": "",
            "LLM_RESOURCE_2_API_KEY": "",
            "LLM_RESOURCE_2_PROVIDER": "",
            "LLM_RESOURCE_2_DEPLOYMENTS": "",
            "LLM_DEPLOYMENT": "gpt-5.4",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = load_llm_config()
        assert len(cfg.resources) == 1

    def test_defaults_when_no_env(self):
        env = {
            "LLM_RESOURCE_1_BASE_URL": "https://res.openai.azure.com",
            "LLM_RESOURCE_1_API_KEY": "key-1",
            "LLM_RESOURCE_1_PROVIDER": "gpt",
            "LLM_RESOURCE_1_DEPLOYMENTS": "gpt-5.4",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = load_llm_config()
        assert cfg.deployment == "gpt-5.4"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 2048
