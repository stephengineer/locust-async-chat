"""
Webhook receiver server for SUT callbacks.

Runs a lightweight Flask server using gevent WSGI to receive
webhook callbacks from the System Under Test (SUT).
"""

import hmac
import hashlib
import logging
from typing import Optional

import gevent
from gevent import pywsgi
from flask import Flask, request, jsonify

from locust_async_chat.infrastructure.registry import CallbackRegistry, get_registry

# Configure logging
logger = logging.getLogger(__name__)


class WebhookServer:
    """
    Lightweight webhook receiver server using Flask + gevent.

    Runs in the same process as Locust, receiving callbacks from
    the SUT and resolving pending requests in the CallbackRegistry.

    Example usage:
        server = WebhookServer(
            host="0.0.0.0",
            port=44379,
            auth_secret="my-secret"
        )
        server.start()  # Non-blocking, runs in greenlet

        # ... run load tests ...

        server.stop()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 44379,
        auth_secret: str = "",
        registry: Optional[CallbackRegistry] = None,
        switchboard_name: str = "",
    ):
        """
        Initialize the webhook server.

        Args:
            host: Host to bind the server
            port: Port to bind the server
            auth_secret: HMAC secret for signature verification (empty = no auth)
            registry: CallbackRegistry instance (uses global if not provided)
            switchboard_name: Filter callbacks by switchboard name (empty = accept all)
        """
        self.host = host
        self.port = port
        self.auth_secret = auth_secret
        self.registry = registry or get_registry()
        self.switchboard_name = switchboard_name

        # Create Flask app
        self.app = Flask(__name__)
        self._setup_routes()

        # Server instance
        self._server: Optional[pywsgi.WSGIServer] = None
        self._greenlet: Optional[gevent.Greenlet] = None

    def _setup_routes(self) -> None:
        """Configure Flask routes."""

        @self.app.route("/health", methods=["GET"])
        def health() -> tuple:
            """Health check endpoint."""
            return (
                jsonify({"status": "ok", "pending": self.registry.pending_count()}),
                200,
            )

        @self.app.route("/webhooks/chat-complete", methods=["POST"])
        def webhook_callback() -> tuple:
            """
            Handle webhook callbacks from SUT.

            Expected headers:
                X-Webhook-Signature: HMAC-SHA256 signature (if auth enabled)
                Content-Type: application/json

            Expected body: CallbackPayload JSON
            """
            # Get raw body for signature verification
            raw_body = request.get_data()

            # Verify signature if auth is enabled
            if self.auth_secret:
                signature = request.headers.get("X-Webhook-Signature", "")
                if not self._verify_signature(raw_body, signature):
                    logger.warning("Invalid webhook signature")
                    return jsonify({"error": "Invalid signature"}), 403

            # Parse payload
            try:
                payload_dict = request.get_json()
                if not payload_dict:
                    return jsonify({"error": "Empty payload"}), 400
            except Exception as e:
                logger.error(f"Failed to parse webhook payload: {e}")
                return jsonify({"error": "Invalid JSON"}), 400

            if payload_dict.get("type") != "message":
                logger.debug(f"Ignoring non-message type: {payload_dict.get('type')}")
                return "", 204

            payload_data = payload_dict.get("payload", {})
            conversation_data = payload_data.get("conversation", {})
            message_data = payload_data.get("message", {})
            content_type = message_data.get("content", {}).get("type", "")

            switchboard = conversation_data.get("activeSwitchBoard", {})
            switchboard_name = switchboard.get("name", "") if switchboard else ""
            if self.switchboard_name and switchboard_name != self.switchboard_name:
                logger.debug(
                    f"Ignoring conversation with switchboard '{switchboard_name}' "
                    f"(expected '{self.switchboard_name}')"
                )
                return "", 204

            if content_type != "text":
                logger.debug(f"Ignoring non-text content type: {content_type}")
                return "", 204

            if message_data.get("author", {}).get("type") == "user":
                logger.debug(
                    f"Ignoring user author type: {message_data.get('author', {}).get('type')}"
                )
                return "", 204

            metadata = message_data.get("metadata", {})
            request_id = metadata.get("correlationID", "")

            if not request_id:
                logger.warning("Webhook received without correlationID")
                return jsonify({"error": "Missing correlationID"}), 400

            # Resolve the pending request
            resolved = self.registry.resolve(request_id, payload_dict)

            if resolved:
                logger.debug(f"Resolved callback for request {request_id}")
                return jsonify({"status": "received", "request_id": request_id}), 200
            else:
                logger.warning(f"No pending request found for {request_id}")
                return (
                    jsonify(
                        {
                            "status": "not_found",
                            "request_id": request_id,
                            "message": "No pending request with this ID",
                        }
                    ),
                    200,
                )  # Still return 200 to avoid SUT retries

        @self.app.route("/webhooks/chat-complete", methods=["GET"])
        def webhook_info() -> tuple:
            """Info endpoint for the webhook."""
            return (
                jsonify(
                    {
                        "endpoint": "/webhooks/chat-complete",
                        "method": "POST",
                        "auth": "hmac-sha256" if self.auth_secret else "none",
                        "pending_requests": self.registry.pending_count(),
                    }
                ),
                200,
            )

    def _verify_signature(self, raw_body: bytes, received_signature: str) -> bool:
        """
        Verify HMAC-SHA256 signature.

        Args:
            raw_body: Raw request body bytes
            received_signature: Signature from header

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.auth_secret:
            return True

        if not received_signature:
            return False

        try:
            expected_signature = hmac.new(
                self.auth_secret.encode(), raw_body, hashlib.sha256
            ).hexdigest()
        except Exception as e:
            logger.error(f"Error computing signature: {e}")
            return False

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, received_signature)

    def start(self) -> None:
        """
        Start the webhook server in a background greenlet.

        Non-blocking - returns immediately after starting the server.
        """
        if self._server is not None:
            logger.warning("Server already running")
            return

        # Create WSGI server with gevent
        self._server = pywsgi.WSGIServer(
            (self.host, self.port),
            self.app,
            log=None,  # Disable access logging
        )

        # Start in background greenlet
        self._greenlet = gevent.spawn(self._server.serve_forever)
        logger.info(f"Webhook server started on {self.host}:{self.port}")

    def stop(self) -> None:
        """
        Stop the webhook server.

        Blocks until the server has fully stopped.
        """
        if self._server is None:
            return

        logger.info("Stopping webhook server...")
        self._server.stop()

        if self._greenlet is not None:
            self._greenlet.kill()
            self._greenlet = None

        self._server = None
        logger.info("Webhook server stopped")

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._server is not None and self._greenlet is not None

    @property
    def address(self) -> str:
        """Get the server address."""
        return f"http://{self.host}:{self.port}"

    @property
    def webhook_url(self) -> str:
        """Get the full webhook callback URL."""
        return f"{self.address}/webhooks/chat-complete"


