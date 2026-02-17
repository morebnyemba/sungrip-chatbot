"""
Celery tasks for meta_integration app.

Aligned with morebnyemba/hanna's meta_integration/tasks.py.
Contains outbound message tasks (send_whatsapp_message_task, send_read_receipt_task)
plus the webhook processing pipeline.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from typing import Dict, Any

from .models import MetaAppConfig, WebhookEventLog
from .services import WhatsAppAPIService, WebhookProcessor
from .utils import extract_message_from_webhook, extract_status_from_webhook, send_whatsapp_message

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
        elif webhook_log.event_type == "flow_response":
            result = _process_flow_response(webhook_log, payload)
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

    Following hanna's pattern:
    1. Creates Contact, Conversation, and Message records (with content_payload)
    2. Sends read receipt + typing via Celery task
    3. Queues the dedicated flow processing task

    Args:
        webhook_log: WebhookEventLog instance
        payload: Webhook payload dict

    Returns:
        dict: Processing result
    """
    from conversations.models import Contact, Message, Conversation

    message_data = extract_message_from_webhook(payload)
    if not message_data:
        return {"status": "error", "message": "No message data in payload"}

    from_number = message_data.get("from")
    wamid = message_data.get("id")
    message_type = message_data.get("type", "text")

    # Get or create contact (use whatsapp_id as unique key, matching hanna)
    contact, created = Contact.objects.get_or_create(
        whatsapp_id=from_number,
        defaults={
            "phone_number": from_number,
            "profile_name": message_data.get("profile", {}).get("name", from_number),
        }
    )

    # Extract text preview
    content = _extract_content_text(message_data, message_type)

    # Get or create a conversation for this contact
    conversation = Conversation.objects.filter(
        contact=contact, status='active'
    ).first()
    if not conversation:
        conversation = Conversation.objects.create(
            contact=contact,
            title=f"Chat with {contact.profile_name or contact.phone_number}",
            status='active',
        )

    # Get active config from webhook log
    config = getattr(webhook_log, 'app_config', None)

    # Create message record with content_payload (matches hanna)
    message = Message.objects.create(
        conversation=conversation,
        contact=contact,
        message_id=wamid,
        direction="inbound",
        message_type=message_type,
        content=content,
        content_payload=message_data,
        app_config=config,
        interactive_data=message_data.get('interactive') if message_type == 'interactive' else None,
        media_id=message_data.get(message_type, {}).get('id', '') if message_type in ('image', 'video', 'audio', 'document') else '',
        location_latitude=message_data.get('location', {}).get('latitude') if message_type == 'location' else None,
        location_longitude=message_data.get('location', {}).get('longitude') if message_type == 'location' else None,
        location_name=message_data.get('location', {}).get('name', '') if message_type == 'location' else '',
        location_address=message_data.get('location', {}).get('address', '') if message_type == 'location' else '',
        timestamp=timezone.now(),
        status="received",
        status_timestamp=timezone.now(),
    )

    # Link message to webhook log
    webhook_log.message = message
    webhook_log.save()

    logger.info(f"Created message {message.id} from contact {contact.phone_number}")

    # Send read receipt + typing indicator via Celery task (matches hanna)
    if config and wamid:
        send_read_receipt_task.delay(
            wamid=wamid,
            config_id=config.id,
            show_typing_indicator=True,
        )

    # Queue the dedicated flow processing task (matches hanna pattern)
    _trigger_flow_processing(message)

    return {
        "status": "success",
        "message_id": message.id,
        "contact_id": contact.id,
        "notes": f"Message processed from {from_number}"
    }


