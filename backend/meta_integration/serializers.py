"""
Serializers for meta_integration app.

Aligned with morebnyemba/hanna's meta_integration/serializers.py.
Provides DRF serializers for MetaAppConfig and WebhookEventLog management APIs.
"""
from rest_framework import serializers
from .models import MetaAppConfig, WebhookEventLog


class MetaAppConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaAppConfig
        fields = [
            'id',
            'name',
            'verify_token',
            'access_token',
            'app_secret',
            'phone_number_id',
            'waba_id',
            'catalog_id',
            'api_version',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'access_token': {
                'write_only': True,
                'required': False,
                'style': {'input_type': 'password'},
                'help_text': "Leave empty if not changing.",
            },
            'app_secret': {
                'write_only': True,
                'required': False,
                'style': {'input_type': 'password'},
                'help_text': "Leave empty if not changing. Used for webhook signature verification.",
            },
        }


class WebhookEventLogSerializer(serializers.ModelSerializer):
    """
    Full serializer for WebhookEventLog — includes the payload.
    """
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    app_config_name = serializers.CharField(source='app_config.name', read_only=True, allow_null=True)

    class Meta:
        model = WebhookEventLog
        fields = [
            'id',
            'event_identifier',
            'app_config',
            'app_config_name',
            'waba_id_received',
            'phone_number_id_received',
            'event_type',
            'event_type_display',
            'payload_object_type',
            'payload',
            'received_at',
            'processed_at',
            'processing_status',
            'processing_notes',
        ]
        read_only_fields = fields


class WebhookEventLogListSerializer(WebhookEventLogSerializer):
    """
    Concise serializer for listing WebhookEventLogs — excludes the large payload.
    """
    class Meta(WebhookEventLogSerializer.Meta):
        fields = [
            'id',
            'event_identifier',
            'app_config',
            'app_config_name',
            'waba_id_received',
            'phone_number_id_received',
            'event_type',
            'event_type_display',
            'payload_object_type',
            'received_at',
            'processed_at',
            'processing_status',
            'processing_notes',
        ]