# Global server instance
_server: Optional[WebhookServer] = None


def get_server() -> Optional[WebhookServer]:
    """
    Get the global webhook server instance.

    Returns:
        WebhookServer instance or None if not created
    """
    return _server


def create_server(
    host: str = "0.0.0.0",
    port: int = 44379,
    auth_secret: str = "",
    registry: Optional[CallbackRegistry] = None,
    switchboard_name: str = "",
) -> WebhookServer:
    """
    Create and set the global webhook server instance.

    Args:
        host: Host to bind the server
        port: Port to bind the server
        auth_secret: HMAC secret for signature verification
        registry: CallbackRegistry instance
        switchboard_name: Filter callbacks by switchboard name (empty = accept all)

    Returns:
        WebhookServer instance
    """
    global _server
    _server = WebhookServer(
        host=host,
        port=port,
        auth_secret=auth_secret,
        registry=registry,
        switchboard_name=switchboard_name,
    )
    return _server


def start_server(
    host: str = "0.0.0.0",
    port: int = 44379,
    auth_secret: str = "",
    registry: Optional[CallbackRegistry] = None,
    switchboard_name: str = "",
) -> WebhookServer:
    """
    Create and start the global webhook server.

    Args:
        host: Host to bind the server
        port: Port to bind the server
        auth_secret: HMAC secret for signature verification
        registry: CallbackRegistry instance
        switchboard_name: Filter callbacks by switchboard name (empty = accept all)

    Returns:
        Running WebhookServer instance
    """
    server = create_server(host, port, auth_secret, registry, switchboard_name)
    server.start()
    return server


def stop_server() -> None:
    """Stop the global webhook server if running."""
    global _server
    if _server is not None:
        _server.stop()
        _server = None
