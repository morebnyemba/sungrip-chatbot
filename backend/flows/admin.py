"""
Admin configuration for flows app
"""
from django.contrib import admin
from .models import Flow, FlowStep, FlowTransition, FlowSession, WhatsAppFlow, WhatsAppFlowResponse


class FlowStepInline(admin.TabularInline):
    model = FlowStep
    extra = 1
    fields = ['name', 'step_type', 'is_entry_point']
    show_change_link = True


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    list_display = ['friendly_name', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'friendly_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [FlowStepInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'friendly_name', 'description', 'is_active')
        }),
        ('Triggers', {
            'fields': ('trigger_keywords', 'trigger_config')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class FlowTransitionInline(admin.TabularInline):
    model = FlowTransition
    fk_name = 'current_step'
    extra = 1
    fields = ['next_step', 'condition_config', 'priority']


@admin.register(FlowStep)
class FlowStepAdmin(admin.ModelAdmin):
    list_display = ['name', 'flow', 'step_type', 'is_entry_point', 'created_at']
    list_filter = ['step_type', 'is_entry_point', 'flow', 'created_at']
    search_fields = ['name', 'flow__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [FlowTransitionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('flow', 'name', 'step_type', 'is_entry_point')
        }),
        ('Configuration', {
            'fields': ('config',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FlowTransition)
class FlowTransitionAdmin(admin.ModelAdmin):
    list_display = ['current_step', 'next_step', 'priority']
    list_filter = ['current_step__flow', 'priority']
    search_fields = ['current_step__name', 'next_step__name']
    
    fieldsets = (
        ('Transition', {
            'fields': ('current_step', 'next_step', 'priority')
        }),
        ('Condition', {
            'fields': ('condition_config',)
        }),
    )


@admin.register(FlowSession)
class FlowSessionAdmin(admin.ModelAdmin):
    list_display = ['contact', 'flow', 'current_step', 'status', 'started_at']
    list_filter = ['status', 'flow', 'started_at']
    search_fields = ['contact__whatsapp_id', 'contact__name', 'flow__name']
    readonly_fields = ['started_at', 'updated_at', 'completed_at']
    date_hierarchy = 'started_at'
    
    fieldsets = (
        ('Session Information', {
            'fields': ('contact', 'flow', 'current_step', 'status')
        }),
        ('Context Data', {
            'fields': ('context_data',)
        }),
        ('Timestamps', {
            'fields': ('started_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


class WhatsAppFlowResponseInline(admin.TabularInline):
    model = WhatsAppFlowResponse
    extra = 0
    readonly_fields = ['contact', 'flow_token', 'is_processed', 'created_at']
    fields = ['contact', 'flow_token', 'is_processed', 'created_at']
    can_delete = False
    show_change_link = True


@admin.register(WhatsAppFlow)
class WhatsAppFlowAdmin(admin.ModelAdmin):
    list_display = ['friendly_name', 'name', 'sync_status', 'is_active', 'version', 'last_synced_at']
    list_filter = ['sync_status', 'is_active', 'meta_app_config', 'created_at']
    search_fields = ['name', 'friendly_name', 'description', 'flow_id']
    readonly_fields = ['flow_id', 'created_at', 'updated_at', 'last_synced_at']
    inlines = [WhatsAppFlowResponseInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'friendly_name', 'description', 'is_active')
        }),
        ('Meta Integration', {
            'fields': ('meta_app_config', 'flow_id', 'sync_status', 'sync_error')
        }),
        ('Flow Definition', {
            'fields': ('flow_json', 'version', 'flow_definition')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_synced_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.sync_status == 'published':
            # Make flow_json readonly if published to prevent accidental modifications
            return self.readonly_fields + ['flow_json']
        return self.readonly_fields


@admin.register(WhatsAppFlowResponse)
class WhatsAppFlowResponseAdmin(admin.ModelAdmin):
    list_display = ['whatsapp_flow', 'contact', 'is_processed', 'created_at', 'processed_at']
    list_filter = ['is_processed', 'whatsapp_flow', 'created_at']
    search_fields = ['contact__whatsapp_id', 'contact__name', 'flow_token', 'whatsapp_flow__name']
    readonly_fields = ['whatsapp_flow', 'contact', 'flow_token', 'response_data', 'created_at', 'processed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Response Information', {
            'fields': ('whatsapp_flow', 'contact', 'flow_token', 'is_processed')
        }),
        ('Response Data', {
            'fields': ('response_data',)
        }),
        ('Processing', {
            'fields': ('processing_notes', 'processed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
