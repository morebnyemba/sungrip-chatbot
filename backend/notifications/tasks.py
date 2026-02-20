# backend/notifications/tasks.py

"""
Celery tasks for dispatching notifications via WhatsApp.
Ported from morebnyemba/hanna's notifications/tasks.py, adapted for Sungrip Solar.
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def dispatch_notification_task(self, notification_id: int):
    """
    Fetches a Notification and attempts to send it via WhatsApp
    to the recipient's linked phone number.

    The path to the recipient's WhatsApp number is:
        User → user.customer (Customer) → customer.whatsapp_contact (Contact)
    Falls back to Customer.whatsapp_number if the Contact doesn't exist.
    """
    from .models import Notification, NotificationTemplate
    from meta_integration.utils import send_whatsapp_message

    try:
        notification = Notification.objects.select_related('recipient').get(
            pk=notification_id
        )
    except Notification.DoesNotExist:
        logger.error(
            f"Notification {notification_id} not found. Aborting task."
        )
        return

    if notification.status != 'pending':
        logger.warning(
            f"Notification {notification_id} is '{notification.status}', "
            "not 'pending'. Skipping."
        )
        return

    recipient = notification.recipient

    # Resolve the recipient's WhatsApp number
    wa_number = _resolve_whatsapp_number(recipient)
    if not wa_number:
        error_msg = (
            f"User '{recipient.username}' has no linked WhatsApp number."
        )
        logger.warning(f"Cannot send notification {notification.id}: {error_msg}")
        notification.status = 'failed'
        notification.error_message = error_msg
        notification.save(update_fields=['status', 'error_message'])
        return

    # Send via Meta WhatsApp API
    try:
        if notification.template_name:
            # Try template message first
            try:
                template_obj = NotificationTemplate.objects.get(
                    name=notification.template_name
                )
            except NotificationTemplate.DoesNotExist:
                template_obj = None

            if template_obj and template_obj.body_parameters:
                # Send as Meta template message
                from .utils import render_template_string, get_versioned_template_name

                render_context = (notification.template_context or {}).copy()
                render_context['recipient'] = recipient

                body_params_list = []
                sorted_params = sorted(
                    template_obj.body_parameters.items(),
                    key=lambda item: int(item[0]),
                )
                for _idx, jinja_path in sorted_params:
                    try:
                        val = render_template_string(
                            f"{{{{ {jinja_path} }}}}", render_context
                        )
                        body_params_list.append({
                            "type": "text",
                            "text": str(val).strip() or "N/A",
                        })
                    except Exception as e:
                        logger.error(
                            f"Error rendering body param '{jinja_path}': {e}"
                        )
                        body_params_list.append({"type": "text", "text": "N/A"})

                components = []
                if body_params_list:
                    components.append({
                        "type": "BODY",
                        "parameters": body_params_list,
                    })

                versioned_name = get_versioned_template_name(
                    notification.template_name
                )
                result = send_whatsapp_message(
                    to_phone_number=wa_number,
                    message_type='template',
                    data={
                        "name": versioned_name,
                        "language": {"code": "en_US"},
                        "components": components,
                    },
                )
            else:
                # Send as plain text
                result = send_whatsapp_message(
                    to_phone_number=wa_number,
                    message_type='text',
                    data={'body': notification.content},
                )
        else:
            result = send_whatsapp_message(
                to_phone_number=wa_number,
                message_type='text',
                data={'body': notification.content},
            )

        if result and 'error' not in result:
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            notification.save(update_fields=['status', 'sent_at'])
            logger.info(
                f"Dispatched notification {notification.id} to "
                f"'{recipient.username}' at {wa_number}."
            )
        else:
            error_detail = result.get('error', 'Unknown error') if result else 'No API response'
            notification.status = 'failed'
            notification.error_message = str(error_detail)
            notification.save(update_fields=['status', 'error_message'])
            logger.error(
                f"Failed to dispatch notification {notification.id}: "
                f"{error_detail}"
            )

    except Exception as e:
        logger.error(
            f"Exception dispatching notification {notification.id}: {e}",
            exc_info=True,
        )
        notification.status = 'failed'
        notification.error_message = str(e)
        notification.save(update_fields=['status', 'error_message'])
        self.retry(exc=e)


def _resolve_whatsapp_number(user) -> str:
    """
    Resolve a User's WhatsApp number.

    Traversal path:
      1. User → Customer (via user FK) → Contact (via whatsapp_contact)
         → Contact.whatsapp_id
      2. User → Customer → Customer.whatsapp_number (fallback)
      3. User → Customer → Customer.phone_number (second fallback)

    Returns the WhatsApp number string, or empty string if not found.
    """
    try:
        customer = getattr(user, 'customer', None)
        if not customer:
            return ''

        # Preferred: linked Contact's WhatsApp ID
        contact = getattr(customer, 'whatsapp_contact', None)
        if contact and contact.whatsapp_id:
            return contact.whatsapp_id

        # Fallback: Customer's stored WhatsApp number
        if customer.whatsapp_number:
            return customer.whatsapp_number

        # Second fallback: Customer's phone number
        return customer.phone_number or ''

    except Exception:
        return ''
