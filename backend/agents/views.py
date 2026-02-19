"""
API views for the agents app
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Agent, AgentClient, Bet, AgentEarning
from .serializers import (
    AgentSerializer, AgentClientSerializer,
    BetSerializer, AgentEarningSerializer,
)
from .services import settle_bet


class AgentViewSet(viewsets.ModelViewSet):
    """API endpoint for agents"""

    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'phone_number', 'email', 'referral_code']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']


class AgentClientViewSet(viewsets.ModelViewSet):
    """API endpoint for agent-client registrations"""

    queryset = AgentClient.objects.select_related('agent', 'contact').all()
    serializer_class = AgentClientSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['agent']
    search_fields = ['contact__phone_number', 'contact__profile_name', 'agent__name']
    ordering_fields = ['registered_at']
    ordering = ['-registered_at']


class BetViewSet(viewsets.ModelViewSet):
    """API endpoint for bets"""

    queryset = Bet.objects.select_related('contact').all()
    serializer_class = BetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'contact', 'currency']
    search_fields = ['bet_reference', 'contact__phone_number', 'description']
    ordering_fields = ['placed_at', 'amount']
    ordering = ['-placed_at']

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        """Settle a bet with outcome: won, lost, or cancelled."""
        bet = self.get_object()
        outcome = request.data.get('outcome')
        if outcome not in ('won', 'lost', 'cancelled'):
            return Response(
                {'error': "outcome must be 'won', 'lost', or 'cancelled'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated_bet = settle_bet(bet, outcome)
        return Response(BetSerializer(updated_bet).data)


class AgentEarningViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for agent earnings (read-only)"""

    queryset = AgentEarning.objects.select_related('agent', 'bet').all()
    serializer_class = AgentEarningSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['agent', 'status', 'currency']
    search_fields = ['agent__name', 'bet__bet_reference']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