def _extract_content_text(message_data: dict, message_type: str) -> str:
    """Extract a text preview from message data for the content field."""
    if message_type == "text":
        return message_data.get("text", {}).get("body", "")
    elif message_type == "image":
        return f"[Image: {message_data.get('image', {}).get('id', '')}]"
    elif message_type == "document":
        return f"[Document: {message_data.get('document', {}).get('filename', '')}]"
    elif message_type == "audio":
        return "[Audio message]"
    elif message_type == "video":
        return "[Video message]"
    elif message_type == "interactive":
        return "[Interactive message]"
    else:
        return f"[{message_type} message]"


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

    wamid = status_data.get("id")
    new_status = status_data.get("status")  # sent, delivered, read, failed

    # Update message status (use message_id field — matches hanna's wamid lookup)
    try:
        message = Message.objects.get(message_id=wamid)
        message.status = new_status
        message.status_timestamp = timezone.now()
        message.save(update_fields=['status', 'status_timestamp'])

        logger.info(f"Updated message {message.id} status to {new_status}")
        return {
            "status": "success",
            "message_id": message.id,
            "new_status": new_status,
            "notes": f"Status updated to {new_status}"
        }
    except Message.DoesNotExist:
        logger.warning(f"Message with WAMID {wamid} not found for status update")
        return {
            "status": "ignored",
            "message": f"Message {wamid} not found in database"
        }


def _trigger_flow_processing(message):
    """
    Queue flow processing via the dedicated Celery task.

    Matches hanna's pattern: the webhook handler creates a Message, then
    queues process_flow_for_message_task to run the flow engine asynchronously.

    Args:
        message: Message instance (must be saved with a valid ID)
    """
    from flows.tasks import process_flow_for_message_task

    process_flow_for_message_task.delay(message.id)


