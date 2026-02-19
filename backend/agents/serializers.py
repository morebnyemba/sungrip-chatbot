"""
Serializers for the agents app
"""
from rest_framework import serializers
from .models import Agent, AgentClient, Bet, AgentEarning


class AgentSerializer(serializers.ModelSerializer):
    """Serializer for Agent model"""

    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    client_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'phone_number', 'email', 'referral_code',
            'commission_rate', 'is_active', 'notes',
            'total_earnings', 'client_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class AgentClientSerializer(serializers.ModelSerializer):
    """Serializer for AgentClient model"""

    agent_name = serializers.CharField(source='agent.name', read_only=True)
    contact_name = serializers.CharField(source='contact.profile_name', read_only=True)

    class Meta:
        model = AgentClient
        fields = [
            'id', 'agent', 'agent_name', 'contact', 'contact_name',
            'registered_at',
        ]
        read_only_fields = ['registered_at']


class BetSerializer(serializers.ModelSerializer):
    """Serializer for Bet model"""

    contact_name = serializers.CharField(source='contact.profile_name', read_only=True)

    class Meta:
        model = Bet
        fields = [
            'id', 'contact', 'contact_name', 'bet_reference',
            'description', 'amount', 'currency', 'status',
            'placed_at', 'settled_at', 'notes',
        ]
        read_only_fields = ['placed_at', 'settled_at']


class AgentEarningSerializer(serializers.ModelSerializer):
    """Serializer for AgentEarning model"""

    agent_name = serializers.CharField(source='agent.name', read_only=True)
    bet_reference = serializers.CharField(source='bet.bet_reference', read_only=True)

    class Meta:
        model = AgentEarning
        fields = [
            'id', 'agent', 'agent_name', 'bet', 'bet_reference',
            'amount', 'commission_rate_applied', 'currency', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
