"""
Login payload models for authentication.

Defines the payload structures for login requests and responses.
"""

from dataclasses import dataclass, field


@dataclass
class LoginRequestPayload:
    given_name: str = "John"
    surname: str = "Doe"
    email: str = "john.doe@locust.com"
    avatar_url: str = (
        "https://www.gravatar.com/avatar/00000000000000000000000000000000.png?s=200&d=mm"
    )
    locale: str = "en-US"
    locale_origin: str = "apiRequest"

    def to_dict(self) -> dict:
        return {
            "givenName": self.given_name,
            "surname": self.surname,
            "email": self.email,
            "avatarUrl": self.avatar_url,
            "locale": self.locale,
            "localeOrigin": self.locale_origin,
        }


@dataclass
class LoginResponseDevice:
    """
    Device information from login response.
    Maps to source.device in the login response.
    """

    guid: str
    integration_id: str
    device_type: str
    info: dict
    id: str = ""  # device id from server
    client_id: str = ""
    status: str = "active"
    last_seen: str = ""

    @classmethod
    def from_dict(cls, device: dict) -> "LoginResponseDevice":
        """Parse device from source.device dict."""
        return cls(
            id=device.get("id", ""),
            guid=device.get("guid", ""),
            client_id=device.get("clientId", ""),
            integration_id=device.get("integrationId", ""),
            device_type=device.get("type", "web"),
            status=device.get("status", "active"),
            info=device.get("info", {}),
            last_seen=device.get("lastSeen", "2025-12-19T07:59:05.329Z"),
        )


@dataclass
class LoginResponseSource:
    source_type: str
    integration_id: str
    device: LoginResponseDevice

    @classmethod
    def from_dict(cls, source: dict) -> "LoginResponseSource":
        device_data = source.get("device", {})
        return cls(
            source_type=source.get("type", "api:conversations"),
            integration_id=source.get("integrationId", ""),
            device=LoginResponseDevice.from_dict(device_data),
        )


@dataclass
class LoginResponseConversation:
    id: str
    created_at: str = ""
    last_updated_at: str = ""
    business_last_read_at: str = ""
    active_switch_board_name: str = ""
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, conv: dict) -> "LoginResponseConversation":
        switch_board = conv.get("activeSwitchBoard", {})
        return cls(
            id=conv.get("id", ""),
            created_at=conv.get("createdAt", ""),
            last_updated_at=conv.get("lastUpdatedAt", ""),
            business_last_read_at=conv.get(
                "businessLastReadAt", "2025-12-19T07:59:05.329Z"
            ),
            active_switch_board_name=switch_board.get("name", ""),
            metadata=conv.get("metadata", {}),
        )


@dataclass
class LoginResponseUser:
    user_id: str
    external_id: str
    given_name: str
    surname: str
    email: str
    avatar_url: str
    locale: str
    locale_origin: str
    signed_up_at: str
    metadata: dict
    authenticated: bool
    to_be_retained: bool

    @classmethod
    def from_dict(cls, data: dict) -> "LoginResponseUser":
        user = data.get("user", {})
        profile = user.get("profile", {})

        return cls(
            user_id=user.get("id", ""),
            external_id=user.get("externalId", ""),
            given_name=profile.get("givenName", ""),
            surname=profile.get("surname", ""),
            email=profile.get("email", ""),
            avatar_url=profile.get(
                "avatarUrl",
                "https://www.gravatar.com/avatar/00000000000000000000000000000000.png?s=200&d=mm",
            ),
            locale=profile.get("locale", "en-US"),
            locale_origin=profile.get("localeOrigin", "apiRequest"),
            signed_up_at=user.get("signedUpAt", ""),
            metadata=user.get("metadata", {}),
            authenticated=user.get("authenticated", True),
            to_be_retained=user.get("toBeRetained", True),
        )
