# backend/notifications/services.py

"""
Notification queuing service.
Ported from morebnyemba/hanna's notifications/services.py, simplified
and tailored for Sungrip Solar.

Entry point: queue_notifications_to_users()
"""

import logging
from typing import List, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from .models import Notification, NotificationTemplate
from .tasks import dispatch_notification_task
from .utils import render_template_string
from conversations.models import Contact
from flows.models import Flow

logger = logging.getLogger(__name__)
User = get_user_model()


def queue_notifications_to_users(
    template_name: str,
    template_context: Optional[dict] = None,
    user_ids: Optional[List[int]] = None,
    group_names: Optional[List[str]] = None,
    contact_ids: Optional[List[int]] = None,
    related_contact: Optional[Contact] = None,
    related_flow: Optional[Flow] = None,
):
    """
    Queues notifications for internal staff users and / or external contacts.

    For **internal users** (by *user_ids* or *group_names*),
    it creates a ``Notification`` record and dispatches a Celery task.

    For **external contacts** (by *contact_ids*),
    it sends a WhatsApp message directly.

    Args:
        template_name: Name of the ``NotificationTemplate``.
        template_context: Dict of variables for Jinja2 rendering.
        user_ids: Specific auth User PKs.
        group_names: Django Group names whose members should be notified.
        contact_ids: External WhatsApp Contact PKs.
        related_contact: Optional Contact to link to the notification.
        related_flow: Optional Flow to link to the notification.
    """
    if not template_name:
        logger.error("queue_notifications_to_users called without a 'template_name'.")
        return

    if not user_ids and not group_names and not contact_ids:
        logger.warning(
            "queue_notifications_to_users called without any target recipients "
            "(user_ids, group_names, or contact_ids)."
        )
        return

    # ------------------------------------------------------------------
    # Render the template
    # ------------------------------------------------------------------
    try:
        template = NotificationTemplate.objects.get(name=template_name)
    except NotificationTemplate.DoesNotExist:
        logger.error(
            f"Notification template '{template_name}' not found. "
            "Cannot queue notifications."
        )
        return

    render_context = (template_context or {}).copy()

    # Flatten common nested variables for Sungrip templates
    if related_contact:
        render_context['contact'] = str(related_contact)
        contact_display = related_contact.profile_name or related_contact.phone_number
        render_context.setdefault('contact_name', contact_display)
        render_context.setdefault('customer_whatsapp_id', related_contact.whatsapp_id)

    # Flatten order details
    if 'created_order_details' in render_context:
        od = render_context['created_order_details']
        if isinstance(od, dict):
            render_context.setdefault('order_number', od.get('order_number', ''))
            render_context.setdefault('order_amount', od.get('amount', '0.00'))
            render_context.setdefault('order_id', od.get('id', ''))

    # Flatten quote request details
    if 'quote_request_saved' in render_context:
        qr = render_context['quote_request_saved']
        if isinstance(qr, dict):
            for field in (
                'gadgets_to_power', 'roof_type',
                'property_type', 'location', 'customer_name', 'request_id',
            ):
                val = qr.get(field)
                if val is not None and val != '':
                    render_context.setdefault(field, val)

    # Provide safe defaults
    for key, default in {
        'customer_name': 'Customer',
        'contact_name': 'Contact',
        'order_number': 'N/A',
        'order_amount': '0.00',
        'product_name': 'N/A',
        'quantity': '1',
        'order_total_display': '$0.00',
        'delivery_method': 'not specified',
        'delivery_address': 'not specified',
        'delivery_name': 'N/A',
        'delivery_phone': 'N/A',
        'enquiry_reference': 'N/A',
        'recipient_name': 'User',
        'roof_type': 'not specified',
        'property_type': 'not specified',
        'location': 'not specified',
        'gadgets_to_power': 'not specified',
    }.items():
        render_context.setdefault(key, default)

    # Title-case delivery_method
    dm = render_context.get('delivery_method', '')
    if dm:
        render_context['delivery_method'] = str(dm).replace('_', ' ').title()

    if related_flow:
        render_context['flow'] = str(related_flow)

    final_message_body = render_template_string(template.message_body, render_context)

    if not final_message_body or not final_message_body.strip():
        logger.warning(
            f"Template '{template_name}' rendered to an empty body. Skipping."
        )
        return

    # ------------------------------------------------------------------
    # Case 1: Internal staff users
    # ------------------------------------------------------------------
    if user_ids or group_names:
        query = Q()
        if user_ids:
            query |= Q(id__in=user_ids)
        if group_names:
            query |= Q(groups__name__in=group_names)

        staff_users = User.objects.filter(query, is_active=True).distinct()

        if staff_users.exists():
            notifications_to_create = [
                Notification(
                    recipient=user,
                    channel='whatsapp',
                    status='pending',
                    content=final_message_body,
                    related_contact=related_contact,
                    related_flow=related_flow,
                    template_name=template_name,
                    template_context=render_context,
                )
                for user in staff_users
            ]
            created = Notification.objects.bulk_create(notifications_to_create)
            logger.info(
                f"Bulk created {len(created)} notifications for template "
                f"'{template_name}'."
            )

            for notif in created:
                transaction.on_commit(
                    lambda n=notif: dispatch_notification_task.delay(n.id)
                )
                logger.info(
                    f"Queued Notification ID {notif.id} for user "
                    f"'{notif.recipient.username}'."
                )
        else:
            logger.info(
                f"No active internal users found for user_ids={user_ids} "
                f"or group_names={group_names}."
            )

    # ------------------------------------------------------------------
    # Case 2: External contacts (direct WhatsApp)
    # ------------------------------------------------------------------
    if contact_ids:
        from meta_integration.utils import send_whatsapp_message

        recipient_contacts = Contact.objects.filter(id__in=contact_ids)
        for recipient_contact in recipient_contacts:
            try:
                send_whatsapp_message(
                    to_phone_number=recipient_contact.whatsapp_id,
                    message_type='text',
                    data={'body': final_message_body},
                )
                logger.info(
                    f"Sent direct WhatsApp notification for template "
                    f"'{template_name}' to contact {recipient_contact.id}."
                )
            except Exception as e:
                logger.error(
                    f"Failed to send notification to contact "
                    f"{recipient_contact.id}: {e}",
                    exc_info=True,
                )
