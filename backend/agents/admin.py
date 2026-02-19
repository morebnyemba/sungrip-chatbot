"""
Admin configuration for agents app
"""
from django.contrib import admin
from .models import Agent, AgentClient, Bet, AgentEarning


class AgentClientInline(admin.TabularInline):
    model = AgentClient
    extra = 0
    readonly_fields = ['registered_at']


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'referral_code', 'phone_number', 'commission_rate', 'is_active', 'client_count', 'total_earnings', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'phone_number', 'email', 'referral_code']
    readonly_fields = ['created_at', 'updated_at', 'total_earnings', 'client_count']
    inlines = [AgentClientInline]

    fieldsets = (
        ('Agent Information', {
            'fields': ('user', 'name', 'phone_number', 'email')
        }),
        ('Referral Settings', {
            'fields': ('referral_code', 'commission_rate', 'is_active')
        }),
        ('Statistics', {
            'fields': ('total_earnings', 'client_count'),
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AgentClient)
class AgentClientAdmin(admin.ModelAdmin):
    list_display = ['contact', 'agent', 'registered_at']
    list_filter = ['agent', 'registered_at']
    search_fields = ['contact__phone_number', 'contact__profile_name', 'agent__name', 'agent__referral_code']
    readonly_fields = ['registered_at']


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ['bet_reference', 'contact', 'amount', 'currency', 'status', 'placed_at', 'settled_at']
    list_filter = ['status', 'currency', 'placed_at']
    search_fields = ['bet_reference', 'contact__phone_number', 'contact__profile_name', 'description']
    readonly_fields = ['placed_at']
    date_hierarchy = 'placed_at'


@admin.register(AgentEarning)
class AgentEarningAdmin(admin.ModelAdmin):
    list_display = ['agent', 'bet', 'amount', 'currency', 'commission_rate_applied', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['agent__name', 'agent__referral_code', 'bet__bet_reference']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
