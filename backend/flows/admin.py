"""
Admin configuration for flows app
"""
from django.contrib import admin
from .models import Flow, FlowStep, FlowTransition, FlowSession


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
