"""
Utility functions for meta_integration app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Provides helper functions for WhatsApp API interactions.
"""
import logging
from typing import Dict, Any, Optional

from .models import MetaAppConfig
from .services import WhatsAppAPIService

logger = logging.getLogger(__name__)


def send_whatsapp_message(
    phone_number: str,
    message_config: Dict[str, Any],
    config: Optional[MetaAppConfig] = None
) -> Dict[str, Any]:
    """
    Send a WhatsApp message using the Meta Business API.

    This is a convenience function that wraps WhatsAppAPIService.

    Args:
        phone_number: Recipient phone number in E.164 format (e.g., +263771234567)
        message_config: Message configuration dict with structure:
            {
                "message_type": "text|template|image|document|interactive",
                "text": {"body": "..."} for text messages,
                "template": {...} for template messages,
                etc.
            }
        config: MetaAppConfig instance. If None, uses the active config.

    Returns:
        dict: API response containing message ID and status

    Example:
        >>> send_whatsapp_message(
        ...     "+263771234567",
        ...     {"message_type": "text", "text": {"body": "Hello!"}}
        ... )
        {'messages': [{'id': 'wamid.XXX'}]}
    """
    try:
        service = WhatsAppAPIService(config=config)
        return service.send_message(phone_number, message_config)
    except Exception as e:
        logger.error(f"Error sending WhatsApp message to {phone_number}: {str(e)}")
        raise


def send_text_message(
    phone_number: str,
    text: str,
    config: Optional[MetaAppConfig] = None
) -> Dict[str, Any]:
    """
    Send a simple text message via WhatsApp.

    Args:
        phone_number: Recipient phone number in E.164 format
        text: Message text content
        config: MetaAppConfig instance. If None, uses the active config.

    Returns:
        dict: API response containing message ID

    Example:
        >>> send_text_message("+263771234567", "Hello from Sungrip Solar!")
    """
    message_config = {
        "message_type": "text",
        "text": {"body": text}
    }
    return send_whatsapp_message(phone_number, message_config, config)


def send_template_message(
    phone_number: str,
    template_name: str,
    language_code: str = "en",
    components: Optional[list] = None,
    config: Optional[MetaAppConfig] = None
) -> Dict[str, Any]:
    """
    Send a WhatsApp template message.

    Args:
        phone_number: Recipient phone number in E.164 format
        template_name: Name of the approved WhatsApp template
        language_code: Language code (default: "en")
        components: List of template components (header, body, buttons)
        config: MetaAppConfig instance. If None, uses the active config.

    Returns:
        dict: API response containing message ID

    Example:
        >>> send_template_message(
        ...     "+263771234567",
        ...     "solar_quote_request",
        ...     components=[{
        ...         "type": "body",
        ...         "parameters": [{"type": "text", "text": "John"}]
        ...     }]
        ... )
    """
    message_config = {
        "message_type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code}
        }
    }

    if components:
        message_config["template"]["components"] = components

    return send_whatsapp_message(phone_number, message_config, config)


def get_active_whatsapp_config() -> MetaAppConfig:
    """
    Get the currently active WhatsApp configuration.

    Returns:
        MetaAppConfig: Active configuration instance

    Raises:
        MetaAppConfig.DoesNotExist: If no active config exists
    """
    return MetaAppConfig.objects.get_active_config()


def send_typing_indicator(
    phone_number: str,
    config: Optional[MetaAppConfig] = None
) -> Dict[str, Any]:
    """
    Send typing indicator to show "typing..." status to recipient.

    The typing indicator is displayed for approximately 10 seconds or until
    a message is sent to the user, whichever comes first. Useful for creating
    a more natural conversation experience.

    Args:
        phone_number: Recipient phone number in E.164 format
        config: MetaAppConfig instance. If None, uses the active config.

    Returns:
        dict: API response

    Example:
        >>> send_typing_indicator("+263771234567")
        {'success': True}
    """
    try:
        service = WhatsAppAPIService(config=config)
        return service.send_typing_indicator(phone_number)
    except Exception as e:
        logger.error(f"Error sending typing indicator to {phone_number}: {str(e)}")
        raise


def format_phone_number(phone: str) -> str:
    """
    Format phone number to E.164 format.

    Args:
        phone: Phone number in any format

    Returns:
        str: Phone number in E.164 format

    Example:
        >>> format_phone_number("0771234567")
        '+263771234567'
        >>> format_phone_number("+263771234567")
        '+263771234567'
    """
    # Remove spaces, dashes, and other non-numeric characters
    cleaned = ''.join(filter(str.isdigit, phone))

    # Add Zimbabwe country code if not present
    if not phone.startswith('+'):
        if cleaned.startswith('0'):
            cleaned = '263' + cleaned[1:]
        elif not cleaned.startswith('263'):
            cleaned = '263' + cleaned

    return '+' + cleaned


def extract_message_from_webhook(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract message data from webhook payload.

    Args:
        payload: Webhook payload dict

    Returns:
        dict: Message data or None if not a message event

    Example payload structure:
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "+263771234567",
                            "id": "wamid.XXX",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }]
                    }
                }]
            }]
        }
    """
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            return messages[0]
        return None
    except (IndexError, KeyError, AttributeError):
        return None


def extract_status_from_webhook(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract message status update from webhook payload.

    Args:
        payload: Webhook payload dict

    Returns:
        dict: Status data or None if not a status event
    """
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        statuses = value.get("statuses", [])

        if statuses:
            return statuses[0]
        return None
    except (IndexError, KeyError, AttributeError):
        return None
