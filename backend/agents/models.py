"""
Agent system models for Sungrip

Replaces the referral concept with a full agent system where agents
earn commission when customers they referred lose bets.
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from conversations.models import Contact


class Agent(models.Model):
    """Agent who recruits customers using a unique referral code.

    Agents earn commission when customers registered under their code lose bets.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Optional link to a Django user account"
    )
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
    referral_code = models.CharField(
        max_length=50, unique=True, db_index=True,
        help_text="Unique code used by customers to register under this agent"
    )
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of lost bet amount awarded to agent"
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agent'
        verbose_name_plural = 'Agents'

    def __str__(self):
        return f"{self.name} ({self.referral_code})"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    @property
    def total_earnings(self):
        """Total confirmed earnings for this agent."""
        return self.earnings.filter(
            status='confirmed'
        ).aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def client_count(self):
        """Number of clients registered under this agent."""
        return self.clients.count()


class AgentClient(models.Model):
    """Tracks which contacts/customers registered under an agent's code."""

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='clients')
    contact = models.OneToOneField(
        Contact, on_delete=models.CASCADE, related_name='agent_registration',
        help_text="WhatsApp contact who registered with the agent's code"
    )
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-registered_at']
        verbose_name = 'Agent Client'
        verbose_name_plural = 'Agent Clients'

    def __str__(self):
        return f"{self.contact} → Agent {self.agent.name}"


class Bet(models.Model):
    """A bet placed by a customer/contact."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('cancelled', 'Cancelled'),
    ]

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='bets',
        help_text="WhatsApp contact who placed the bet"
    )
    bet_reference = models.CharField(
        max_length=100, unique=True,
        help_text="Unique reference for this bet"
    )
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Amount wagered"
    )
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True
    )

    # Metadata
    placed_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-placed_at']
        verbose_name = 'Bet'
        verbose_name_plural = 'Bets'

    def __str__(self):
        return f"Bet {self.bet_reference} - {self.contact} ({self.get_status_display()})"


class AgentEarning(models.Model):
    """Commission earned by an agent from a referred customer's lost bet."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='earnings')
    bet = models.OneToOneField(
        Bet, on_delete=models.CASCADE, related_name='agent_earning',
        help_text="The lost bet that generated this earning"
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Commission amount earned"
    )
    commission_rate_applied = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Commission rate that was applied at time of earning"
    )
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agent Earning'
        verbose_name_plural = 'Agent Earnings'

    def __str__(self):
        return f"{self.agent.name} earned {self.amount} {self.currency} from {self.bet.bet_reference}"
