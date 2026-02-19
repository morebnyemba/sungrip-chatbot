"""
Agent system business logic.

Core service for processing bet outcomes and awarding agents.
"""
import logging
from decimal import Decimal
from django.utils import timezone

from .models import Agent, AgentClient, Bet, AgentEarning

logger = logging.getLogger(__name__)


def register_client_with_agent(contact, referral_code):
    """Register a contact under an agent using the agent's referral code.

    Returns the AgentClient instance if successful, None otherwise.
    """
    try:
        agent = Agent.objects.get(referral_code=referral_code, is_active=True)
    except Agent.DoesNotExist:
        logger.warning("Registration failed: no active agent with code %s", referral_code)
        return None

    agent_client, created = AgentClient.objects.get_or_create(
        contact=contact,
        defaults={'agent': agent},
    )
    if created:
        logger.info("Contact %s registered under agent %s", contact, agent.name)
    else:
        logger.info("Contact %s already registered under agent %s", contact, agent_client.agent.name)
    return agent_client


def process_bet_outcome(bet):
    """Process a settled bet and award the agent if the bet was lost.

    Call this when a bet's status changes to 'lost'. If the contact who
    placed the bet is registered under an agent, an AgentEarning record
    is created.

    Returns the AgentEarning instance if created, None otherwise.
    """
    if bet.status != 'lost':
        return None

    try:
        agent_client = AgentClient.objects.select_related('agent').get(
            contact=bet.contact
        )
    except AgentClient.DoesNotExist:
        logger.debug("Bet %s: contact has no agent, skipping earning.", bet.bet_reference)
        return None

    agent = agent_client.agent
    if not agent.is_active:
        logger.info("Bet %s: agent %s is inactive, skipping earning.", bet.bet_reference, agent.name)
        return None

    # Check for existing earning (idempotency)
    if AgentEarning.objects.filter(bet=bet).exists():
        logger.info("Bet %s: earning already exists, skipping.", bet.bet_reference)
        return AgentEarning.objects.get(bet=bet)

    commission_amount = (bet.amount * agent.commission_rate) / Decimal('100')

    earning = AgentEarning.objects.create(
        agent=agent,
        bet=bet,
        amount=commission_amount,
        commission_rate_applied=agent.commission_rate,
        currency=bet.currency,
        status='pending',
    )

    logger.info(
        "Agent %s earned %s %s from bet %s (rate: %s%%)",
        agent.name, commission_amount, bet.currency,
        bet.bet_reference, agent.commission_rate,
    )
    return earning


def settle_bet(bet, outcome):
    """Settle a bet with the given outcome and process agent earnings.

    Args:
        bet: Bet instance to settle.
        outcome: One of 'won', 'lost', 'cancelled'.

    Returns:
        The updated Bet instance.
    """
    if bet.status != 'pending':
        logger.warning("Bet %s is already settled (%s).", bet.bet_reference, bet.status)
        return bet

    bet.status = outcome
    bet.settled_at = timezone.now()
    bet.save(update_fields=['status', 'settled_at'])

    if outcome == 'lost':
        process_bet_outcome(bet)

    return bet
