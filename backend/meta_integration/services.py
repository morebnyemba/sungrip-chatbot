"""
WhatsApp Business API service layer for meta_integration app.

Aligned with morebnyemba/hanna's meta_integration architecture.
Provides WhatsAppAPIService for programmatic message sending.

Note: Webhook processing is handled synchronously in views.py.
      Direct API calls (send_whatsapp_message, send_read_receipt_api,
      download_whatsapp_media) are now in utils.py matching hanna's pattern.
"""
import logging
from typing import Dict, Any, Optional

from .models import MetaAppConfig

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

    def send_typing_indicator(self, to: str) -> Dict[str, Any]:
        """
        Send typing indicator to show "typing..." status.

        The typing indicator is displayed for approximately 10 seconds or until
        a message is sent to the user, whichever comes first.

        Args:
            to: Phone number in E.164 format (e.g., +263771234567)

        Returns:
            dict: API response

        Example:
            >>> service.send_typing_indicator("+263771234567")
            {'success': True}
        """
        import requests

        url = f"{self.base_url}/{self.config.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "typing_action",
            "typing_action": {"status": "typing"}
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Typing indicator sent to {to}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send typing indicator to {to}: {str(e)}")
            raise
