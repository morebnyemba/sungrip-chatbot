"""
Serializers for the conversations app
"""
from rest_framework import serializers
from .models import Contact, Message, Conversation


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model - aligned with hanna"""
    direction = serializers.SerializerMethodField()
    text_content = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'message_id', 'direction', 'message_type',
            'content', 'text_content', 'content_preview',
            'media_url', 'caption', 'location_latitude', 'location_longitude',
            'location_name', 'location_address', 'interactive_data',
            'status', 'timestamp', 'created_at',
        ]
        read_only_fields = fields

    def get_direction(self, obj):
        # Normalise to 'in'/'out' as expected by frontend
        if obj.direction in ('inbound', 'in'):
            return 'in'
        return 'out'

    def get_text_content(self, obj):
        if obj.message_type == 'text':
            return obj.content
        if obj.content_payload:
            try:
                payload = obj.content_payload
                if isinstance(payload, dict):
                    text = payload.get('text', {})
                    if isinstance(text, dict):
                        return text.get('body', '')
                    return str(text) if text else ''
            except Exception:
                pass
        return obj.content or ''

    def get_content_preview(self, obj):
        if obj.message_type == 'image':
            return f"📷 {obj.caption or 'Photo'}"
        if obj.message_type == 'video':
            return f"🎥 {obj.caption or 'Video'}"
        if obj.message_type == 'audio':
            return '🎙 Voice message'
        if obj.message_type == 'document':
            return f"📄 {obj.caption or 'Document'}"
        if obj.message_type == 'location':
            return f"📍 {obj.location_name or 'Location'}"
        if obj.message_type == 'interactive':
            if obj.interactive_data:
                try:
                    d = obj.interactive_data
                    reply = d.get('button_reply') or d.get('list_reply')
                    if reply:
                        return reply.get('title', 'Interactive reply')
                except Exception:
                    pass
            return 'Interactive message'
        return obj.content or ''


class ContactSerializer(serializers.ModelSerializer):
    """Serializer for Contact with fields required by the frontend"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'id', 'whatsapp_id', 'phone_number', 'profile_name', 'name',
            'display_name', 'is_blocked', 'opt_in_status',
            'needs_human_intervention', 'last_message_preview',
            'unread_count', 'last_message_date', 'last_seen',
            'message_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'whatsapp_id', 'phone_number', 'last_message_date',
            'message_count', 'created_at', 'updated_at',
        ]

    def get_display_name(self, obj):
        return obj.name or obj.profile_name or obj.phone_number


class ContactListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the contact list panel"""
    name = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'id', 'whatsapp_id', 'phone_number', 'name',
            'needs_human_intervention', 'last_message_preview',
            'unread_count', 'last_seen', 'last_message_date',
        ]

    def get_name(self, obj):
        return obj.name or obj.profile_name or obj.phone_number
