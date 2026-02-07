"""
Admin configuration for meta_integration app
"""
from django.contrib import admin
from .models import MetaAppConfig, WebhookEventLog


@admin.register(MetaAppConfig)
class MetaAppConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number_id', 'waba_id', 'api_version', 'is_active', 'created_at']
    list_filter = ['is_active', 'api_version', 'created_at']
    search_fields = ['name', 'phone_number_id', 'waba_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Meta/WhatsApp Credentials', {
            'fields': ('phone_number_id', 'waba_id', 'catalog_id', 'api_version')
        }),
        ('Authentication', {
            'fields': ('verify_token', 'access_token', 'app_secret'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Automatically handle active status"""
        super().save_model(request, obj, form, change)


@admin.register(WebhookEventLog)
class WebhookEventLogAdmin(admin.ModelAdmin):
    list_display = ['event_identifier', 'event_type', 'app_config', 'processing_status', 'received_at']
    list_filter = ['event_type', 'processing_status', 'received_at', 'app_config']
    search_fields = ['event_identifier', 'processing_notes', 'phone_number_id_received']
    readonly_fields = ['received_at', 'processed_at', 'payload']
    date_hierarchy = 'received_at'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('event_identifier', 'event_type', 'payload_object_type')
        }),
        ('Configuration', {
            'fields': ('app_config', 'waba_id_received', 'phone_number_id_received')
        }),
        ('Processing', {
            'fields': ('processing_status', 'processing_notes', 'received_at', 'processed_at')
        }),
        ('Payload', {
            'fields': ('payload',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Webhook logs are created automatically"""
        return False
