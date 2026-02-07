"""
Customer models for Sungrip Solar
"""
from django.db import models
from django.contrib.auth.models import User


class Customer(models.Model):
    """Customer profile for solar installation clients"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    
    # Address information
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Location for installation
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Customer classification
    customer_type = models.CharField(
        max_length=20,
        choices=[
            ('residential', 'Residential'),
            ('commercial', 'Commercial'),
            ('industrial', 'Industrial'),
        ],
        default='residential'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
    
    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"


class CustomerInteraction(models.Model):
    """Track all interactions with customers"""
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(
        max_length=20,
        choices=[
            ('inquiry', 'Inquiry'),
            ('quote_request', 'Quote Request'),
            ('follow_up', 'Follow Up'),
            ('support', 'Support'),
            ('complaint', 'Complaint'),
            ('payment', 'Payment'),
        ]
    )
    channel = models.CharField(
        max_length=20,
        choices=[
            ('whatsapp', 'WhatsApp'),
            ('phone', 'Phone Call'),
            ('email', 'Email'),
            ('in_person', 'In Person'),
        ],
        default='whatsapp'
    )
    summary = models.TextField()
    details = models.TextField(blank=True)
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer Interaction'
        verbose_name_plural = 'Customer Interactions'
    
    def __str__(self):
        return f"{self.customer.full_name} - {self.interaction_type} ({self.created_at.date()})"

