"""
Admin configuration for customers app
"""
from django.contrib import admin
from .models import Customer, CustomerInteraction


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone_number', 'customer_type', 'city', 'is_active', 'created_at']
    list_filter = ['customer_type', 'is_active', 'province', 'created_at']
    search_fields = ['full_name', 'phone_number', 'email', 'address_line1']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CustomerInteraction)
class CustomerInteractionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'interaction_type', 'channel', 'handled_by', 'created_at']
    list_filter = ['interaction_type', 'channel', 'created_at']
    search_fields = ['customer__full_name', 'summary']
    readonly_fields = ['created_at']
