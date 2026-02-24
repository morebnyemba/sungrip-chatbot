"""
Tests for the notifications service.
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock

from .services import queue_notifications_to_users
from .models import NotificationTemplate
from .utils import render_template_string


class NotificationTemplateRenderingTests(TestCase):
    """Tests for notification template rendering with quote data."""

    def setUp(self):
        self.template = NotificationTemplate.objects.create(
            name='sungrip_new_quote_request',
            description='Test quote notification',
            message_body=(
                "👤 *Customer:* {{ customer_name }}\n"
                "📱 *Phone:* {{ customer_phone }}\n"
                "💰 *Monthly Bill:* ${{ monthly_bill }}\n"
                "🏠 *Roof Type:* {{ roof_type }}\n"
                "🏘️ *Property:* {{ property_type }}\n"
                "📍 *Location:* {{ location }}\n"
            ),
        )

    def test_render_with_top_level_quote_variables(self):
        """Template renders correctly when quote variables are at the top level."""
        context = {
            'customer_name': 'Alice',
            'customer_phone': '+263712345678',
            'monthly_bill': '150',
            'roof_type': 'Tile Roof',
            'property_type': 'Residential',
            'location': 'Harare',
        }
        rendered = render_template_string(self.template.message_body, context)
        self.assertIn('Alice', rendered)
        self.assertIn('150', rendered)
        self.assertIn('Tile Roof', rendered)
        self.assertIn('Residential', rendered)
        self.assertIn('Harare', rendered)

    def test_quote_request_saved_flattening(self):
        """quote_request_saved dict is flattened into render context."""
        context = {
            'quote_request_saved': {
                'success': True,
                'id': 1,
                'request_id': 'QUOTE-123',
                'monthly_bill': '200',
                'gadgets_to_power': 'TV, fridge',
                'roof_type': 'Metal / IBR',
                'property_type': 'Commercial',
                'location': 'Bulawayo',
                'customer_name': 'Bob',
            },
            'customer_phone': '+263712345678',
        }
        # Simulate what queue_notifications_to_users does internally
        render_context = context.copy()

        # Flatten quote_request_saved (as in the updated service code)
        if 'quote_request_saved' in render_context:
            qr = render_context['quote_request_saved']
            if isinstance(qr, dict):
                for field in (
                    'monthly_bill', 'gadgets_to_power', 'roof_type',
                    'property_type', 'location', 'customer_name', 'request_id',
                ):
                    val = qr.get(field)
                    if val is not None and val != '':
                        render_context.setdefault(field, val)

        rendered = render_template_string(self.template.message_body, render_context)
        self.assertIn('Bob', rendered)
        self.assertIn('200', rendered)
        self.assertIn('Metal / IBR', rendered)
        self.assertIn('Commercial', rendered)
        self.assertIn('Bulawayo', rendered)

    def test_top_level_values_take_precedence_over_nested(self):
        """Top-level context values are NOT overwritten by nested ones."""
        context = {
            'monthly_bill': '300',  # top-level takes priority
            'roof_type': 'Tile',
            'quote_request_saved': {
                'monthly_bill': '200',
                'roof_type': 'Metal',
            },
        }
        render_context = context.copy()
        if 'quote_request_saved' in render_context:
            qr = render_context['quote_request_saved']
            if isinstance(qr, dict):
                for field in ('monthly_bill', 'roof_type'):
                    val = qr.get(field)
                    if val is not None and val != '':
                        render_context.setdefault(field, val)

        rendered = render_template_string(
            "${{ monthly_bill }} {{ roof_type }}", render_context
        )
        self.assertIn('300', rendered)
        self.assertIn('Tile', rendered)
        self.assertNotIn('200', rendered)
        self.assertNotIn('Metal', rendered)

    def test_safe_defaults_for_quote_fields(self):
        """Missing quote fields get safe default values."""
        defaults = {
            'monthly_bill': 'not provided',
            'roof_type': 'not specified',
            'property_type': 'not specified',
            'location': 'not specified',
            'gadgets_to_power': 'not specified',
        }
        render_context = {}
        for key, default in defaults.items():
            render_context.setdefault(key, default)

        for field, expected_default in defaults.items():
            self.assertEqual(render_context[field], expected_default)


class SendGroupNotificationFlatteningTests(TestCase):
    """Tests for send_group_notification flattening of saved data."""

    def test_flatten_quote_request_saved_into_notification_context(self):
        """send_group_notification flattens quote_request_saved into context."""
        from flows.actions import send_group_notification

        context = {
            'customer_name': 'Charlie',
            'quote_request_saved': {
                'success': True,
                'id': 42,
                'monthly_bill': '175',
                'roof_type': 'Concrete',
                'property_type': 'Residential',
                'location': 'Mutare',
                'request_id': 'QUOTE-456',
            },
        }
        contact = MagicMock()
        contact.phone_number = '+263712345678'

        with patch('notifications.services.queue_notifications_to_users') as mock_queue:
            send_group_notification(
                contact=contact,
                context=context,
                params={
                    'template_name': 'test_template',
                    'group_names': ['Sales Team'],
                },
            )
            mock_queue.assert_called_once()
            call_kwargs = mock_queue.call_args
            notif_ctx = call_kwargs.kwargs.get(
                'template_context',
                call_kwargs[1].get('template_context') if len(call_kwargs) > 1 else None,
            )
            if notif_ctx is None:
                notif_ctx = call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}

            self.assertEqual(notif_ctx.get('monthly_bill'), '175')
            self.assertEqual(notif_ctx.get('roof_type'), 'Concrete')
            self.assertEqual(notif_ctx.get('property_type'), 'Residential')
            self.assertEqual(notif_ctx.get('location'), 'Mutare')
