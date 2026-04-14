"""
Callback payload models for webhook responses.

Defines the payload structures for callbacks received from the SUT via webhook.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CallbackMessageContent:
    content_type: str = "text"
    text: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "CallbackMessageContent":
        return cls(
            content_type=data.get("type", "text"),
            text=data.get("text", ""),
        )


@dataclass
class CallbackAuthorUser:
    user_id: str = ""
    external_id: str = ""
    given_name: str = ""
    surname: str = ""
    email: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "CallbackAuthorUser":
        profile = data.get("profile", {})
        return cls(
            user_id=data.get("id", ""),
            external_id=data.get("externalId", ""),
            given_name=profile.get("givenName", ""),
            surname=profile.get("surname", ""),
            email=profile.get("email", ""),
        )


@dataclass
class CallbackAuthor:
    author_type: str = "business"
    display_name: str = ""
    avatar_url: str = ""
    user: Optional[CallbackAuthorUser] = None

    @classmethod
    def from_dict(cls, data: dict) -> "CallbackAuthor":
        user_data = data.get("user")
        return cls(
            author_type=data.get("type", "business"),
            display_name=data.get("displayName", ""),
            avatar_url=data.get("avatarUrl", ""),
            user=CallbackAuthorUser.from_dict(user_data) if user_data else None,
        )


@dataclass
class CallbackMessage:
    author: CallbackAuthor
    content: CallbackMessageContent
    source: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "CallbackMessage":
        return cls(
            author=CallbackAuthor.from_dict(data.get("author", {})),
            content=CallbackMessageContent.from_dict(data.get("content", {})),
            source=data.get("source", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CallbackConversation:
    conversation_id: str = ""
    active_switch_board_name: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "CallbackConversation":
        switch_board = data.get("activeSwitchBoard", {})
        return cls(
            conversation_id=data.get("id", ""),
            active_switch_board_name=switch_board.get("name", ""),
        )


@dataclass
class CallbackPayloadData:
    conversation: CallbackConversation
    message: CallbackMessage

    @classmethod
    def from_dict(cls, data: dict) -> "CallbackPayloadData":
        return cls(
            conversation=CallbackConversation.from_dict(data.get("conversation", {})),
            message=CallbackMessage.from_dict(data.get("message", {})),
        )


@dataclass
class CallbackPayload:
    payload_type: str = "message"
    request_id: str = ""
    created_at: str = ""
    data: Optional[CallbackPayloadData] = None

    @classmethod
    def from_dict(cls, payload: dict) -> "CallbackPayload":
        payload_data = payload.get("payload")
        return cls(
            payload_type=payload.get("type", "message"),
            request_id=payload.get("id", ""),
            created_at=payload.get("createdAt", ""),
            data=CallbackPayloadData.from_dict(payload_data) if payload_data else None,
        )

    @property
    def response_text(self) -> str:
        if self.data and self.data.message:
            return self.data.message.content.text
        return ""

    @property
    def conversation_id(self) -> str:
        if self.data and self.data.conversation:
            return self.data.conversation.conversation_id
        return ""

    @property
    def correlation_id(self) -> str:
        if self.data and self.data.message:
            return str(self.data.message.metadata.get("correlationID", ""))
        return ""

    @property
    def author_type(self) -> str:
        if self.data and self.data.message:
            return self.data.message.author.author_type
        return ""
