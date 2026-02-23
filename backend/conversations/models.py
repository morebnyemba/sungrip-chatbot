"""
Conversation models for WhatsApp messaging
"""
from django.db import models
from customers.models import Customer


class Contact(models.Model):
    """WhatsApp contact"""
    
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, null=True, blank=True, related_name='whatsapp_contact')
    whatsapp_id = models.CharField(max_length=100, unique=True, help_text="WhatsApp phone number ID")
    phone_number = models.CharField(max_length=20)
    profile_name = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=200, blank=True, help_text="Display name (alias for profile_name)")
    
    # Status
    is_blocked = models.BooleanField(default=False)
    opt_in_status = models.BooleanField(default=True, help_text="Has opted in to receive messages")
    needs_human_intervention = models.BooleanField(
        default=False,
        help_text="When True, automated bot responses are paused for this contact"
    )
    
    # Message summary (updated by webhook processing)
    last_message_preview = models.CharField(max_length=255, blank=True, help_text="Preview of the last message")
    unread_count = models.IntegerField(default=0, help_text="Number of unread inbound messages")
    
    # Metadata
    first_message_date = models.DateTimeField(null=True, blank=True)
    last_message_date = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True, help_text="When the contact was last active")
    message_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_message_date']
        verbose_name = 'WhatsApp Contact'
        verbose_name_plural = 'WhatsApp Contacts'
    
    def __str__(self):
        return f"{self.profile_name or self.name or self.phone_number}"

    def save(self, *args, **kwargs):
        # Keep name and profile_name in sync
        if self.profile_name and not self.name:
            self.name = self.profile_name
        elif self.name and not self.profile_name:
            self.profile_name = self.name
        super().save(*args, **kwargs)

    def update_last_message(self, preview_text, timestamp=None):
        """Update contact summary fields after any message (inbound or outbound)."""
        from django.utils import timezone as tz
        self.last_message_date = timestamp or tz.now()
        self.last_message_preview = (preview_text or '')[:255]
        self.save(update_fields=['last_message_date', 'last_message_preview'])



class Conversation(models.Model):
    """WhatsApp conversation thread"""
    
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('pending', 'Pending Response'),
            ('resolved', 'Resolved'),
            ('archived', 'Archived'),
        ],
        default='active'
    )
    
    # Assignment
    assigned_to = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_conversations')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_message_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
    
    def __str__(self):
        return f"Conversation with {self.contact}"


class Message(models.Model):
    """WhatsApp message — aligned with morebnyemba/hanna's Message model."""
    
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('location', 'Location'),
        ('interactive', 'Interactive'),
        ('template', 'Template'),
    ]
    
    DIRECTION_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='messages')
    
    # Message identification
    # Nullable for outgoing messages before Meta API returns a WAMID (matches hanna's wamid)
    message_id = models.CharField(
        max_length=200, unique=True, null=True, blank=True,
        help_text="WhatsApp message ID (WAMID). Set from webhook for inbound, from API response for outbound."
    )
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES)
    
    # Content
    content = models.TextField(blank=True)
    content_payload = models.JSONField(
        null=True, blank=True,
        help_text="Full message payload. For inbound: raw webhook data. For outbound: API data dict."
    )
    media_url = models.URLField(blank=True)
    media_id = models.CharField(max_length=200, blank=True)
    media_mime_type = models.CharField(max_length=100, blank=True)
    caption = models.TextField(blank=True)
    
    # Location data (if message_type is 'location')
    location_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_name = models.CharField(max_length=200, blank=True)
    location_address = models.TextField(blank=True)
    
    # Interactive message data
    interactive_data = models.JSONField(null=True, blank=True)
    
    # Config (matches hanna's app_config FK)
    app_config = models.ForeignKey(
        'meta_integration.MetaAppConfig',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='messages',
        help_text="MetaAppConfig used for this message."
    )
    
    # Status (matches hanna's status choices)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending_dispatch', 'Pending Dispatch'),
            ('queued', 'Queued'),
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('read', 'Read'),
            ('failed', 'Failed'),
            ('received', 'Received'),
        ],
        default='queued'
    )
    status_timestamp = models.DateTimeField(
        null=True, blank=True,
        help_text="When status was last updated."
    )
    
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # Reply information (equivalent to hanna's related_incoming_message)
    replied_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    
    # Metadata
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
    
    def __str__(self):
        return f"{self.direction} {self.message_type} - {self.contact} ({self.timestamp})"


class MessageTemplate(models.Model):
    """WhatsApp message templates"""
    
    name = models.CharField(max_length=200, db_index=True)
    language = models.CharField(max_length=10, default='en')
    category = models.CharField(
        max_length=50,
        choices=[
            ('marketing', 'Marketing'),
            ('utility', 'Utility'),
            ('authentication', 'Authentication'),
        ]
    )
    
    # Template content
    header_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('image', 'Image'),
            ('video', 'Video'),
            ('document', 'Document'),
        ],
        blank=True
    )
    header_content = models.TextField(blank=True)
    
    body = models.TextField(help_text="Template body with placeholders like {{1}}, {{2}}")
    footer = models.TextField(blank=True)
    
    # Buttons
    buttons = models.JSONField(default=list, blank=True, help_text="List of button configurations")
    
    # Meta information
    template_id = models.CharField(max_length=200, blank=True, help_text="WhatsApp template ID")
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = [('name', 'language')]
        verbose_name = 'Message Template'
        verbose_name_plural = 'Message Templates'
    
    def __str__(self):
        return f"{self.name} ({self.language})"

