from django.contrib import admin
from .models import (
    PaymentPlan, QuoteRequest, Quote, QuoteItem, 
    Order, OrderItem, Installation, PaymentSchedule,
    ProductOrder,
)


# ── ProductOrder (catalog / WhatsApp quick orders) ─────────────────────
@admin.register(ProductOrder)
class ProductOrderAdmin(admin.ModelAdmin):
    """Admin interface for WhatsApp catalog product orders & enquiries."""

    list_display = [
        "order_number", "customer_name", "product_name",
        "quantity", "total_price", "currency",
        "status", "delivery_method", "created_at",
    ]
    list_filter = ["status", "delivery_method", "currency", "created_at"]
    search_fields = [
        "order_number", "customer_name", "customer_phone",
        "product_name", "product_sku",
    ]
    readonly_fields = [
        "order_number", "unit_price", "total_price",
        "created_at", "updated_at",
    ]
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        ("Order Info", {
            "fields": (
                "order_number", "status", "customer", "contact",
                "customer_name", "customer_phone",
            ),
        }),
        ("Product", {
            "fields": (
                "product", "product_name", "product_sku",
                "quantity", "unit_price", "total_price", "currency",
            ),
        }),
        ("Delivery", {
            "fields": ("delivery_method", "delivery_address"),
        }),
        ("Conversion to Full Order", {
            "fields": ("full_order",),
            "classes": ("collapse",),
        }),
        ("Notes", {
            "fields": ("customer_notes", "internal_notes"),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
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