def _process_flow_response(webhook_log: WebhookEventLog, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a WhatsApp Flow response from webhook payload.

    Following hanna's pattern:
    1. Extracts the nfm_reply message from the webhook payload
    2. Gets/creates contact and conversation
    3. Creates a Message record for the flow response (with content_payload)
    4. Calls process_whatsapp_flow_response() from services (updates context)
    5. Queues process_flow_for_message_task with the Message ID

    Args:
        webhook_log: WebhookEventLog instance
        payload: Webhook payload dict

    Returns:
        dict: Processing result
    """
    from conversations.models import Contact, Message, Conversation
    from flows.services import process_whatsapp_flow_response
    from flows.tasks import process_flow_for_message_task

    try:
        # Extract flow response message from webhook payload
        messages = payload.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('messages', [])

        if not messages:
            return {"status": "error", "message": "No messages in flow response payload"}

        msg_data = messages[0]
        from_number = msg_data.get('from')
        wamid = msg_data.get('id')
        message_type = msg_data.get('type')

        if message_type != 'interactive':
            return {"status": "error", "message": f"Expected interactive message type, got {message_type}"}

        interactive_data = msg_data.get('interactive', {})
        if interactive_data.get('type') != 'nfm_reply':
            return {"status": "error", "message": f"Expected nfm_reply type, got {interactive_data.get('type')}"}

        # Get or create contact
        contact, _ = Contact.objects.get_or_create(
            whatsapp_id=from_number,
            defaults={
                "phone_number": from_number,
                "profile_name": from_number,
            }
        )

        # Get or create conversation
        conversation = Conversation.objects.filter(
            contact=contact, status='active'
        ).first()
        if not conversation:
            conversation = Conversation.objects.create(
                contact=contact,
                title=f"Chat with {contact.profile_name or contact.phone_number}",
                status='active',
            )

        config = getattr(webhook_log, 'app_config', None)

        # Create Message record for the flow response (matches hanna)
        message, _ = Message.objects.update_or_create(
            message_id=wamid,
            defaults={
                'conversation': conversation,
                'contact': contact,
                'app_config': config,
                'direction': 'inbound',
                'message_type': 'interactive',
                'content': '[WhatsApp Flow Response]',
                'content_payload': msg_data,
                'interactive_data': interactive_data,
                'timestamp': timezone.now(),
                'status': 'received',
                'status_timestamp': timezone.now(),
            }
        )

        # Link to webhook log
        webhook_log.message = message
        webhook_log.save()

        # Process via services.py (updates context only, matches hanna pattern)
        success, notes = process_whatsapp_flow_response(msg_data, contact, config)

        if success:
            # Queue flow task with the Message ID (matches hanna)
            process_flow_for_message_task.delay(message.id)
            logger.info(f"Queued flow processing for flow response message {message.id}")
            return {
                "status": "success",
                "contact_id": contact.id,
                "notes": f"{notes} Flow task queued.",
            }
        else:
            logger.error(f"Failed to process flow response: {notes}")
            return {"status": "error", "message": notes}

    except Exception as e:
        logger.error(f"Error processing flow response: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Exception: {str(e)}"}


# =============================================================================
# Outbound Message Tasks (matches hanna's task architecture)
# =============================================================================

@shared_task(bind=True, max_retries=10, default_retry_delay=3)
def send_whatsapp_message_task(self, outgoing_message_id: int, active_config_id: int):
    """
    Celery task to send a WhatsApp message asynchronously.
    Updates the Message object's status based on the outcome.

    Matches hanna's send_whatsapp_message_task:
    - Takes Message ID + Config ID (not raw phone/content)
    - Loads Message from DB, manages sequential delivery
    - Calls send_whatsapp_message() utility
    - Updates message status with WAMID from API response
    - Retries with backoff on failure

    Args:
        outgoing_message_id: ID of the outgoing Message object to send
        active_config_id: ID of the MetaAppConfig to use for sending
    """
    from conversations.models import Message

    try:
        outgoing_msg = Message.objects.select_related('contact').get(pk=outgoing_message_id)
    except Message.DoesNotExist:
        logger.error(f"send_whatsapp_message_task: Message {outgoing_message_id} not found.")
        return

    try:
        active_config = MetaAppConfig.objects.get(pk=active_config_id)
    except MetaAppConfig.DoesNotExist:
        logger.error(f"send_whatsapp_message_task: Config {active_config_id} not found.")
        outgoing_msg.status = 'failed'
        outgoing_msg.error_message = f'MetaAppConfig ID {active_config_id} not found.'
        outgoing_msg.status_timestamp = timezone.now()
        outgoing_msg.save(update_fields=['status', 'error_message', 'status_timestamp'])
        return

    if outgoing_msg.direction != 'outbound':
        logger.warning(f"Message {outgoing_message_id} is not outbound. Skipping.")
        return

    # Skip if already sent successfully
    if outgoing_msg.message_id and outgoing_msg.status == 'sent':
        logger.info(
            f"Message {outgoing_message_id} already sent "
            f"(WAMID: {outgoing_msg.message_id}). Skipping."
        )
        return
    if outgoing_msg.status == 'failed' and self.request.retries >= self.max_retries:
        logger.warning(f"Message {outgoing_message_id} already failed and max retries reached. Skipping.")
        return

    # --- Sequential delivery logic (matches hanna) ---
    stale_threshold = timezone.now() - timedelta(seconds=20)
    stale_pending_threshold = timezone.now() - timedelta(minutes=1)

    halting_message = Message.objects.filter(
        Q(contact=outgoing_msg.contact),
        Q(direction='outbound'),
        Q(id__lt=outgoing_msg.id),
        (
            Q(status='pending_dispatch', timestamp__gte=stale_pending_threshold) |
            Q(status='sent', status_timestamp__gte=stale_threshold)
        )
    ).order_by('-id').first()

    if halting_message:
        logger.warning(
            f"send_whatsapp_message_task: Halting message {outgoing_message_id} for contact "
            f"{outgoing_msg.contact.whatsapp_id}. Waiting for preceding message "
            f"{halting_message.id} (Status: {halting_message.status}). Retrying."
        )
        try:
            raise self.retry()
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for message {outgoing_message_id} while waiting.")
            outgoing_msg.status = 'failed'
            outgoing_msg.error_code = 'max_retries_waiting'
            outgoing_msg.error_message = 'Max retries exceeded while waiting for preceding message.'
            outgoing_msg.status_timestamp = timezone.now()
            outgoing_msg.save(update_fields=['status', 'error_code', 'error_message', 'status_timestamp'])
            return

    logger.info(
        f"send_whatsapp_message_task started for Message {outgoing_message_id}, "
        f"Contact: {outgoing_msg.contact.whatsapp_id}"
    )

    # --- Build message_config and send ---
    try:
        if not isinstance(outgoing_msg.content_payload, dict):
            raise ValueError("Message content_payload is not a valid dictionary for sending.")

        # Reconstruct message_config: {message_type: ..., <type>: data}
        msg_config = {
            'message_type': outgoing_msg.message_type,
            outgoing_msg.message_type: outgoing_msg.content_payload,
        }

        api_response = send_whatsapp_message(
            phone_number=outgoing_msg.contact.whatsapp_id,
            message_config=msg_config,
            config=active_config,
        )

        if api_response and api_response.get('messages') and api_response['messages'][0].get('id'):
            outgoing_msg.message_id = api_response['messages'][0]['id']
            outgoing_msg.status = 'sent'
            outgoing_msg.error_code = ''
            outgoing_msg.error_message = ''
            logger.info(
                f"Message {outgoing_message_id} sent successfully. "
                f"WAMID: {outgoing_msg.message_id}"
            )
        else:
            error_info = api_response or {'error': 'Meta API returned unexpected response.'}
            logger.error(f"Failed to send Message {outgoing_message_id}: {error_info}")
            outgoing_msg.status = 'failed'
            outgoing_msg.error_message = str(error_info)[:500]
            raise ValueError("Meta API call failed.")

    except Exception as e:
        logger.error(
            f"Exception in send_whatsapp_message_task for Message {outgoing_message_id}: {e}",
            exc_info=True,
        )
        outgoing_msg.status = 'failed'
        outgoing_msg.error_message = str(e)[:500]
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for sending Message {outgoing_message_id}.")
            outgoing_msg.status_timestamp = timezone.now()
            outgoing_msg.save(
                update_fields=['message_id', 'status', 'error_code', 'error_message', 'status_timestamp']
            )
            return

    # Save final state on success
    outgoing_msg.status_timestamp = timezone.now()
    outgoing_msg.save(
        update_fields=['message_id', 'status', 'error_code', 'error_message', 'status_timestamp']
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_read_receipt_task(self, wamid: str, config_id: int, show_typing_indicator: bool = False):
    """
    Celery task to send a read receipt for a given message ID.
    Optionally sends a typing indicator.

    Matches hanna's send_read_receipt_task pattern.

    Args:
        wamid: WhatsApp message ID to mark as read
        config_id: MetaAppConfig ID
        show_typing_indicator: Whether to also show typing indicator
    """
    logger.info(f"send_read_receipt_task started for WAMID: {wamid} (Typing: {show_typing_indicator})")

    try:
        active_config = MetaAppConfig.objects.get(pk=config_id)
    except MetaAppConfig.DoesNotExist:
        logger.error(f"send_read_receipt_task: Config {config_id} not found.")
        return

    try:
        service = WhatsAppAPIService(config=active_config)

        # Send read receipt
        service.mark_message_as_read(wamid)
        logger.info(f"Read receipt sent for WAMID {wamid}")

        # Optionally send typing indicator
        if show_typing_indicator:
            try:
                from conversations.models import Message
                msg = Message.objects.filter(message_id=wamid).select_related('contact').first()
                if msg and msg.contact:
                    service.send_typing_indicator(msg.contact.whatsapp_id)
                    logger.info(f"Typing indicator sent for contact {msg.contact.whatsapp_id}")
            except Exception as e:
                logger.warning(f"Failed to send typing indicator for WAMID {wamid}: {e}")

    except Exception as e:
        logger.error(f"Error sending read receipt for WAMID {wamid}: {e}", exc_info=True)
        raise self.retry(exc=e)

