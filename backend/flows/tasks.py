# backend/flows/tasks.py
"""
Celery tasks for the flows app.

Aligned with morebnyemba/hanna's flows/tasks.py.
Provides dedicated flow processing tasks that run asynchronously,
creating outgoing Message records and queuing send_whatsapp_message_task.
"""
import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from conversations.models import Message, Contact
from .services import process_message_for_flow

logger = logging.getLogger(__name__)


@shared_task(queue='celery')
def process_flow_for_message_task(message_id: int):
    """
    Asynchronously runs the entire flow engine for an incoming message.

    Matches hanna's process_flow_for_message_task:
    1. Loads the Message from DB (with content_payload or reconstructed data)
    2. Calls process_message_for_flow() to evaluate the flow logic
    3. Creates outgoing Message records for each send action
    4. Queues send_whatsapp_message_task for each outgoing message

    Args:
        message_id: ID of the incoming Message to process
    """
    from meta_integration.models import MetaAppConfig
    from meta_integration.tasks import send_whatsapp_message_task

    try:
        # Collect tasks to dispatch after the transaction commits
        tasks_to_dispatch = []

        with transaction.atomic():
            incoming_message = Message.objects.select_related(
                'contact', 'app_config'
            ).get(pk=message_id)
            contact = incoming_message.contact

            # Use content_payload if available (matches hanna), else reconstruct
            message_data = incoming_message.content_payload or _build_message_data_from_model(incoming_message)

            actions = process_message_for_flow(contact, message_data)

            if not actions:
                logger.info(f"Flow processing for message {message_id} resulted in no actions.")
                return

            config_to_use = incoming_message.app_config
            if not config_to_use:
                logger.warning(f"Message {message_id} has no app_config. Falling back to active config.")
                config_to_use = MetaAppConfig.objects.get_active_config()

            dispatch_countdown = 0
            for action in actions:
                action_type = action.get('type')

                if action_type == 'send_whatsapp_message':
                    wa_id = action.get('recipient_wa_id')
                    msg_type = action.get('message_type', 'text')
                    data = action.get('data', {})

                    if not wa_id or data is None:
                        continue

                    # Create outgoing Message record (matches hanna)
                    outgoing_msg = Message.objects.create(
                        contact=contact,
                        conversation=incoming_message.conversation,
                        app_config=config_to_use,
                        direction='outbound',
                        message_type=msg_type,
                        content_payload=data,
                        content=_summarize_outgoing(msg_type, data),
                        timestamp=timezone.now(),
                        status='pending_dispatch',
                        status_timestamp=timezone.now(),
                        replied_to=incoming_message,
                    )

                    tasks_to_dispatch.append(
                        (outgoing_msg.id, config_to_use.id, dispatch_countdown)
                    )
                    dispatch_countdown += 2

                elif action_type == 'send_typing_indicator':
                    # Typing is handled as part of read receipt task
                    pass

                elif action_type and action_type.startswith('_internal_'):
                    # Internal commands handled by the engine
                    pass

                else:
                    logger.warning(f"Unknown action type: {action_type}")

        # Dispatch Celery tasks after transaction commits
        for msg_id, config_id, countdown in tasks_to_dispatch:
            send_whatsapp_message_task.apply_async(
                args=[msg_id, config_id],
                countdown=countdown,
            )

    except Message.DoesNotExist:
        logger.error(f"process_flow_for_message_task: Message {message_id} not found.")
    except Exception as e:
        logger.error(
            f"Critical error in process_flow_for_message_task for message {message_id}: {e}",
            exc_info=True,
        )


