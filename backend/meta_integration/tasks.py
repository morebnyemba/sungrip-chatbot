"""
Celery tasks for meta_integration app.

Aligned with morebnyemba/hanna's meta_integration/tasks.py.
Contains only outbound tasks:
  - send_whatsapp_message_task   (send a queued outgoing message)
  - send_read_receipt_task       (mark an incoming message as read)
  - download_whatsapp_media_task (download media to a temp file)

Webhook processing is handled synchronously in views.py (not via tasks).
"""
import logging
import tempfile
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from .models import MetaAppConfig
from .utils import send_whatsapp_message, send_read_receipt_api, download_whatsapp_media

logger = logging.getLogger(__name__)


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

    # --- Send via utility (matches hanna's direct call pattern) ---
    try:
        if not isinstance(outgoing_msg.content_payload, dict):
            raise ValueError("Message content_payload is not a valid dictionary for sending.")

        api_response = send_whatsapp_message(
            to_phone_number=outgoing_msg.contact.whatsapp_id,
            message_type=outgoing_msg.message_type,
            data=outgoing_msg.content_payload,
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

    # Broadcast outbound message to WebSocket subscribers in real time
    try:
        from conversations.consumers import broadcast_message_to_websocket
        broadcast_message_to_websocket(outgoing_msg)
    except Exception as ws_exc:
        logger.warning(f"WebSocket broadcast failed for outbound message {outgoing_message_id}: {ws_exc}")


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_read_receipt_task(self, wamid: str, config_id: int, show_typing_indicator: bool = False):
    """
    Celery task to send a read receipt for a given message ID.
    Optionally sends a typing indicator.

    Matches hanna's send_read_receipt_task pattern — calls send_read_receipt_api utility.

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
        api_response = send_read_receipt_api(
            wamid=wamid,
            config=active_config,
            show_typing_indicator=show_typing_indicator,
        )

        if not api_response or not api_response.get('success'):
            raise ValueError(f"Read receipt API call failed for WAMID {wamid}. Response: {api_response}")

        logger.info(f"Read receipt sent for WAMID {wamid}")

    except Exception as e:
        logger.warning(f"Exception in send_read_receipt_task for WAMID {wamid}, will retry. Error: {e}")
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for sending read receipt for WAMID {wamid}.")


@shared_task(name="meta_integration.download_whatsapp_media_task")
def download_whatsapp_media_task(media_id: str, config_id: int):
    """
    Downloads media from WhatsApp and saves it to a temporary file.

    Matches hanna's download_whatsapp_media_task.

    Args:
        media_id: The WhatsApp Media ID to download
        config_id: MetaAppConfig ID

    Returns:
        str: Path to the temporary file, or None on failure
    """
    log_prefix = f"[Media Download Task - Media ID: {media_id}]"
    try:
        config = MetaAppConfig.objects.get(pk=config_id)
        download_result = download_whatsapp_media(media_id, config)

        if download_result is None:
            logger.error(f"{log_prefix} download_whatsapp_media utility returned None.")
            return None

        media_content, mime_type = download_result

        if media_content and mime_type:
            suffix = f".{mime_type.split('/')[-1].split(';')[0]}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(media_content)
                logger.info(f"{log_prefix} Media saved to temporary file: {temp_file.name}")
                return temp_file.name
        else:
            logger.error(f"{log_prefix} Failed to download media content from WhatsApp.")
            return None

    except MetaAppConfig.DoesNotExist:
        logger.error(f"{log_prefix} MetaAppConfig with ID {config_id} not found.")
        return None
    except Exception as e:
        logger.error(f"{log_prefix} Unexpected error during media download: {e}", exc_info=True)
        return None

