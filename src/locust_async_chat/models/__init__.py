"""
Payload models for SUT load testing.

Provides data models for:
- Callback payloads (webhook responses)
- Login payloads (authentication)
- Message payloads (sending messages)
- Parsing utilities
"""

# Callback models
from locust_async_chat.models.callback import (
    CallbackPayload,
    CallbackPayloadData,
    CallbackMessage,
    CallbackAuthor,
    CallbackAuthorUser,
    CallbackMessageContent,
    CallbackConversation,
)

# Login models
from locust_async_chat.models.login import (
    LoginRequestPayload,
    LoginResponseUser,
    LoginResponseDevice,
    LoginResponseSource,
    LoginResponseConversation,
)

# Message models
from locust_async_chat.models.message import MessagePayload

# Parsers
from locust_async_chat.models.parsers import (
    parse_conversation_id,
    parse_correlation_id,
)

__all__ = [
    # Callback models
    "CallbackPayload",
    "CallbackPayloadData",
    "CallbackMessage",
    "CallbackAuthor",
    "CallbackAuthorUser",
    "CallbackMessageContent",
    "CallbackConversation",
    # Login models
    "LoginRequestPayload",
    "LoginResponseUser",
    "LoginResponseDevice",
    "LoginResponseSource",
    "LoginResponseConversation",
    # Message models
    "MessagePayload",
    # Parsers
    "parse_conversation_id",
    "parse_correlation_id",
]
