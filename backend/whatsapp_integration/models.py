"""
WhatsApp Business API integration models
"""
from django.db import models


class WhatsAppConfig(models.Model):
    """WhatsApp Business API configuration"""
    
    name = models.CharField(max_length=100, unique=True, default='default')
    
    # Meta/WhatsApp credentials
    phone_number_id = models.CharField(max_length=200)
    business_account_id = models.CharField(max_length=200)
    access_token = models.CharField(max_length=500)
    app_secret = models.CharField(max_length=200)
    verify_token = models.CharField(max_length=200)
    
    # API settings
    api_version = models.CharField(max_length=10, default='v18.0')
    webhook_url = models.URLField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'WhatsApp Configuration'
        verbose_name_plural = 'WhatsApp Configurations'
    
    def __str__(self):
        return f"WhatsApp Config: {self.name}"


class WebhookLog(models.Model):
    """Log of webhook events from WhatsApp"""
    
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Webhook Log'
        verbose_name_plural = 'Webhook Logs'
    
    def __str__(self):
        return f"{self.event_type} - {self.created_at}"

