"""
Celery tasks for meta_integration app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Handles asynchronous webhook processing and message sending.
"""
import logging
from celery import shared_task
from django.utils import timezone
from typing import Dict, Any

from .models import MetaAppConfig, WebhookEventLog
from .services import WhatsAppAPIService, WebhookProcessor
from .utils import extract_message_from_webhook, extract_status_from_webhook

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_webhook_event_task(self, webhook_log_id: int):
    """
    Process a webhook event asynchronously.

    This task:
    1. Retrieves the WebhookEventLog
    2. Processes based on event type (message, status, etc.)
    3. Creates/updates Contact and Message records
    4. Triggers flow processing if applicable
    5. Updates the log with processing status

    Args:
        webhook_log_id: ID of the WebhookEventLog to process

    Returns:
        dict: Processing result
    """
    try:
        webhook_log = WebhookEventLog.objects.get(id=webhook_log_id)
        payload = webhook_log.payload

        logger.info(f"Processing webhook event {webhook_log_id}: {webhook_log.event_type}")

        # Process based on event type
        if webhook_log.event_type == "message":
            result = _process_incoming_message(webhook_log, payload)
        elif webhook_log.event_type == "message_status":
            result = _process_message_status(webhook_log, payload)
        else:
            result = {"status": "ignored", "reason": f"Event type {webhook_log.event_type} not processed"}

        # Update webhook log
        webhook_log.processing_status = "processed"
        webhook_log.processed_at = timezone.now()
        webhook_log.processing_notes = result.get("notes", "Processed successfully")
        webhook_log.save()

        logger.info(f"Webhook event {webhook_log_id} processed successfully")
        return result

    except WebhookEventLog.DoesNotExist:
        logger.error(f"WebhookEventLog {webhook_log_id} not found")
        return {"status": "error", "message": "Webhook log not found"}
    except Exception as e:
        logger.error(f"Error processing webhook event {webhook_log_id}: {str(e)}", exc_info=True)

        # Update webhook log with error
        try:
            webhook_log = WebhookEventLog.objects.get(id=webhook_log_id)
            webhook_log.processing_status = "error"
            webhook_log.processing_notes = f"Error: {str(e)}"
            webhook_log.save()
        except:
            pass

        # Retry the task
        raise self.retry(exc=e)


def _process_incoming_message(webhook_log: WebhookEventLog, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an incoming message from webhook payload.

    Args:
        webhook_log: WebhookEventLog instance
        payload: Webhook payload dict

    Returns:
        dict: Processing result
    """
    from conversations.models import Contact, Message

    message_data = extract_message_from_webhook(payload)
    if not message_data:
        return {"status": "error", "message": "No message data in payload"}

    from_number = message_data.get("from")
    message_id = message_data.get("id")
    message_type = message_data.get("type", "text")
    timestamp = message_data.get("timestamp")

    # Get or create contact
    contact, created = Contact.objects.get_or_create(
        phone_number=from_number,
        defaults={
            "name": message_data.get("profile", {}).get("name", from_number)
        }
    )

    # Extract message content based on type
    content = ""
    if message_type == "text":
        content = message_data.get("text", {}).get("body", "")
    elif message_type == "image":
        content = f"[Image: {message_data.get('image', {}).get('id', '')}]"
    elif message_type == "document":
        content = f"[Document: {message_data.get('document', {}).get('filename', '')}]"
    elif message_type == "audio":
        content = "[Audio message]"
    elif message_type == "video":
        content = "[Video message]"
    else:
        content = f"[{message_type} message]"

    # Create message record
    message = Message.objects.create(
        contact=contact,
        direction="inbound",
        message_type=message_type,
        content=content,
        whatsapp_message_id=message_id,
        status="received",
        metadata=message_data
    )

    # Link message to webhook log
    webhook_log.message = message
    webhook_log.save()

    logger.info(f"Created message {message.id} from contact {contact.phone_number}")

    # Trigger flow processing (if applicable)
    _trigger_flow_processing(contact, message, content)

    return {
        "status": "success",
        "message_id": message.id,
        "contact_id": contact.id,
        "notes": f"Message processed from {from_number}"
    }


def _process_message_status(webhook_log: WebhookEventLog, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a message status update from webhook payload.

    Args:
        webhook_log: WebhookEventLog instance
        payload: Webhook payload dict

    Returns:
        dict: Processing result
    """
    from conversations.models import Message

    status_data = extract_status_from_webhook(payload)
    if not status_data:
        return {"status": "error", "message": "No status data in payload"}

    message_id = status_data.get("id")
    status = status_data.get("status")  # sent, delivered, read, failed

    # Update message status
    try:
        message = Message.objects.get(whatsapp_message_id=message_id)
        message.status = status
        message.save()

        logger.info(f"Updated message {message.id} status to {status}")
        return {
            "status": "success",
            "message_id": message.id,
            "new_status": status,
            "notes": f"Status updated to {status}"
        }
    except Message.DoesNotExist:
        logger.warning(f"Message with whatsapp_message_id {message_id} not found")
        return {
            "status": "ignored",
            "message": f"Message {message_id} not found in database"
        }


def _trigger_flow_processing(contact, message, content: str):
    """
    Trigger flow processing based on message content.

    Args:
        contact: Contact instance
        message: Message instance
        content: Message text content
    """
    from flows.models import Flow, FlowSession

    # Check if contact has an active flow session
    active_session = FlowSession.objects.filter(
        contact=contact,
        status='active'
    ).first()

    if active_session:
        # Process within existing flow
        from flows.services import FlowProcessor
        processor = FlowProcessor(active_session)
        processor.process_user_reply(content)
    else:
        # Check for flow triggers
        content_lower = content.lower()
        triggered_flow = Flow.objects.filter(
            is_active=True,
            trigger_keywords__icontains=content_lower
        ).first()

        if triggered_flow:
            # Start new flow session
            from flows.services import FlowProcessor
            processor = FlowProcessor.start_flow(triggered_flow, contact)
            logger.info(f"Started flow {triggered_flow.name} for contact {contact.phone_number}")


@shared_task
def send_message_task(phone_number: str, message_config: Dict[str, Any], config_id: int = None):
    """
    Send a WhatsApp message asynchronously.

    Args:
        phone_number: Recipient phone number in E.164 format
        message_config: Message configuration dict
        config_id: Optional MetaAppConfig ID. If None, uses active config.

    Returns:
        dict: API response
    """
    try:
        config = None
        if config_id:
            config = MetaAppConfig.objects.get(id=config_id)

        service = WhatsAppAPIService(config=config)
        result = service.send_message(phone_number, message_config)

        logger.info(f"Message sent to {phone_number} via task")
        return result
    except Exception as e:
        logger.error(f"Error sending message to {phone_number}: {str(e)}", exc_info=True)
        raise


@shared_task
def mark_message_as_read_task(message_id: str, config_id: int = None):
    """
    Mark a WhatsApp message as read asynchronously.

    Args:
        message_id: WhatsApp message ID (wamid)
        config_id: Optional MetaAppConfig ID. If None, uses active config.

    Returns:
        dict: API response
    """
    try:
        config = None
        if config_id:
            config = MetaAppConfig.objects.get(id=config_id)

        service = WhatsAppAPIService(config=config)
        result = service.mark_message_as_read(message_id)

        logger.info(f"Message {message_id} marked as read via task")
        return result
    except Exception as e:
        logger.error(f"Error marking message as read: {str(e)}", exc_info=True)
        raise
