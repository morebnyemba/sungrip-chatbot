"""
WebSocket consumer for real-time conversation management.

Aligned with morebnyemba/hanna's conversation WebSocket pattern.
Each client connects to ws/conversations/<contact_id>/ and joins
a contact-specific group so all subscribers receive new messages.
"""
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from conversations.models import Contact, Message
from conversations.serializers import MessageSerializer, ContactSerializer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Broadcast helper — call from anywhere (Celery tasks, views, etc.)
# ---------------------------------------------------------------------------
def broadcast_message_to_websocket(message_obj):
    """
    Broadcast a Message instance to all WebSocket subscribers of that
    contact's conversation group.

    Safe to call from synchronous code (Celery tasks, views).
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("broadcast_message_to_websocket: No channel layer available")
        return

    contact_id = message_obj.contact_id
    group_name = f'conversation_{contact_id}'

    msg_data = MessageSerializer(message_obj).data
    # Ensure JSON-serializable (datetimes, Decimals, etc.)
    msg_data = json.loads(json.dumps(msg_data, default=str))

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {'type': 'new_message', 'message': msg_data},
        )
    except Exception as exc:
        logger.warning(f"broadcast_message_to_websocket failed for contact {contact_id}: {exc}")


class ConversationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for a single contact conversation.

    URL pattern:  ws/conversations/<contact_id>/
    Auth:         JWT token passed as ?token=<access_token> query param.
    """

    async def connect(self):
        user = self.scope.get('user')
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            logger.warning("WS rejected: unauthenticated user")
            await self.close(code=4001)
            return

        self.contact_id = self.scope['url_route']['kwargs']['contact_id']
        self.group_name = f'conversation_{self.contact_id}'

        # Verify contact exists
        contact = await self._get_contact(self.contact_id)
        if contact is None:
            logger.warning(f"WS rejected: contact {self.contact_id} not found")
            await self.close(code=4004)
            return

        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        except Exception as exc:
            logger.error(f"WS channel layer group_add failed: {exc}")
            await self.close(code=4500)
            return

        await self.accept()
        logger.debug(f"WS connected: user={user} contact={self.contact_id}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle messages sent from the browser."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')

        if msg_type == 'send_message':
            text = data.get('message', '').strip()
            if text:
                await self._send_whatsapp_message(text)

        elif msg_type == 'toggle_intervention':
            contact_data = await self._toggle_intervention()
            await self.channel_layer.group_send(
                self.group_name,
                {'type': 'contact_updated', 'contact': contact_data},
            )

    # -----------------------------------------------------------------------
    # Group event handlers (messages from channel layer)
    # -----------------------------------------------------------------------
    async def new_message(self, event):
        """Forward new_message event to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message'],
        }))

    async def contact_updated(self, event):
        """Forward contact_updated event to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'contact_updated',
            'contact': event['contact'],
        }))

    # -----------------------------------------------------------------------
    # DB helpers
    # -----------------------------------------------------------------------
    @database_sync_to_async
    def _get_contact(self, contact_id):
        try:
            return Contact.objects.get(pk=contact_id)
        except Contact.DoesNotExist:
            return None

    @database_sync_to_async
    def _toggle_intervention(self):
        contact = Contact.objects.get(pk=self.contact_id)
        contact.needs_human_intervention = not contact.needs_human_intervention
        contact.save(update_fields=['needs_human_intervention'])
        return ContactSerializer(contact).data

    @database_sync_to_async
    def _send_whatsapp_message(self, text):
        """Send a text message via the WhatsApp API and persist it."""
        from meta_integration.models import MetaAppConfig
        from conversations.models import Conversation
        from django.utils import timezone

        try:
            contact = Contact.objects.get(pk=self.contact_id)
            config = MetaAppConfig.objects.get_active_config()
        except Exception as e:
            logger.error(f"Cannot send message: {e}")
            return

        # Get or create the conversation for this contact
        conversation, _ = Conversation.objects.get_or_create(
            contact=contact,
            defaults={'status': 'active'},
        )

        # Persist as a pending outbound message
        msg = Message.objects.create(
            conversation=conversation,
            contact=contact,
            direction='outbound',
            message_type='text',
            content=text,
            content_payload={'body': text},
            status='pending_dispatch',
            timestamp=timezone.now(),
            app_config=config,
        )

        # Send via Meta API
        from meta_integration.utils import send_whatsapp_message
        try:
            result = send_whatsapp_message(
                to_phone_number=contact.whatsapp_id,
                message_type='text',
                data={'body': text},
                config=config,
            )
            wamid = result.get('messages', [{}])[0].get('id') if result else None
            msg.message_id = wamid
            msg.status = 'sent'
            msg.save(update_fields=['message_id', 'status'])
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            msg.status = 'failed'
            msg.error_message = str(e)
            msg.save(update_fields=['status', 'error_message'])

        # Broadcast new message to all subscribers of this conversation
        broadcast_message_to_websocket(msg)

        # Update contact's last_message_date for contacts list ordering
        contact.update_last_message(
            preview_text=text,
            timestamp=msg.timestamp,
        )
