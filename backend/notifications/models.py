from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """
    Represents a notification to be sent to a system user (admin/agent).
    Ported from morebnyemba/hanna's notifications app, adapted for Sungrip Solar.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    channel = models.CharField(
        _("Channel"),
        max_length=20,
        default='whatsapp',
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
            ('read', 'Read'),
        ],
        default='pending',
        db_index=True,
    )
    content = models.TextField(_("Content"))

    related_contact = models.ForeignKey(
        'conversations.Contact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_notifications',
    )
    related_flow = models.ForeignKey(
        'flows.Flow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_notifications',
    )

    template_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="The name of the notification template used.",
    )
    template_context = models.JSONField(
        blank=True,
        null=True,
        help_text="The context data used to render the template variables.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Notification for {self.recipient.username} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("System Notification")
        verbose_name_plural = _("System Notifications")


class NotificationTemplate(models.Model):
    """
    Stores templates for system notifications.
    Ported from hanna — message_body supports Jinja2 variables like {{ order_number }}.
    """

    name = models.CharField(
        _("Template Name"),
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique identifier, e.g. 'sungrip_new_product_order'.",
    )
    description = models.TextField(_("Description"), blank=True, null=True)
    message_body = models.TextField(
        _("Message Body"),
        help_text="Template content. Supports Jinja2 variables like {{ order_number }}.",
    )
    buttons = models.JSONField(
        _("Quick Reply Buttons"),
        default=list,
        blank=True,
        help_text="Up to 3 text strings for quick-reply buttons.",
    )
    body_parameters = models.JSONField(
        _("Body Parameters Mapping"),
        default=dict,
        blank=True,
        help_text=(
            "Mapping of Meta body parameter index to Jinja2 variable path, "
            "e.g. {'1': 'order_number', '2': 'customer_name'}."
        ),
    )
    url_parameters = models.JSONField(
        _("URL Parameters Mapping"),
        default=dict,
        blank=True,
        help_text="Mapping of Meta URL parameter index to Jinja2 variable path.",
    )
    meta_template_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The ID of the template on Meta's systems (if synced).",
    )
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('synced', 'Synced'),
            ('pending', 'Pending Sync'),
            ('failed', 'Sync Failed'),
            ('disabled', 'Disabled'),
        ],
        default='pending',
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Notification Template")
        verbose_name_plural = _("Notification Templates")
