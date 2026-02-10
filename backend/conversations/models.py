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
    source = models.CharField(max_length=50, default='whatsapp', help_text="Channel source for this contact (e.g., whatsapp)")
    
    # Status
    is_blocked = models.BooleanField(default=False)
    opt_in_status = models.BooleanField(default=True, help_text="Has opted in to receive messages")
    
    # Metadata
    first_message_date = models.DateTimeField(null=True, blank=True)
    last_message_date = models.DateTimeField(null=True, blank=True)
    message_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_message_date']
        verbose_name = 'WhatsApp Contact'
        verbose_name_plural = 'WhatsApp Contacts'
    
    def __str__(self):
        return f"{self.profile_name or self.phone_number}"


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
    """WhatsApp message"""
    
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
    message_id = models.CharField(max_length=200, unique=True, help_text="WhatsApp message ID")
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES)
    
    # Content
    content = models.TextField(blank=True)
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
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('queued', 'Queued'),
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('read', 'Read'),
            ('failed', 'Failed'),
        ],
        default='queued'
    )
    
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # Reply information
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
    
    name = models.CharField(max_length=200, unique=True)
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
        verbose_name = 'Message Template'
        verbose_name_plural = 'Message Templates'
    
    def __str__(self):
        return f"{self.name} ({self.language})"
