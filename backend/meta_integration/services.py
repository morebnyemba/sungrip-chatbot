"""
WhatsApp Business API service layer for meta_integration app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Handles message sending, webhook processing, and API interactions.
"""
import logging
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from django.conf import settings

from .models import MetaAppConfig, WebhookEventLog
from conversations.models import Contact, Message

logger = logging.getLogger(__name__)


class WhatsAppAPIService:
    """
    Service for interacting with the Meta WhatsApp Business API.
    Handles message sending, media uploads, and API calls.
    """

    def __init__(self, config: Optional[MetaAppConfig] = None):
        """
        Initialize the service with a MetaAppConfig.

        Args:
            config: MetaAppConfig instance. If None, uses the active config.
        """
        if config is None:
            config = MetaAppConfig.objects.get_active_config()
        self.config = config
        self.base_url = f"https://graph.facebook.com/{config.api_version}"
        self.headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json"
        }

    def send_text_message(self, to: str, text: str) -> Dict[str, Any]:
        """
        Send a text message to a WhatsApp number.

        Args:
            to: Phone number in E.164 format (e.g., +263771234567)
            text: Message text content

        Returns:
            dict: API response containing message ID
        """
        import requests

        url = f"{self.base_url}/{self.config.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Message sent successfully to {to}: {result.get('messages', [{}])[0].get('id')}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to {to}: {str(e)}")
            raise

    def send_template_message(self, to: str, template_name: str,
                             language_code: str = "en",
                             components: Optional[list] = None) -> Dict[str, Any]:
        """
        Send a template message to a WhatsApp number.

        Args:
            to: Phone number in E.164 format
            template_name: Name of the approved WhatsApp template
            language_code: Language code (default: "en")
            components: List of template components (header, body, buttons)

        Returns:
            dict: API response containing message ID
        """
        import requests

        url = f"{self.base_url}/{self.config.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code}
            }
        }

        if components:
            payload["template"]["components"] = components

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Template message sent to {to}: {template_name}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send template to {to}: {str(e)}")
            raise

    def send_message(self, to: str, message_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic message sender supporting multiple message types.

        Args:
            to: Phone number in E.164 format
            message_config: Message configuration dict with structure:
                {
                    "message_type": "text|template|image|document|interactive",
                    "text": {"body": "..."} for text messages,
                    "template": {...} for template messages,
                    etc.
                }

        Returns:
            dict: API response containing message ID
        """
        import requests

        message_type = message_config.get("message_type", "text")

        if message_type == "text":
            return self.send_text_message(to, message_config.get("text", {}).get("body", ""))
        elif message_type == "template":
            template_data = message_config.get("template", {})
            return self.send_template_message(
                to=to,
                template_name=template_data.get("name"),
                language_code=template_data.get("language", {}).get("code", "en"),
                components=template_data.get("components")
            )
        else:
            # Generic message sending for other types
            url = f"{self.base_url}/{self.config.phone_number_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": message_type,
                **{k: v for k, v in message_config.items() if k != "message_type"}
            }

            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                logger.info(f"{message_type} message sent to {to}")
                return result
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to send {message_type} message to {to}: {str(e)}")
                raise

    def mark_message_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.

        Args:
            message_id: WhatsApp message ID (wamid)

        Returns:
            dict: API response
        """
        import requests

        url = f"{self.base_url}/{self.config.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to mark message as read: {str(e)}")
            raise


class WebhookProcessor:
    """
    Processes incoming webhook events from Meta WhatsApp Business API.
    Handles signature verification, event parsing, and logging.
    """

    @staticmethod
    def verify_signature(payload: bytes, signature: str, app_secret: str) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.

        Args:
            payload: Raw request body as bytes
            signature: X-Hub-Signature-256 header value (format: "sha256=...")
            app_secret: App secret from MetaAppConfig

        Returns:
            bool: True if signature is valid
        """
        if not signature or not signature.startswith("sha256="):
            return False

        expected_signature = signature.split("sha256=")[1]
        computed_hmac = hmac.new(
            app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed_hmac, expected_signature)

    @staticmethod
    def extract_phone_number_id(payload: Dict[str, Any]) -> Optional[str]:
        """
        Extract phone_number_id from webhook payload.

        Args:
            payload: Webhook payload dict

        Returns:
            str: phone_number_id or None
        """
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            metadata = changes.get("value", {}).get("metadata", {})
            return metadata.get("phone_number_id")
        except (IndexError, KeyError, AttributeError):
            return None

    @staticmethod
    def extract_event_type(payload: Dict[str, Any]) -> str:
        """
        Determine event type from webhook payload.

        Args:
            payload: Webhook payload dict

        Returns:
            str: Event type (message, message_status, etc.)
        """
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})

            if "messages" in value:
                return "message"
            elif "statuses" in value:
                return "message_status"
            elif "contacts" in value:
                return "referral"
            else:
                return "unknown"
        except (IndexError, KeyError, AttributeError):
            return "unknown"

    @staticmethod
    def process_webhook_event(payload: Dict[str, Any], config: MetaAppConfig) -> WebhookEventLog:
        """
        Process a webhook event and create a log entry.

        Args:
            payload: Webhook payload dict
            config: MetaAppConfig instance

        Returns:
            WebhookEventLog: Created log entry
        """
        event_type = WebhookProcessor.extract_event_type(payload)
        phone_number_id = WebhookProcessor.extract_phone_number_id(payload)

        # Extract event identifier (e.g., wamid for messages)
        event_identifier = None
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})

            if "messages" in value:
                event_identifier = value["messages"][0].get("id")
            elif "statuses" in value:
                event_identifier = value["statuses"][0].get("id")
        except (IndexError, KeyError, AttributeError):
            pass

        # Create webhook log
        webhook_log = WebhookEventLog.objects.create(
            event_identifier=event_identifier,
            app_config=config,
            event_type=event_type,
            payload_object_type=payload.get("object"),
            payload=payload,
            phone_number_id_received=phone_number_id,
            waba_id_received=config.waba_id,
            processing_status="pending"
        )

        logger.info(f"Webhook event logged: {event_type} - {event_identifier}")
        return webhook_log
