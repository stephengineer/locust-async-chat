"""
Message payload models for sending messages to SUT.

Defines the payload structure for messages sent to the SUT API.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from locust_async_chat.models.login import (
    LoginResponseUser,
    LoginResponseSource,
    LoginResponseConversation,
)


@dataclass
class MessagePayload:
    conversation: Optional[LoginResponseConversation] = None
    conversation_id: Optional[str] = None
    user: LoginResponseUser = None  # type: ignore[assignment]
    source: LoginResponseSource = None  # type: ignore[assignment]
    text: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )

    def to_dict(self) -> dict:
        if self.conversation is not None:
            conversation_payload = {
                "id": self.conversation.id,
                "activeSwitchBoard": {
                    "name": self.conversation.active_switch_board_name
                },
                "createdAt": self.conversation.created_at,
                "lastUpdatedAt": self.conversation.last_updated_at,
                "businessLastReadAt": self.conversation.business_last_read_at,
                "metadata": self.conversation.metadata,
            }
        elif self.conversation_id is not None:
            # Backwards-compatible minimal payload for legacy conversation_id usage.
            conversation_payload = {
                "id": self.conversation_id,
                "activeSwitchBoard": {"name": ""},
                "createdAt": "",
                "lastUpdatedAt": "",
                "businessLastReadAt": "",
                "metadata": {},
            }
        else:
            raise ValueError(
                "MessagePayload requires either 'conversation' or 'conversation_id'."
            )

        return {
            "type": "message",
            "payload": {
                "conversation": conversation_payload,
                "message": {
                    "author": {
                        "displayName": f"{self.user.given_name}",
                        "type": "user",
                        "avatarUrl": self.user.avatar_url,
                        "user": {
                            "id": self.user.user_id,
                            "externalId": self.user.external_id,
                            "profile": {
                                "givenName": self.user.given_name,
                                "surname": self.user.surname,
                                "email": self.user.email,
                                "avatarUrl": self.user.avatar_url,
                                "locale": self.user.locale,
                                "localeOrigin": self.user.locale_origin,
                            },
                            "signedUpAt": self.user.signed_up_at,
                            "metadata": self.user.metadata,
                            "authenticated": self.user.authenticated,
                            "toBeRetained": self.user.to_be_retained,
                        },
                    },
                    "content": {"type": "text", "text": self.text},
                    "source": {
                        "type": self.source.source_type,
                        "integrationId": self.source.integration_id,
                        "device": {
                            "id": self.source.device.id,
                            "guid": self.source.device.guid,
                            "clientId": self.source.device.client_id,
                            "integrationId": self.source.device.integration_id,
                            "type": self.source.device.device_type,
                            "status": self.source.device.status,
                            "info": self.source.device.info,
                            "lastSeen": self.source.device.last_seen,
                        },
                    },
                },
            },
            "id": "loadtestmessages",
            "createdAt": self.created_at,
        }
