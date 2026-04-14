import pytest

from locust_async_chat.models.callback import (
    CallbackMessageContent,
    CallbackAuthorUser,
    CallbackAuthor,
    CallbackConversation,
    CallbackPayload,
)
from locust_async_chat.models.login import (
    LoginRequestPayload,
    LoginResponseDevice,
    LoginResponseSource,
    LoginResponseConversation,
    LoginResponseUser,
)
from locust_async_chat.models.message import MessagePayload

# ── Callback models ──────────────────────────────────────────────


class TestCallbackMessageContent:
    def test_from_dict(self):
        content = CallbackMessageContent.from_dict({"type": "text", "text": "hi"})
        assert content.content_type == "text"
        assert content.text == "hi"

    def test_defaults_on_empty_dict(self):
        content = CallbackMessageContent.from_dict({})
        assert content.content_type == "text"
        assert content.text == ""


class TestCallbackAuthorUser:
    def test_extracts_profile_fields(self):
        data = {
            "id": "u1",
            "externalId": "e1",
            "profile": {
                "givenName": "Jane",
                "surname": "Smith",
                "email": "jane@example.com",
            },
        }
        user = CallbackAuthorUser.from_dict(data)
        assert user.user_id == "u1"
        assert user.external_id == "e1"
        assert user.given_name == "Jane"
        assert user.surname == "Smith"
        assert user.email == "jane@example.com"

    def test_defaults_when_profile_missing(self):
        user = CallbackAuthorUser.from_dict({})
        assert user.given_name == ""
        assert user.email == ""


class TestCallbackAuthor:
    def test_with_user(self):
        data = {
            "type": "business",
            "displayName": "Bot",
            "avatarUrl": "https://img.png",
            "user": {
                "id": "u1",
                "externalId": "e1",
                "profile": {"givenName": "Bot"},
            },
        }
        author = CallbackAuthor.from_dict(data)
        assert author.author_type == "business"
        assert author.display_name == "Bot"
        assert author.user is not None
        assert author.user.user_id == "u1"

    def test_without_user(self):
        author = CallbackAuthor.from_dict({"type": "system"})
        assert author.author_type == "system"
        assert author.user is None


class TestCallbackConversation:
    def test_extracts_switch_board(self):
        data = {"id": "conv-1", "activeSwitchBoard": {"name": "TestBot"}}
        conv = CallbackConversation.from_dict(data)
        assert conv.conversation_id == "conv-1"
        assert conv.active_switch_board_name == "TestBot"

    def test_defaults(self):
        conv = CallbackConversation.from_dict({})
        assert conv.conversation_id == ""
        assert conv.active_switch_board_name == ""


class TestCallbackPayload:
    def test_full_parse(self, full_callback_dict):
        payload = CallbackPayload.from_dict(full_callback_dict)
        assert payload.payload_type == "message"
        assert payload.request_id == "req-abc-123"
        assert payload.data is not None

    def test_properties(self, full_callback_dict):
        payload = CallbackPayload.from_dict(full_callback_dict)
        assert payload.response_text == "Hello, how can I help?"
        assert payload.conversation_id == "conv-001"
        assert payload.correlation_id == "corr-xyz-789"
        assert payload.author_type == "business"

    def test_properties_return_empty_when_no_data(self):
        payload = CallbackPayload.from_dict({})
        assert payload.data is None
        assert payload.response_text == ""
        assert payload.conversation_id == ""
        assert payload.correlation_id == ""
        assert payload.author_type == ""


# ── Login models ─────────────────────────────────────────────────


class TestLoginRequestPayload:
    def test_to_dict_uses_camel_case_keys(self):
        payload = LoginRequestPayload(given_name="Alice", surname="Test")
        d = payload.to_dict()
        assert d["givenName"] == "Alice"
        assert d["surname"] == "Test"
        assert "given_name" not in d

    def test_defaults(self):
        payload = LoginRequestPayload()
        d = payload.to_dict()
        assert d["givenName"] == "John"
        assert d["locale"] == "en-US"


class TestLoginResponseDevice:
    def test_from_dict(self):
        data = {
            "id": "dev-1",
            "guid": "guid-1",
            "clientId": "c1",
            "integrationId": "int-1",
            "type": "mobile",
            "status": "active",
            "info": {"os": "iOS"},
        }
        device = LoginResponseDevice.from_dict(data)
        assert device.id == "dev-1"
        assert device.guid == "guid-1"
        assert device.device_type == "mobile"
        assert device.info == {"os": "iOS"}

    def test_defaults(self):
        device = LoginResponseDevice.from_dict({})
        assert device.device_type == "web"
        assert device.status == "active"


class TestLoginResponseConversation:
    def test_from_dict(self):
        data = {
            "id": "conv-1",
            "createdAt": "2026-01-01",
            "activeSwitchBoard": {"name": "TestBot"},
            "metadata": {"key": "val"},
        }
        conv = LoginResponseConversation.from_dict(data)
        assert conv.id == "conv-1"
        assert conv.active_switch_board_name == "TestBot"
        assert conv.metadata == {"key": "val"}


class TestLoginResponseUser:
    def test_from_dict(self, login_response_dict):
        user = LoginResponseUser.from_dict(login_response_dict)
        assert user.user_id == "user-42"
        assert user.given_name == "John"
        assert user.surname == "Doe1"
        assert user.email == "john.doe1@locust.com"
        assert user.authenticated is True

    def test_defaults_on_empty(self):
        user = LoginResponseUser.from_dict({})
        assert user.user_id == ""
        assert user.locale == "en-US"


# ── Message payload ──────────────────────────────────────────────


class TestMessagePayload:
    def _make_user(self, login_response_dict):
        return LoginResponseUser.from_dict(login_response_dict)

    def _make_source(self):
        return LoginResponseSource.from_dict(
            {
                "type": "api:conversations",
                "integrationId": "int-1",
                "device": {
                    "guid": "g1",
                    "integrationId": "int-1",
                    "type": "web",
                    "info": {},
                },
            }
        )

    def _make_conversation(self):
        return LoginResponseConversation.from_dict(
            {
                "id": "conv-1",
                "createdAt": "2026-01-01",
                "activeSwitchBoard": {"name": "TestBot"},
            }
        )

    def test_to_dict_with_conversation_object(self, login_response_dict):
        msg = MessagePayload(
            conversation=self._make_conversation(),
            user=self._make_user(login_response_dict),
            source=self._make_source(),
            text="Hello",
        )
        d = msg.to_dict()
        assert d["type"] == "message"
        assert d["payload"]["conversation"]["id"] == "conv-1"
        assert d["payload"]["message"]["content"]["text"] == "Hello"

    def test_to_dict_with_conversation_id_string(self, login_response_dict):
        msg = MessagePayload(
            conversation_id="conv-2",
            user=self._make_user(login_response_dict),
            source=self._make_source(),
            text="Hi",
        )
        d = msg.to_dict()
        assert d["payload"]["conversation"]["id"] == "conv-2"
        assert d["payload"]["conversation"]["activeSwitchBoard"]["name"] == ""

    def test_raises_without_conversation(self, login_response_dict):
        msg = MessagePayload(
            user=self._make_user(login_response_dict),
            source=self._make_source(),
            text="Oops",
        )
        with pytest.raises(ValueError, match="requires either"):
            msg.to_dict()
