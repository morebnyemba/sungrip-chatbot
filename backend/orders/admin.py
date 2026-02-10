from django.contrib import admin
from .models import (
    PaymentPlan, QuoteRequest, Quote, QuoteItem, 
    Order, OrderItem, Installation, PaymentSchedule
)


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    """Admin interface for QuoteRequest model"""
    list_display = ['request_id', 'customer_name', 'monthly_bill', 'roof_type', 'status', 'created_at']
    list_filter = ['status', 'roof_type', 'created_at']
    search_fields = ['request_id', 'customer_name', 'location', 'customer__full_name']
    readonly_fields = ['request_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_id', 'status', 'customer', 'contact')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'location')
        }),
        ('Quote Details', {
            'fields': ('monthly_bill', 'roof_type')
        }),
        ('Conversion', {
            'fields': ('quote', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

