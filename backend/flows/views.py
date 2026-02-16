"""REST API views for flows app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Provides endpoints for managing flows, sessions, and WhatsApp flows.
"""

from rest_framework import viewsets, serializers, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging

from .models import Flow, FlowStep, FlowTransition, ContactFlowState, WhatsAppFlow, WhatsAppFlowResponse
from conversations.models import Contact

logger = logging.getLogger(__name__)


# ============================================================================
# Serializers
# ============================================================================

class FlowStepSerializer(serializers.ModelSerializer):
    """Serializer for FlowStep."""

    class Meta:
        model = FlowStep
        fields = [
            'id', 'flow', 'name', 'step_type', 'config', 
            'is_entry_point', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FlowTransitionSerializer(serializers.ModelSerializer):
    """Serializer for FlowTransition."""

    next_step_name = serializers.CharField(source='next_step.name', read_only=True)

    class Meta:
        model = FlowTransition
        fields = [
            'id', 'current_step', 'next_step', 'next_step_name',
            'condition_config', 'priority'
        ]
        read_only_fields = ['id']


class FlowSerializer(serializers.ModelSerializer):
    """Serializer for Flow."""

    steps = FlowStepSerializer(many=True, read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = Flow
        fields = [
            'id', 'name', 'friendly_name', 'description',
            'is_active', 'trigger_keywords', 'trigger_config',
            'steps', 'step_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_step_count(self, obj):
        return obj.steps.count()


class ContactFlowStateSerializer(serializers.ModelSerializer):
    """Serializer for ContactFlowState."""

    contact_phone = serializers.CharField(source='contact.phone_number', read_only=True)
    flow_name = serializers.CharField(source='flow.name', read_only=True)
    current_step_name = serializers.CharField(source='current_step.name', read_only=True)

    class Meta:
        model = ContactFlowState
        fields = [
            'id', 'contact', 'contact_phone', 'flow', 'flow_name',
            'current_step', 'current_step_name', 'context_data',
            'status', 'started_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'started_at', 'updated_at', 'completed_at',
            'contact_phone', 'flow_name', 'current_step_name'
        ]


class WhatsAppFlowSerializer(serializers.ModelSerializer):
    """Serializer for WhatsAppFlow."""

    app_config_name = serializers.CharField(
        source='meta_app_config.app_name', read_only=True
    )

    class Meta:
        model = WhatsAppFlow
        fields = [
            'id', 'name', 'friendly_name', 'description',
            'flow_id', 'flow_json', 'sync_status', 'sync_error',
            'version', 'is_active', 'meta_app_config', 'app_config_name',
            'flow_definition', 'created_at', 'updated_at', 'last_synced_at'
        ]
        read_only_fields = [
            'id', 'flow_id', 'sync_error', 'created_at',
            'updated_at', 'last_synced_at', 'app_config_name'
        ]


class WhatsAppFlowResponseSerializer(serializers.ModelSerializer):
    """Serializer for WhatsAppFlowResponse."""

    contact_phone = serializers.CharField(source='contact.phone_number', read_only=True)
    flow_name = serializers.CharField(source='whatsapp_flow.name', read_only=True)

    class Meta:
        model = WhatsAppFlowResponse
        fields = [
            'id', 'whatsapp_flow', 'flow_name', 'contact', 'contact_phone',
            'flow_token', 'response_data', 'is_processed', 'processing_notes',
            'created_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'processed_at',
            'flow_name', 'contact_phone'
        ]


# ============================================================================
# ViewSets
# ============================================================================

class FlowViewSet(viewsets.ModelViewSet):
    """ViewSet for managing flows."""

    queryset = Flow.objects.all()
    serializer_class = FlowSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'name']
    search_fields = ['name', 'friendly_name', 'description']
    ordering_fields = ['name', 'created_at', 'is_active']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a flow."""
        flow = self.get_object()
        flow.is_active = True
        flow.save()
        return Response({'status': 'Flow activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a flow."""
        flow = self.get_object()
        flow.is_active = False
        flow.save()
        return Response({'status': 'Flow deactivated'})

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get all sessions for a flow."""
        flow = self.get_object()
        sessions = flow.sessions.all().order_by('-started_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            sessions = sessions.filter(status=status_filter)

        serializer = ContactFlowStateSerializer(sessions, many=True)
        return Response(serializer.data)


class FlowStepViewSet(viewsets.ModelViewSet):
    """ViewSet for managing flow steps."""

    serializer_class = FlowStepSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['flow', 'step_type', 'is_entry_point']

    def get_queryset(self):
        return FlowStep.objects.all()

    @action(detail=True, methods=['get'])
    def transitions(self, request, pk=None):
        """Get outgoing transitions from this step."""
        step = self.get_object()
        transitions = step.outgoing_transitions.all().order_by('priority')
        serializer = FlowTransitionSerializer(transitions, many=True)
        return Response(serializer.data)


class FlowTransitionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing flow transitions."""

    queryset = FlowTransition.objects.all()
    serializer_class = FlowTransitionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['current_step', 'next_step']

    def perform_create(self, serializer):
        """Validate flow consistency on create."""
        # Additional validation if needed
        serializer.save()


class ContactFlowStateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing flow sessions."""

    serializer_class = ContactFlowStateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['contact', 'flow', 'status']
    ordering_fields = ['started_at', 'updated_at']
    ordering = ['-started_at']

    def get_queryset(self):
        return ContactFlowState.objects.prefetch_related('contact', 'flow', 'current_step')

    @action(detail=True, methods=['post'])
    def abandon(self, request, pk=None):
        """Abandon an active session."""
        session = self.get_object()
        
        if session.status == 'active':
            session.status = 'abandoned'
            session.completed_at = timezone.now()
            session.save()
            
            return Response({
                'status': 'Session abandoned',
                'session': ContactFlowStateSerializer(session).data
            })
        
        return Response(
            {'error': f'Cannot abandon session with status {session.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a session as completed."""
        session = self.get_object()
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()
        
        return Response({
            'status': 'Session completed',
            'session': ContactFlowStateSerializer(session).data
        })

    @action(detail=True, methods=['get'])
    def context(self, request, pk=None):
        """Get session context data."""
        session = self.get_object()
        return Response({
            'session_id': session.id,
            'context_data': session.context_data
        })


class WhatsAppFlowViewSet(viewsets.ModelViewSet):
    """ViewSet for managing WhatsApp flows."""

    queryset = WhatsAppFlow.objects.all()
    serializer_class = WhatsAppFlowSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sync_status', 'is_active', 'meta_app_config']
    search_fields = ['name', 'friendly_name', 'description']
    ordering_fields = ['name', 'created_at', 'sync_status']
    ordering = ['-updated_at']

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sync a WhatsApp flow with Meta API."""
        flow = self.get_object()
        
        try:
            from .whatsapp_flow_service import WhatsAppFlowService
            service = WhatsAppFlowService(flow.meta_app_config)
            
            action_type = request.data.get('action', 'validate')
            
            if action_type == 'validate':
                result = service.validate_flow(flow)
            elif action_type == 'publish':
                result = service.publish_flow(flow)
                if result['success']:
                    flow.sync_status = 'published'
                    flow.flow_id = result.get('flow_id')
                    flow.last_synced_at = timezone.now()
                    flow.save()
            elif action_type == 'update':
                result = service.update_flow(flow)
                if result['success']:
                    flow.last_synced_at = timezone.now()
                    flow.save()
            else:
                return Response(
                    {'error': f'Unknown action: {action_type}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if result['success']:
                return Response({
                    'status': f'Flow {action_type} successful',
                    'flow': WhatsAppFlowSerializer(flow).data,
                    'result': result
                })
            else:
                return Response(
                    {
                        'status': f'Flow {action_type} failed',
                        'error': result.get('error')
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.exception(f"Error syncing flow {pk}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WhatsAppFlowResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing WhatsApp flow responses."""

    queryset = WhatsAppFlowResponse.objects.all()
    serializer_class = WhatsAppFlowResponseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['whatsapp_flow', 'contact', 'is_processed']
    ordering_fields = ['created_at', 'processed_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def mark_processed(self, request, pk=None):
        """Mark a flow response as processed."""
        response = self.get_object()
        response.is_processed = True
        response.processed_at = timezone.now()
        response.processing_notes = request.data.get('notes', '')
        response.save()
        
        return Response({
            'status': 'Response marked as processed',
            'response': WhatsAppFlowResponseSerializer(response).data
        })
