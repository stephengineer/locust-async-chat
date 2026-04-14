"""
Parsing utilities for extracting IDs from responses.

Provides functions to parse conversation IDs and correlation IDs from API responses.
"""

from typing import Optional


def parse_correlation_id(submit_response: dict) -> Optional[str]:
    """
    Extract correlationID from SUT submit response.

    The SUT returns correlationID in payload.message.metadata.correlationID.

    Args:
        submit_response: JSON response from the SUT POST message endpoint

    Returns:
        The correlationID string if found, None otherwise
    """
    payload = submit_response.get("payload", {})
    message = payload.get("message", {})
    metadata = message.get("metadata", {})
    correlation_id = metadata.get("correlationID")
    if correlation_id:
        return str(correlation_id)
    return None


def parse_conversation_id(login_response: dict) -> Optional[str]:
    """
    Extract conversation ID from login response.

    Args:
        login_response: JSON response from the SUT login endpoint

    Returns:
        The conversation ID string if found, None otherwise
    """
    conversations = login_response.get("conversations", [])
    if conversations and isinstance(conversations, list):
        first_conv = conversations[0]
        if isinstance(first_conv, dict) and "id" in first_conv:
            return str(first_conv["id"])
    return None
