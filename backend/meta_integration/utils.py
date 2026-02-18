"""
Utility functions for meta_integration app.

Aligned with morebnyemba/hanna's meta_integration/utils.py.
Provides direct helper functions for WhatsApp API interactions.
"""
import json
import logging
import requests
from typing import Dict, Any, Optional, Tuple

from .models import MetaAppConfig

logger = logging.getLogger(__name__)


def get_active_meta_config_for_sending() -> Optional[MetaAppConfig]:
    """
    Get the active MetaAppConfig for sending messages.
    Matches hanna's helper function.

    Returns:
        MetaAppConfig instance, or None
    """
    try:
        return MetaAppConfig.objects.get_active_config()
    except Exception:
        logger.error("Cannot retrieve active MetaAppConfig for sending.")
        return None


def send_whatsapp_message(
    to_phone_number: str,
    message_type: str,
    data: dict,
    config: Optional[MetaAppConfig] = None,
) -> Optional[Dict[str, Any]]:
    """
    Send a WhatsApp message using the Meta Graph API.
    Matches hanna's send_whatsapp_message signature.

    Args:
        to_phone_number: The recipient's WhatsApp ID (phone number).
        message_type: Type of message ('text', 'interactive', 'template', 'image', etc.).
        data: The payload specific to the message type.
        config: MetaAppConfig instance. If None, tries to fetch the active one.

    Returns:
        dict: The JSON response from Meta API on success.
              On error, returns a dict with 'error' key.
              Returns None only if config is not available.
    """
    if not config:
        config = get_active_meta_config_for_sending()

    if not config:
        logger.error("Cannot send WhatsApp message: No active MetaAppConfig available.")
        return None

    api_version = config.api_version
    phone_number_id = config.phone_number_id
    access_token = config.access_token

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone_number,
        "type": message_type,
        message_type: data,
    }

    if message_type == "text" and "preview_url" in data:
        if not isinstance(data["preview_url"], bool):
            data["preview_url"] = bool(data["preview_url"])

    logger.debug(f"Sending WhatsApp message via config '{config.name}'. URL: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        response_json = response.json()
        logger.info(
            f"Message sent successfully to {to_phone_number} via config '{config.name}'. "
            f"Response: {response_json}"
        )
        return response_json
    except requests.exceptions.HTTPError as e:
        error_body = {}
        try:
            error_body = e.response.json()
        except Exception:
            error_body = {'raw_text': e.response.text[:500]}
        logger.error(
            f"HTTP error sending message to {to_phone_number}: "
            f"{e.response.status_code} - {error_body}"
        )
        return {
            'error': error_body,
            'status_code': e.response.status_code,
            'error_type': error_body.get('error', {}).get('type', 'Unknown'),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error sending message to {to_phone_number}: {e}")
        return {'error': str(e)}


def send_read_receipt_api(
    wamid: str,
    config: MetaAppConfig,
    show_typing_indicator: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Send a read receipt to the Meta Graph API for a specific message.
    Matches hanna's send_read_receipt_api utility.

    Args:
        wamid: The WhatsApp Message ID to mark as read.
        config: The MetaAppConfig instance to use.
        show_typing_indicator: If True, includes a typing indicator.

    Returns:
        dict: The JSON response from Meta API, or None on failure.
    """
    if not config:
        logger.error("Cannot send read receipt: No MetaAppConfig provided.")
        return None

    url = f"https://graph.facebook.com/{config.api_version}/{config.phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": wamid,
    }

    if show_typing_indicator:
        payload["typing_indicator"] = {"type": "text"}

    logger.debug(f"Sending read receipt for WAMID {wamid} via config '{config.name}'.")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        response_json = response.json()
        logger.info(f"Read receipt sent for WAMID {wamid} via config '{config.name}'.")
        return response_json
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"HTTP error sending read receipt for WAMID {wamid}: "
            f"{e.response.status_code} - {e.response.text}"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error sending read receipt for WAMID {wamid}: {e}")

    return None


def download_whatsapp_media(
    media_id: str,
    config: MetaAppConfig,
) -> Optional[Tuple[bytes, str]]:
    """
    Downloads media from WhatsApp using a given Media ID.
    Matches hanna's download_whatsapp_media utility.

    Args:
        media_id: The Media ID of the file to download.
        config: The active MetaAppConfig containing the API token.

    Returns:
        Tuple of (content_bytes, mime_type) or None on failure.
    """
    if not all([media_id, config, config.access_token]):
        logger.error("download_whatsapp_media: Missing media_id, config, or access_token.")
        return None

    # 1. Get Media URL
    get_url_endpoint = f"https://graph.facebook.com/{config.api_version}/{media_id}/"
    headers = {"Authorization": f"Bearer {config.access_token}"}

    try:
        response = requests.get(get_url_endpoint, headers=headers, timeout=10)
        response.raise_for_status()
        media_info = response.json()
        media_url = media_info.get("url")
        mime_type = media_info.get("mime_type")

        if not media_url:
            logger.error(f"No URL returned for media ID {media_id}.")
            return None

        # 2. Download the actual media content
        media_response = requests.get(media_url, headers=headers, timeout=30)
        media_response.raise_for_status()

        logger.info(f"Downloaded media {media_id} ({mime_type}, {len(media_response.content)} bytes).")
        return media_response.content, mime_type

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading media {media_id}: {e}")
        return None
