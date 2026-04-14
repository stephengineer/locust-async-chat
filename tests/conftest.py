import pytest

from locust_async_chat.config.config import LoadTestConfig


@pytest.fixture
def default_config() -> LoadTestConfig:
    """A LoadTestConfig with minimal required fields populated."""
    return LoadTestConfig(
        sut_login_url="https://example.com/api/v1/chat/login",
        sut_submit_url="https://example.com/api/v1/chat/messages",
        sut_auth_header="Bearer test-token",
    )


@pytest.fixture
def full_callback_dict() -> dict:
    """A realistic webhook callback payload dict."""
    return {
        "type": "message",
        "id": "req-abc-123",
        "createdAt": "2026-01-01T00:00:00Z",
        "payload": {
            "conversation": {
                "id": "conv-001",
                "activeSwitchBoard": {"name": "TestBot"},
            },
            "message": {
                "author": {
                    "type": "business",
                    "displayName": "Assistant",
                    "avatarUrl": "https://example.com/avatar.png",
                    "user": {
                        "id": "user-100",
                        "externalId": "ext-100",
                        "profile": {
                            "givenName": "Test",
                            "surname": "Bot",
                            "email": "bot@example.com",
                        },
                    },
                },
                "content": {"type": "text", "text": "Hello, how can I help?"},
                "source": {"type": "api"},
                "metadata": {"correlationID": "corr-xyz-789"},
            },
        },
    }


@pytest.fixture
def login_response_dict() -> dict:
    """A realistic login response dict."""
    return {
        "user": {
            "id": "user-42",
            "externalId": "ext-42",
            "profile": {
                "givenName": "John",
                "surname": "Doe1",
                "email": "john.doe1@locust.com",
                "avatarUrl": "https://example.com/avatar.png",
                "locale": "en-US",
                "localeOrigin": "apiRequest",
            },
            "signedUpAt": "2026-01-01T00:00:00Z",
            "metadata": {},
            "authenticated": True,
            "toBeRetained": True,
        },
        "conversations": [
            {
                "id": "conv-001",
                "createdAt": "2026-01-01T00:00:00Z",
                "lastUpdatedAt": "2026-01-01T00:00:00Z",
                "activeSwitchBoard": {"name": "TestBot"},
                "metadata": {},
            }
        ],
    }
