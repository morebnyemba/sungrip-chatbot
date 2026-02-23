from django.contrib import admin
from django.contrib import messages as django_messages

from .models import Notification, NotificationTemplate


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'recipient',
        'template_name',
        'status',
        'channel',
        'created_at',
        'sent_at',
    )
    list_filter = ('status', 'channel', 'template_name')
    search_fields = ('recipient__username', 'content', 'template_name')
    readonly_fields = (
        'created_at',
        'sent_at',
        'recipient',
        'related_contact',
        'related_flow',
        'content',
        'error_message',
        'template_context',
    )
    list_per_page = 30
    list_select_related = ('recipient',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Recipient', {
            'fields': ('recipient', 'channel', 'status'),
        }),
        ('Content', {
            'fields': ('content', 'template_name', 'template_context'),
        }),
        ('Relations', {
            'fields': ('related_contact', 'related_flow'),
            'classes': ('collapse',),
        }),
        ('Status & Errors', {
            'fields': ('sent_at', 'error_message'),
        }),
        ('Metadata', {
            'fields': ('created_at',),
        }),
    )


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'sync_status', 'updated_at')
    list_filter = ('sync_status',)
    search_fields = ('name', 'message_body', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'message_body'),
        }),
        ('Buttons & Parameters', {
            'fields': ('buttons', 'body_parameters', 'url_parameters'),
            'classes': ('collapse',),
        }),
        ('Meta Sync', {
            'fields': ('meta_template_id', 'sync_status'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    actions = ['sync_templates_from_meta']

    @admin.action(description="\u2b07\ufe0f Sync notification templates from Meta")
    def sync_templates_from_meta(self, request, queryset):
        """Import / update notification templates from Meta WABA."""
        from meta_integration.template_service import MetaTemplateService

        try:
            svc = MetaTemplateService()
            stats = svc.sync_notification_templates()

            msg = (
                f"Meta notification template sync complete \u2014 "
                f"Created: {stats['created']}, Updated: {stats['updated']}, "
                f"Skipped: {stats['skipped']}"
            )
            if stats['errors']:
                msg += f", Errors: {len(stats['errors'])}"
                for err in stats['errors'][:5]:
                    self.message_user(request, f"\u26a0\ufe0f {err}", django_messages.WARNING)

            self.message_user(request, msg, django_messages.SUCCESS)

        except Exception as exc:
            self.message_user(
                request, f"\u274c Sync failed: {exc}", django_messages.ERROR
            )
