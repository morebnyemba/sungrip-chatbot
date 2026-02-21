"""
API views for the conversations app
"""
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Contact, Message
from .serializers import ContactSerializer, ContactListSerializer, MessageSerializer


class ContactViewSet(viewsets.ModelViewSet):
    """
    API endpoint for WhatsApp contacts.
    Provides list, detail, and nested messages endpoint.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_blocked', 'needs_human_intervention']
    search_fields = ['name', 'profile_name', 'phone_number', 'whatsapp_id']
    ordering_fields = ['last_message_date', 'created_at', 'name']
    ordering = ['-last_message_date']

    def get_queryset(self):
        return Contact.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return ContactListSerializer
        return ContactSerializer

    @action(detail=True, methods=['get'], url_path='messages')
    def messages(self, request, pk=None):
        """Return the message history for a contact"""
        contact = self.get_object()
        msgs = (
            Message.objects
            .filter(contact=contact)
            .select_related('replied_to')
            .order_by('-timestamp')[:100]
        )
        serializer = MessageSerializer(msgs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='toggle-intervention')
    def toggle_intervention(self, request, pk=None):
        """Toggle the needs_human_intervention flag for a contact"""
        contact = self.get_object()
        contact.needs_human_intervention = not contact.needs_human_intervention
        contact.save(update_fields=['needs_human_intervention'])
        serializer = ContactSerializer(contact)
        return Response(serializer.data)

