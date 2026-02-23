"""
API views for the conversations app
"""
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Contact, Message
from .serializers import ContactSerializer, ContactListSerializer, MessageSerializer


class DashboardStatsView(APIView):
    """Returns aggregate counts for the dashboard cards."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from orders.models import ProductOrder, InstallationRequest
        from .models import Conversation

        active_conversations = Conversation.objects.filter(status='active').count()
        total_contacts = Contact.objects.count()
        pending_orders = ProductOrder.objects.filter(status='pending').count()
        installation_requests = InstallationRequest.objects.filter(
            status__in=['pending', 'contacted', 'scheduled'],
        ).count()

        return Response({
            'active_conversations': active_conversations,
            'total_contacts': total_contacts,
            'pending_orders': pending_orders,
            'installation_requests': installation_requests,
        })


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
        """Return the message history for a contact with cursor pagination."""
        contact = self.get_object()
        qs = (
            Message.objects
            .filter(contact=contact)
            .select_related('replied_to')
            .order_by('-timestamp')
        )

        # Cursor-style pagination: ?before=<message_id>&limit=<N>
        before_id = request.query_params.get('before')
        limit = min(int(request.query_params.get('limit', 50)), 200)

        if before_id:
            try:
                cursor_msg = Message.objects.get(pk=before_id, contact=contact)
                qs = qs.filter(timestamp__lt=cursor_msg.timestamp)
            except Message.DoesNotExist:
                pass

        msgs = list(qs[:limit + 1])  # fetch one extra to check has_more
        has_more = len(msgs) > limit
        msgs = msgs[:limit]

        serializer = MessageSerializer(msgs, many=True)
        return Response({
            'results': serializer.data,
            'has_more': has_more,
        })

    @action(detail=True, methods=['post'], url_path='toggle-intervention')
    def toggle_intervention(self, request, pk=None):
        """Toggle the needs_human_intervention flag for a contact"""
        contact = self.get_object()
        contact.needs_human_intervention = not contact.needs_human_intervention
        contact.save(update_fields=['needs_human_intervention'])
        serializer = ContactSerializer(contact)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, pk=None):
        """Send a text message to a contact via the WhatsApp API (REST fallback)."""
        from django.utils import timezone
        from .models import Conversation

        contact = self.get_object()
        text = request.data.get('message', '').strip()
        if not text:
            return Response(
                {'error': 'Message text is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from meta_integration.services import WhatsAppService
        try:
            wa_service = WhatsAppService()
            result = wa_service.send_text_message(contact.whatsapp_id, text)
        except Exception as e:
            return Response(
                {'error': f'Failed to send message: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        now = timezone.now()

        # Get or create a conversation for this contact
        conversation, _ = Conversation.objects.get_or_create(
            contact=contact,
            status='active',
            defaults={'last_message_at': now},
        )

        wamid = result.get('messages', [{}])[0].get('id', '') or None

        # Persist the outgoing message locally
        msg = Message.objects.create(
            conversation=conversation,
            contact=contact,
            direction='outbound',
            message_type='text',
            content=text,
            status='sent',
            message_id=wamid,
            timestamp=now,
        )

        # Update conversation timestamp
        conversation.last_message_at = now
        conversation.save(update_fields=['last_message_at'])

        # Update contact summary fields
        contact.update_last_message(preview_text=text, timestamp=now)

        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

