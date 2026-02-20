# backend/notifications/handlers.py

"""
Django signal handlers that queue system notifications.
Ported from morebnyemba/hanna's notifications/handlers.py, adapted for Sungrip.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(post_save, sender='orders.ProductOrder')
def notify_on_new_product_order(sender, instance, created, **kwargs):
    """
    When a new ProductOrder is created, queue a notification to the
    Sales Team so they can follow up promptly.
    """
    if not created:
        return

    # Only notify for real orders (not enquiries which have customer_notes starting with 'Enquiry')
    is_enquiry = (instance.customer_notes or '').startswith('Enquiry')

    from .services import queue_notifications_to_users

    try:
        template_name = (
            'sungrip_new_product_enquiry'
            if is_enquiry
            else 'sungrip_new_product_order'
        )
        contact = getattr(instance, 'contact', None)

        queue_notifications_to_users(
            template_name=template_name,
            group_names=['Sales Team'],
            related_contact=contact,
            template_context={
                'order_number': instance.order_number or 'N/A',
                'customer_name': instance.customer_name or 'Unknown',
                'customer_phone': instance.customer_phone or 'N/A',
                'product_name': instance.product_name or 'N/A',
                'product_sku': instance.product_sku or '',
                'quantity': str(instance.quantity),
                'order_total_display': f"${instance.total_price:,.2f}" if instance.total_price else '$0.00',
                'delivery_method': instance.delivery_method or 'not_specified',
                'delivery_address': instance.delivery_address or 'N/A',
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M'),
            },
        )
        logger.info(
            f"Queued '{template_name}' notification for order "
            f"{instance.order_number}"
        )
    except Exception as e:
        logger.error(
            f"Failed to queue notification for order "
            f"{instance.order_number}: {e}",
            exc_info=True,
        )
