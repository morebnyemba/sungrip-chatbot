# backend/notifications/management/commands/load_notification_templates.py

"""
Management command to seed / update Sungrip notification templates.

Usage:
    python manage.py load_notification_templates
"""

from django.core.management.base import BaseCommand
from notifications.models import NotificationTemplate


# ---------------------------------------------------------------------------
# Template definitions — Tailored for Sungrip Solar
# ---------------------------------------------------------------------------

SUNGRIP_TEMPLATES = [
    # ── Product orders ────────────────────────────────────────────────
    {
        "name": "sungrip_new_product_order",
        "description": "Notifies the Sales Team when a customer places a product order via WhatsApp.",
        "message_body": (
            "🛒 *New Product Order — Sungrip Solar*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🧾 *Order:* {{ order_number }}\n"
            "👤 *Customer:* {{ customer_name }}\n"
            "📱 *Phone:* {{ customer_phone }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 *Product:* {{ product_name }}\n"
            "🔢 *Qty:* {{ quantity }}\n"
            "💰 *Total:* {{ order_total_display }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚚 *Delivery:* {{ delivery_method }}\n"
            "📍 *Address:* {{ delivery_address }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏰ *Placed:* {{ timestamp }}\n\n"
            "Please follow up with the customer to arrange payment and delivery."
        ),
        "buttons": [],
        "body_parameters": {},
        "sync_status": "disabled",
    },
    {
        "name": "sungrip_new_product_enquiry",
        "description": "Notifies the Sales Team when a customer sends a product enquiry via WhatsApp.",
        "message_body": (
            "💬 *New Product Enquiry — Sungrip Solar*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🧾 *Ref:* {{ order_number }}\n"
            "👤 *Customer:* {{ customer_name }}\n"
            "📱 *Phone:* {{ customer_phone }}\n"
            "📦 *Product:* {{ product_name }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏰ *Received:* {{ timestamp }}\n\n"
            "The customer is interested in this product. "
            "Please reach out to provide more information and close the sale."
        ),
        "buttons": [],
        "body_parameters": {},
        "sync_status": "disabled",
    },

    # ── Quote requests ────────────────────────────────────────────────
    {
        "name": "sungrip_new_quote_request",
        "description": "Notifies staff when a customer submits a solar quote request.",
        "message_body": (
            "📋 *New Solar Quote Request — Sungrip Solar*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 *Customer:* {{ customer_name }}\n"
            "📱 *Phone:* {{ customer_phone }}\n"
            "💰 *Monthly Bill:* ${{ monthly_bill }}\n"
            "🏠 *Roof Type:* {{ roof_type }}\n"
            "🏘️ *Property:* {{ property_type }}\n"
            "📍 *Location:* {{ location }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏰ *Submitted:* {{ timestamp }}\n\n"
            "Please prepare a quote and contact the customer within 24 hours."
        ),
        "buttons": [],
        "body_parameters": {},
        "sync_status": "disabled",
    },

    # ── Installation scheduling ───────────────────────────────────────
    {
        "name": "sungrip_new_installation_request",
        "description": "Notifies the Installations Team when a customer schedules an installation.",
        "message_body": (
            "🔧 *New Installation Request — Sungrip Solar*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 *Customer:* {{ customer_name }}\n"
            "📱 *Phone:* {{ customer_phone }}\n"
            "📦 *Package:* {{ package_name }}\n"
            "📍 *Address:* {{ installation_address }}\n"
            "🗓️ *Preferred Date:* {{ preferred_date }}\n"
            "⏰ *Time Slot:* {{ time_slot }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Please confirm the installation slot and contact the customer."
        ),
        "buttons": [],
        "body_parameters": {},
        "sync_status": "disabled",
    },

    # ── Contact / support ─────────────────────────────────────────────
    {
        "name": "sungrip_human_handover_required",
        "description": "Notifies support staff when the chatbot escalates to a human agent.",
        "message_body": (
            "🤝 *Human Handover Required — Sungrip Solar*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 *Customer:* {{ customer_name }}\n"
            "📱 *WhatsApp:* {{ customer_whatsapp_id }}\n"
            "💬 *Last Message:* {{ last_bot_message }}\n"
            "🔄 *Flow:* {{ flow }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "The chatbot could not resolve this customer's request. "
            "Please take over the conversation."
        ),
        "buttons": [],
        "body_parameters": {},
        "sync_status": "disabled",
    },

    # ── Order status updates (customer-facing) ────────────────────────
    {
        "name": "sungrip_order_status_update",
        "description": "Notifies the customer when their order status changes (e.g. confirmed, shipped).",
        "message_body": (
            "📦 *Order Update — Sungrip Solar*\n\n"
            "Hi {{ customer_name }},\n\n"
            "Your order *{{ order_number }}* has been updated:\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Status:* {{ new_status }}\n"
            "📦 *Product:* {{ product_name }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "If you have any questions, reply to this message or "
            "call us at *0782 233 111*."
        ),
        "buttons": [],
        "body_parameters": {},
        "sync_status": "disabled",
    },

    # ── Package order (solar packages flow) ───────────────────────────
    {
        "name": "sungrip_new_package_order",
        "description": "Notifies the Sales Team when a customer orders a solar package.",
        "message_body": (
            "☀️ *New Solar Package Order — Sungrip Solar*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🧾 *Order:* {{ order_number }}\n"
            "👤 *Customer:* {{ customer_name }}\n"
            "📱 *Phone:* {{ customer_phone }}\n"
            "📦 *Package:* {{ package_name }}\n"
            "💰 *Amount:* {{ order_amount }}\n"
            "💳 *Payment Plan:* {{ payment_plan }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏰ *Placed:* {{ timestamp }}\n\n"
            "Please contact the customer to confirm the order and arrange payment."
        ),
        "buttons": [],
        "body_parameters": {},
        "sync_status": "disabled",
    },

    # ── Message send failure (technical) ──────────────────────────────
    {
        "name": "sungrip_message_send_failure",
        "description": "Notifies Technical Admin when a WhatsApp message fails to send.",
        "message_body": (
            "⚠️ *Message Send Failure — Sungrip Solar*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 *Contact:* {{ contact_name }}\n"
            "📱 *WhatsApp:* {{ contact_whatsapp_id }}\n"
            "❌ *Error:* {{ error_details }}\n"
            "⏰ *Time:* {{ error_time }}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Please check the message queue and WhatsApp API status."
        ),
        "buttons": [],
        "body_parameters": {},
        "sync_status": "disabled",
    },
]


class Command(BaseCommand):
    help = "Load or update Sungrip Solar notification templates"

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for tpl_data in SUNGRIP_TEMPLATES:
            obj, created = NotificationTemplate.objects.update_or_create(
                name=tpl_data['name'],
                defaults={
                    'description': tpl_data['description'],
                    'message_body': tpl_data['message_body'],
                    'buttons': tpl_data.get('buttons', []),
                    'body_parameters': tpl_data.get('body_parameters', {}),
                    'url_parameters': tpl_data.get('url_parameters', {}),
                    'sync_status': tpl_data.get('sync_status', 'disabled'),
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ Created: {obj.name}"))
            else:
                updated_count += 1
                self.stdout.write(f"  🔄 Updated: {obj.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone — {created_count} created, {updated_count} updated, "
                f"{len(SUNGRIP_TEMPLATES)} total templates."
            )
        )
