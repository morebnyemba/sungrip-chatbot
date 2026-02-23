from django.contrib import admin
from django.contrib import messages

from .models import MessageTemplate


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'language', 'category', 'status', 'is_active', 'updated_at')
    list_filter = ('status', 'category', 'language', 'is_active')
    search_fields = ('name', 'body', 'template_id')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30

    fieldsets = (
        (None, {
            'fields': ('name', 'language', 'category', 'status', 'is_active'),
        }),
        ('Content', {
            'fields': ('header_type', 'header_content', 'body', 'footer', 'buttons'),
        }),
        ('Meta Sync', {
            'fields': ('template_id',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    actions = ['sync_templates_from_meta']

    @admin.action(description="\u2b07\ufe0f Sync all templates from Meta")
    def sync_templates_from_meta(self, request, queryset):
        """Import / update all WhatsApp message templates from Meta."""
        from meta_integration.template_service import MetaTemplateService

        try:
            svc = MetaTemplateService()
            stats = svc.import_templates()

            msg = (
                f"Meta template sync complete \u2014 "
                f"Created: {stats['created']}, Updated: {stats['updated']}, "
                f"Skipped: {stats['skipped']}"
            )
            if stats['errors']:
                msg += f", Errors: {len(stats['errors'])}"
                for err in stats['errors'][:5]:
                    self.message_user(request, f"\u26a0\ufe0f {err}", messages.WARNING)

            self.message_user(request, msg, messages.SUCCESS)

        except Exception as exc:
            self.message_user(
                request, f"\u274c Sync failed: {exc}", messages.ERROR
            )
