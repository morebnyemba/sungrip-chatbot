"""
Tests for the agents app
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from conversations.models import Contact
from .models import Agent, AgentClient, Bet, AgentEarning
from .services import register_client_with_agent, process_bet_outcome, settle_bet


class AgentModelTests(TestCase):
    """Tests for Agent model."""

    def test_agent_creation(self):
        agent = Agent.objects.create(
            name='Test Agent',
            phone_number='+263771234567',
            referral_code='AGENT01',
            commission_rate=Decimal('10.00'),
        )
        self.assertEqual(agent.name, 'Test Agent')
        self.assertEqual(agent.referral_code, 'AGENT01')
        self.assertTrue(agent.is_active)

    def test_agent_str(self):
        agent = Agent.objects.create(
            name='Test Agent',
            phone_number='+263771234567',
            referral_code='AGENT01',
        )
        self.assertEqual(str(agent), 'Test Agent (AGENT01)')

    def test_agent_auto_generates_referral_code(self):
        agent = Agent(name='Auto Code', phone_number='+263771234568')
        agent.save()
        self.assertTrue(len(agent.referral_code) > 0)

    def test_agent_total_earnings_empty(self):
        agent = Agent.objects.create(
            name='Test Agent',
            phone_number='+263771234567',
            referral_code='AGENT01',
        )
        self.assertEqual(agent.total_earnings, 0)

    def test_agent_client_count(self):
        agent = Agent.objects.create(
            name='Test Agent',
            phone_number='+263771234567',
            referral_code='AGENT01',
        )
        self.assertEqual(agent.client_count, 0)


class AgentClientModelTests(TestCase):
    """Tests for AgentClient model."""

    def setUp(self):
        self.agent = Agent.objects.create(
            name='Test Agent',
            phone_number='+263771234567',
            referral_code='AGENT01',
        )
        self.contact = Contact.objects.create(
            whatsapp_id='263771111111',
            phone_number='+263771111111',
            profile_name='Client One',
        )

    def test_agent_client_creation(self):
        client = AgentClient.objects.create(agent=self.agent, contact=self.contact)
        self.assertEqual(client.agent, self.agent)
        self.assertEqual(client.contact, self.contact)
        self.assertEqual(self.agent.client_count, 1)

    def test_agent_client_str(self):
        client = AgentClient.objects.create(agent=self.agent, contact=self.contact)
        self.assertIn('Agent', str(client))


class BetModelTests(TestCase):
    """Tests for Bet model."""

    def setUp(self):
        self.contact = Contact.objects.create(
            whatsapp_id='263772222222',
            phone_number='+263772222222',
            profile_name='Bettor',
        )

    def test_bet_creation(self):
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-001',
            amount=Decimal('50.00'),
            description='Match bet',
        )
        self.assertEqual(bet.status, 'pending')
        self.assertEqual(bet.amount, Decimal('50.00'))

    def test_bet_str(self):
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-002',
            amount=Decimal('100.00'),
        )
        self.assertIn('BET-002', str(bet))


class AgentEarningModelTests(TestCase):
    """Tests for AgentEarning model."""

    def setUp(self):
        self.agent = Agent.objects.create(
            name='Test Agent',
            phone_number='+263771234567',
            referral_code='AGENT01',
            commission_rate=Decimal('10.00'),
        )
        self.contact = Contact.objects.create(
            whatsapp_id='263773333333',
            phone_number='+263773333333',
            profile_name='Client',
        )
        self.bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-003',
            amount=Decimal('200.00'),
            status='lost',
        )

    def test_earning_creation(self):
        earning = AgentEarning.objects.create(
            agent=self.agent,
            bet=self.bet,
            amount=Decimal('20.00'),
            commission_rate_applied=Decimal('10.00'),
        )
        self.assertEqual(earning.amount, Decimal('20.00'))
        self.assertEqual(earning.status, 'pending')

    def test_agent_total_earnings_with_confirmed(self):
        AgentEarning.objects.create(
            agent=self.agent,
            bet=self.bet,
            amount=Decimal('20.00'),
            commission_rate_applied=Decimal('10.00'),
            status='confirmed',
        )
        self.assertEqual(self.agent.total_earnings, Decimal('20.00'))


class RegisterClientServiceTests(TestCase):
    """Tests for register_client_with_agent service."""

    def setUp(self):
        self.agent = Agent.objects.create(
            name='Agent A',
            phone_number='+263771234567',
            referral_code='ACODE1',
        )
        self.contact = Contact.objects.create(
            whatsapp_id='263774444444',
            phone_number='+263774444444',
            profile_name='New Client',
        )

    def test_register_with_valid_code(self):
        result = register_client_with_agent(self.contact, 'ACODE1')
        self.assertIsNotNone(result)
        self.assertEqual(result.agent, self.agent)
        self.assertEqual(result.contact, self.contact)

    def test_register_with_invalid_code(self):
        result = register_client_with_agent(self.contact, 'INVALID')
        self.assertIsNone(result)

    def test_register_with_inactive_agent(self):
        self.agent.is_active = False
        self.agent.save()
        result = register_client_with_agent(self.contact, 'ACODE1')
        self.assertIsNone(result)

    def test_register_idempotent(self):
        first = register_client_with_agent(self.contact, 'ACODE1')
        second = register_client_with_agent(self.contact, 'ACODE1')
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(AgentClient.objects.count(), 1)


class ProcessBetOutcomeServiceTests(TestCase):
    """Tests for process_bet_outcome service."""

    def setUp(self):
        self.agent = Agent.objects.create(
            name='Agent B',
            phone_number='+263771234568',
            referral_code='BCODE1',
            commission_rate=Decimal('15.00'),
        )
        self.contact = Contact.objects.create(
            whatsapp_id='263775555555',
            phone_number='+263775555555',
            profile_name='Bettor Client',
        )
        AgentClient.objects.create(agent=self.agent, contact=self.contact)

    def test_process_lost_bet_creates_earning(self):
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-010',
            amount=Decimal('100.00'),
            status='lost',
        )
        earning = process_bet_outcome(bet)
        self.assertIsNotNone(earning)
        self.assertEqual(earning.agent, self.agent)
        # 15% of 100 = 15
        self.assertEqual(earning.amount, Decimal('15.00'))
        self.assertEqual(earning.commission_rate_applied, Decimal('15.00'))

    def test_process_won_bet_no_earning(self):
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-011',
            amount=Decimal('100.00'),
            status='won',
        )
        result = process_bet_outcome(bet)
        self.assertIsNone(result)

    def test_process_bet_no_agent(self):
        unregistered_contact = Contact.objects.create(
            whatsapp_id='263776666666',
            phone_number='+263776666666',
            profile_name='No Agent',
        )
        bet = Bet.objects.create(
            contact=unregistered_contact,
            bet_reference='BET-012',
            amount=Decimal('100.00'),
            status='lost',
        )
        result = process_bet_outcome(bet)
        self.assertIsNone(result)

    def test_process_bet_idempotent(self):
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-013',
            amount=Decimal('100.00'),
            status='lost',
        )
        first = process_bet_outcome(bet)
        second = process_bet_outcome(bet)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(AgentEarning.objects.count(), 1)

    def test_process_bet_inactive_agent(self):
        self.agent.is_active = False
        self.agent.save()
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-014',
            amount=Decimal('100.00'),
            status='lost',
        )
        result = process_bet_outcome(bet)
        self.assertIsNone(result)


class SettleBetServiceTests(TestCase):
    """Tests for settle_bet service."""

    def setUp(self):
        self.agent = Agent.objects.create(
            name='Agent C',
            phone_number='+263771234569',
            referral_code='CCODE1',
            commission_rate=Decimal('20.00'),
        )
        self.contact = Contact.objects.create(
            whatsapp_id='263777777777',
            phone_number='+263777777777',
            profile_name='Settled Bettor',
        )
        AgentClient.objects.create(agent=self.agent, contact=self.contact)

    def test_settle_bet_lost(self):
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-020',
            amount=Decimal('200.00'),
        )
        updated = settle_bet(bet, 'lost')
        self.assertEqual(updated.status, 'lost')
        self.assertIsNotNone(updated.settled_at)
        # Agent should get 20% of 200 = 40
        earning = AgentEarning.objects.get(bet=bet)
        self.assertEqual(earning.amount, Decimal('40.00'))

    def test_settle_bet_won(self):
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-021',
            amount=Decimal('200.00'),
        )
        updated = settle_bet(bet, 'won')
        self.assertEqual(updated.status, 'won')
        self.assertFalse(AgentEarning.objects.filter(bet=bet).exists())

    def test_settle_bet_cancelled(self):
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-022',
            amount=Decimal('200.00'),
        )
        updated = settle_bet(bet, 'cancelled')
        self.assertEqual(updated.status, 'cancelled')
        self.assertFalse(AgentEarning.objects.filter(bet=bet).exists())

    def test_settle_already_settled_bet(self):
        bet = Bet.objects.create(
            contact=self.contact,
            bet_reference='BET-023',
            amount=Decimal('200.00'),
            status='won',
        )
        updated = settle_bet(bet, 'lost')
        # Should not change since it's already settled
        self.assertEqual(updated.status, 'won')