@shared_task(queue='celery')
def process_flow_continuation_task(contact_id: int, message_data: dict):
    """
    Run the flow engine for a synthetic/internal message (e.g., after WhatsApp flow response).

    Used when there is no real Message object — for example, when triggering
    flow continuation with an internal_whatsapp_flow_response after the context
    has already been updated by the response processor.

    Args:
        contact_id: ID of the Contact to process
        message_data: Structured message dict (e.g., {'type': 'internal_whatsapp_flow_response'})
    """
    from meta_integration.models import MetaAppConfig
    from meta_integration.tasks import send_whatsapp_message_task
    from conversations.models import Conversation

    try:
        tasks_to_dispatch = []

        with transaction.atomic():
            contact = Contact.objects.get(pk=contact_id)
            actions = process_message_for_flow(contact, message_data)

            if not actions:
                logger.info(f"Flow continuation for contact {contact_id} resulted in no actions.")
                return

            config_to_use = MetaAppConfig.objects.get_active_config()

            # Get or create conversation for outgoing messages
            conversation = Conversation.objects.filter(
                contact=contact, status='active'
            ).first()
            if not conversation:
                conversation = Conversation.objects.create(
                    contact=contact,
                    title=f"Chat with {contact.profile_name or contact.phone_number}",
                    status='active',
                )

            dispatch_countdown = 0
            for action in actions:
                action_type = action.get('type')

                if action_type == 'send_whatsapp_message':
                    wa_id = action.get('recipient_wa_id')
                    msg_type = action.get('message_type', 'text')
                    data = action.get('data', {})

                    if not wa_id or data is None:
                        continue

                    outgoing_msg = Message.objects.create(
                        contact=contact,
                        conversation=conversation,
                        app_config=config_to_use,
                        direction='outbound',
                        message_type=msg_type,
                        content_payload=data,
                        content=_summarize_outgoing(msg_type, data),
                        timestamp=timezone.now(),
                        status='pending_dispatch',
                        status_timestamp=timezone.now(),
                    )

                    tasks_to_dispatch.append(
                        (outgoing_msg.id, config_to_use.id, dispatch_countdown)
                    )
                    dispatch_countdown += 2

                elif action_type == 'send_typing_indicator':
                    pass
                elif action_type and action_type.startswith('_internal_'):
                    pass
                else:
                    logger.warning(f"Unknown action type: {action_type}")

        for msg_id, config_id, countdown in tasks_to_dispatch:
            send_whatsapp_message_task.apply_async(
                args=[msg_id, config_id],
                countdown=countdown,
            )

    except Contact.DoesNotExist:
        logger.error(f"process_flow_continuation_task: Contact {contact_id} not found.")
    except Exception as e:
        logger.error(
            f"Critical error in process_flow_continuation_task for contact {contact_id}: {e}",
            exc_info=True,
        )


def _summarize_outgoing(msg_type: str, data: dict) -> str:
    """Create a short text summary for an outgoing message's content field."""
    if msg_type == 'text':
        return data.get('body', '')[:200]
    elif msg_type == 'template':
        return f"[Template: {data.get('name', 'unknown')}]"
    elif msg_type == 'interactive':
        interactive_type = data.get('type', 'unknown')
        return f"[Interactive: {interactive_type}]"
    elif msg_type == 'image':
        return f"[Image: {data.get('id', data.get('link', ''))}]"
    else:
        return f"[{msg_type} message]"


def _build_message_data_from_model(message: Message) -> dict:
    """
    Reconstruct structured message_data from a Message model instance.

    Used as fallback when content_payload is not available.

    Args:
        message: The Message instance

    Returns:
        Structured message_data dict
    """
    msg_type = message.message_type or 'text'

    if msg_type == 'interactive' and message.interactive_data:
        return {
            'type': 'interactive',
            'interactive': message.interactive_data,
        }
    elif msg_type == 'location':
        location_data = {}
        if message.location_latitude is not None:
            location_data['latitude'] = float(message.location_latitude)
        if message.location_longitude is not None:
            location_data['longitude'] = float(message.location_longitude)
        if message.location_name:
            location_data['name'] = message.location_name
        if message.location_address:
            location_data['address'] = message.location_address
        return {
            'type': 'location',
            'location': location_data,
        }
    elif msg_type == 'image':
        return {
            'type': 'image',
            'image': {'id': message.media_id} if message.media_id else {},
        }
    else:
        return {
            'type': 'text',
            'text': {'body': message.content or ''},
        }
