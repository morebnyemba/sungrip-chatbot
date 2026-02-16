"""
Unit and integration tests for flows app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Tests cover flow execution, transitions, conditions, and context management.
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
import json

from .models import Flow, FlowStep, FlowTransition, ContactFlowState, WhatsAppFlow, WhatsAppFlowResponse
from conversations.models import Contact
from meta_integration.models import MetaAppConfig
from .services import process_message_for_flow
from . import schemas


# ============================================================================
# Model Tests
# ============================================================================

class FlowModelTests(TestCase):
    """Tests for Flow model."""

    def setUp(self):
        self.flow = Flow.objects.create(
            name='test_flow',
            friendly_name='Test Flow',
            description='A test flow',
            is_active=True,
            trigger_keywords=['hello', 'start']
        )

    def test_flow_creation(self):
        """Test creating a flow."""
        self.assertEqual(self.flow.name, 'test_flow')
        self.assertEqual(self.flow.friendly_name, 'Test Flow')
        self.assertTrue(self.flow.is_active)

    def test_flow_str(self):
        """Test flow string representation."""
        expected = 'Test Flow (Active)'
        self.assertEqual(str(self.flow), expected)

    def test_trigger_keywords_validation(self):
        """Test trigger keywords validation."""
        flow = Flow(name='test2', trigger_keywords='not_a_list')
        with self.assertRaises(Exception):
            flow.full_clean()

    def test_friendly_name_auto_generation(self):
        """Test automatic friendly name generation on save."""
        flow = Flow.objects.create(name='my_test_flow_2')
        self.assertEqual(flow.friendly_name, 'My Test Flow 2')


class FlowStepModelTests(TestCase):
    """Tests for FlowStep model."""

    def setUp(self):
        self.flow = Flow.objects.create(name='test_flow')
        self.step = FlowStep.objects.create(
            flow=self.flow,
            name='welcome',
            step_type='send_message',
            config={'message': 'Welcome!'},
            is_entry_point=True
        )

    def test_step_creation(self):
        """Test creating a flow step."""
        self.assertEqual(self.step.name, 'welcome')
        self.assertEqual(self.step.step_type, 'send_message')
        self.assertTrue(self.step.is_entry_point)

    def test_entry_point_uniqueness(self):
        """Test that only one entry point per flow is allowed."""
        with self.assertRaises(Exception):
            FlowStep.objects.create(
                flow=self.flow,
                name='welcome2',
                step_type='send_message',
                is_entry_point=True
            )

    def test_config_schema_validation(self):
        """Test that step config is validated."""
        step = FlowStep(
            flow=self.flow,
            name='question_step',
            step_type='question',
            config={
                'question_text': 'What is your name?',
                'input_type': 'text'
            }
        )
        step.full_clean()  # Should not raise
        self.assertEqual(step.config['question_text'], 'What is your name?')


class FlowTransitionModelTests(TestCase):
    """Tests for FlowTransition model."""

    def setUp(self):
        self.flow = Flow.objects.create(name='test_flow')
        self.step1 = FlowStep.objects.create(
            flow=self.flow,
            name='step1',
            step_type='send_message',
            is_entry_point=True
        )
        self.step2 = FlowStep.objects.create(
            flow=self.flow,
            name='step2',
            step_type='question'
        )

    def test_transition_creation(self):
        """Test creating a transition."""
        transition = FlowTransition.objects.create(
            current_step=self.step1,
            next_step=self.step2,
            condition_config={'type': 'auto'}
        )
        self.assertEqual(transition.current_step, self.step1)
        self.assertEqual(transition.next_step, self.step2)

    def test_transition_cross_flow_validation(self):
        """Test that transitions can't cross flows."""
        other_flow = Flow.objects.create(name='other_flow')
        other_step = FlowStep.objects.create(
            flow=other_flow,
            name='other_step',
            step_type='send_message'
        )

        transition = FlowTransition(
            current_step=self.step1,
            next_step=other_step
        )
        with self.assertRaises(Exception):
            transition.full_clean()


class ContactFlowStateModelTests(TestCase):
    """Tests for ContactFlowState model."""

    def setUp(self):
        self.contact = Contact.objects.create(
            phone_number='+1234567890',
            source='whatsapp'
        )
        self.flow = Flow.objects.create(name='test_flow')
        self.step = FlowStep.objects.create(
            flow=self.flow,
            name='step1',
            step_type='send_message',
            is_entry_point=True
        )

    def test_session_creation(self):
        """Test creating a flow session."""
        session = ContactFlowState.objects.create(
            contact=self.contact,
            flow=self.flow,
            current_step=self.step,
            status='active'
        )
        self.assertEqual(session.status, 'active')
        self.assertEqual(session.contact, self.contact)

    def test_context_data_validation(self):
        """Test that context data is validated."""
        session = ContactFlowState(
            contact=self.contact,
            flow=self.flow,
            context_data={'monthly_bill': 500, 'roof_type': 'tile'}
        )
        session.full_clean()  # Should validate
        self.assertEqual(session.context_data['monthly_bill'], 500)


# ============================================================================
# Schema Validation Tests
# ============================================================================

class SchemaValidationTests(TestCase):
    """Tests for Pydantic schema validation."""

    def test_send_message_config_validation(self):
        """Test send_message config validation."""
        config = {'message': 'Hello!'}
        validated = schemas.validate_step_config('send_message', config)
        self.assertEqual(validated['message'], 'Hello!')

    def test_question_config_validation(self):
        """Test question config validation."""
        config = {
            'question_text': 'What is your name?',
            'input_type': 'text'
        }
        validated = schemas.validate_step_config('question', config)
        self.assertEqual(validated['question_text'], 'What is your name?')

    def test_invalid_question_missing_options(self):
        """Test that options required for option-type questions."""
        config = {
            'question_text': 'Choose one',
            'input_type': 'options'
        }
        with self.assertRaises(Exception):
            schemas.validate_step_config('question', config)

    def test_condition_config_validation(self):
        """Test condition config validation."""
        config = {
            'type': 'user_reply_matches',
            'keywords': ['yes', 'ok'],
            'match_type': 'exact'
        }
        validated = schemas.validate_transition_config(config)
        self.assertEqual(validated['type'], 'user_reply_matches')

    def test_context_data_validation(self):
        """Test context data validation."""
        context = {'contact_phone': '+1234567890', 'monthly_bill': 500}
        validated = schemas.validate_context_data(context)
        self.assertEqual(validated['monthly_bill'], 500)


# ============================================================================
# Service/Processor Tests
# ============================================================================

# NOTE: FlowProcessor tests are commented out as we've migrated to function-based services
# These tests need to be refactored to test process_message_for_flow() function
# TODO: Rewrite these tests for the new function-based API

# class FlowProcessorTests(TransactionTestCase):
#     """Tests for FlowProcessor service."""
#
# #     def setUp(self):
#         self.contact = Contact.objects.create(
#             phone_number='+1234567890',
#             source='whatsapp'
#         )
#         self.flow = Flow.objects.create(
#             name='solar_quote',
#             is_active=True
#         )
# 
#         # Create steps
#         self.step1 = FlowStep.objects.create(
#             flow=self.flow,
#             name='welcome',
#             step_type='send_message',
#             config={'message': 'Welcome to Solar Quote!'},
#             is_entry_point=True
#         )
# 
#         self.step2 = FlowStep.objects.create(
#             flow=self.flow,
#             name='ask_roof_type',
#             step_type='question',
#             config={
#                 'question_text': 'What type of roof do you have?',
#                 'input_type': 'options',
#                 'options': ['tile', 'asphalt', 'metal']
#             }
#         )
# 
#         self.step3 = FlowStep.objects.create(
#             flow=self.flow,
#             name='ask_bill',
#             step_type='question',
#             config={
#                 'question_text': 'What is your monthly electricity bill?',
#                 'input_type': 'text'
#             }
#         )
# 
#         # Create transitions
#         FlowTransition.objects.create(
#             current_step=self.step1,
#             next_step=self.step2,
#             condition_config={'type': 'auto'}
#         )
# 
#         FlowTransition.objects.create(
#             current_step=self.step2,
#             next_step=self.step3,
#             condition_config={'type': 'auto'}
#         )
# 
#     def test_start_flow(self):
#         """Test starting a flow."""
#         processor = FlowProcessor.start_flow(self.contact, self.flow)
#         
#         self.assertIsNotNone(processor.session)
#         self.assertEqual(processor.session.contact, self.contact)
#         self.assertEqual(processor.session.flow, self.flow)
#         self.assertEqual(processor.session.current_step, self.step1)
#         self.assertEqual(processor.session.status, 'active')
# 
#     def test_condition_evaluation(self):
#         """Test condition evaluation with context data."""
#         session = ContactFlowState.objects.create(
#             contact=self.contact,
#             flow=self.flow,
#             current_step=self.step2,
#             context_data={'monthly_bill': 150}
#         )
#         processor = FlowProcessor(session)
# 
#         # Test simple comparison
#         result = processor._evaluate_condition('monthly_bill > 100')
#         self.assertTrue(result)
# 
#         # Test false condition
#         result = processor._evaluate_condition('monthly_bill < 100')
#         self.assertFalse(result)
# 
#     def test_variable_replacement(self):
#         """Test context variable replacement in configs."""
#         session = ContactFlowState.objects.create(
#             contact=self.contact,
#             flow=self.flow,
#             context_data={'user_name': 'John', 'roof_type': 'tile'}
#         )
#         processor = FlowProcessor(session)
# 
#         config = {
#             'message': 'Hello {{user_name}}, your roof type is {{roof_type}}'
#         }
#         result = processor._replace_variables(config)
#         self.assertEqual(
#             result['message'],
#             'Hello John, your roof type is tile'
#         )
# 
#     def test_user_reply_matching(self):
#         """Test user reply matching in transitions."""
#         session = ContactFlowState.objects.create(
#             contact=self.contact,
#             flow=self.flow,
#             current_step=self.step2,
#             context_data={'_last_user_reply': 'yes, please'}
#         )
#         processor = FlowProcessor(session)
# 
#         # Test keyword match
#         condition_config = {'pattern': r'yes|ok'}
#         result = processor._check_user_reply_matches(condition_config)
#         self.assertTrue(result)
# 
#         # Test non-match
#         condition_config = {'pattern': r'no|never'}
#         result = processor._check_user_reply_matches(condition_config)
#         self.assertFalse(result)


# ============================================================================
# API Tests
# ============================================================================

class FlowAPITests(APITestCase):
    """Tests for Flow REST API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.flow = Flow.objects.create(
            name='test_flow',
            friendly_name='Test Flow',
            is_active=True
        )

    def test_list_flows(self):
        """Test listing flows."""
        response = self.client.get('/api/flows/flows/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_flow(self):
        """Test retrieving a single flow."""
        response = self.client.get(f'/api/flows/flows/{self.flow.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test_flow')

    def test_activate_flow(self):
        """Test activating a flow."""
        self.flow.is_active = False
        self.flow.save()

        response = self.client.post(f'/api/flows/flows/{self.flow.id}/activate/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.flow.refresh_from_db()
        self.assertTrue(self.flow.is_active)

    def test_list_sessions(self):
        """Test listing flow sessions."""
        contact = Contact.objects.create(
            phone_number='+1234567890',
            source='whatsapp'
        )
        ContactFlowState.objects.create(
            contact=contact,
            flow=self.flow,
            status='active'
        )

        response = self.client.get('/api/flows/sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


# ============================================================================
# Integration Tests
# ============================================================================

# NOTE: FlowIntegrationTests are commented out as we've migrated to function-based services
# These tests need to be refactored to test process_message_for_flow() function
# TODO: Rewrite these tests for the new function-based API

    def setUp(self):
        self.contact = Contact.objects.create(
            phone_number='+1234567890',
            source='whatsapp'
        )
        
        # Create a simple 3-step flow
        self.flow = Flow.objects.create(
            name='simple_flow',
            is_active=True
        )

        self.step1 = FlowStep.objects.create(
            flow=self.flow,
            name='start',
            step_type='send_message',
            config={'message': 'Getting started'},
            is_entry_point=True
        )

        self.step2 = FlowStep.objects.create(
            flow=self.flow,
            name='ask_name',
            step_type='question',
            config={'question_text': 'What is your name?'}
        )

        self.step3 = FlowStep.objects.create(
            flow=self.flow,
            name='confirm',
            step_type='send_message',
            config={'message': 'Thanks {{user_name}}!'}
        )

        FlowTransition.objects.create(
            current_step=self.step1,
            next_step=self.step2,
            condition_config={'type': 'auto'}
        )

        FlowTransition.objects.create(
            current_step=self.step2,
            next_step=self.step3,
            condition_config={'type': 'auto'}
        )

    def test_complete_flow_execution(self):
        """Test executing a complete flow from start to end."""
        # Start the flow
        processor = FlowProcessor.start_flow(self.contact, self.flow)
        
        # Verify we're at step 1
        self.assertEqual(processor.session.current_step, self.step1)

        # Move to step 2
        processor.execute_current_step()
        # In real scenario, would call move_to_next_step() after user reply
        # processor.move_to_next_step()
        
        # Session should still be active
        processor.session.refresh_from_db()
        self.assertEqual(processor.session.status, 'active')


# ============================================================================
# Flow Action Tests
# ============================================================================

class FlowActionTests(TransactionTestCase):
    """Tests for flow actions."""

    def setUp(self):
        """Set up test data."""
        from customers.models import Customer
        
        self.customer = Customer.objects.create(
            phone_number='+1234567890',
            full_name='John Doe',
            email='john@example.com'
        )
        
        self.contact = Contact.objects.create(
            whatsapp_id='1234567890',
            phone_number='+1234567890',
            profile_name='John Doe',
            customer=self.customer
        )

    def test_save_quote_request_action(self):
        """Test save_quote_request flow action saves to database."""
        from .actions import save_quote_request
        from orders.models import QuoteRequest
        
        # Prepare context
        context = {
            'monthly_bill': 150.50,
            'roof_type': 'tile',
            'location': 'Harare, Zimbabwe'
        }
        
        # Call the action
        result_context = save_quote_request(
            contact=self.contact,
            context=context,
            params={'save_to_variable': 'quote_saved'}
        )
        
        # Check that context was updated
        self.assertIn('quote_saved', result_context)
        saved_data = result_context['quote_saved']
        
        # Verify success
        self.assertTrue(saved_data.get('success'))
        self.assertIn('id', saved_data)
        self.assertIn('request_id', saved_data)
        
        # Verify database record was created
        quote_request = QuoteRequest.objects.get(id=saved_data['id'])
        self.assertEqual(quote_request.customer, self.customer)
        self.assertEqual(quote_request.contact, self.contact)
        self.assertEqual(quote_request.customer_name, 'John Doe')
        self.assertEqual(float(quote_request.monthly_bill), 150.50)
        self.assertEqual(quote_request.roof_type, 'tile')
        self.assertEqual(quote_request.location, 'Harare, Zimbabwe')
        self.assertEqual(quote_request.status, 'pending')

    def test_save_quote_request_without_customer(self):
        """Test save_quote_request when contact has no linked customer."""
        from .actions import save_quote_request
        from orders.models import QuoteRequest
        
        # Create contact without customer
        contact_no_customer = Contact.objects.create(
            whatsapp_id='9876543210',
            phone_number='+9876543210',
            profile_name='Jane Smith'
        )
        
        context = {
            'monthly_bill': 200.00,
            'roof_type': 'metal',
            'location': 'Bulawayo'
        }
        
        # Call the action
        result_context = save_quote_request(
            contact=contact_no_customer,
            context=context,
            params={}
        )
        
        # Verify database record
        saved_data = result_context['quote_request_saved']
        quote_request = QuoteRequest.objects.get(id=saved_data['id'])
        
        self.assertIsNone(quote_request.customer)
        self.assertEqual(quote_request.contact, contact_no_customer)
        self.assertEqual(quote_request.customer_name, 'Jane Smith')

    def test_save_quote_request_error_handling(self):
        """Test save_quote_request handles errors gracefully."""
        from .actions import save_quote_request
        
        # Call with invalid data (contact without required attribute)
        context = {'monthly_bill': 'invalid'}  # Invalid type
        
        # The function should handle errors gracefully
        result_context = save_quote_request(
            contact=None,
            context=context,
            params={}
        )
        
        # Should return error status
        saved_data = result_context.get('quote_request_saved', {})
        # Even with errors, it should create the record or return error info
        self.assertIn('success', saved_data)

    def test_calculate_solar_quote_action(self):
        """Test calculate_solar_quote action."""
        from .actions import calculate_solar_quote
        
        context = {'monthly_bill': 120}
        
        result_context = calculate_solar_quote(
            contact=self.contact,
            context=context,
            params={'save_to_variable': 'solar_quote'}
        )
        
        # Check result
        self.assertIn('solar_quote', result_context)
        quote_data = result_context['solar_quote']
        
        self.assertTrue(quote_data.get('success'))
        self.assertEqual(quote_data['monthly_bill'], 120)
        self.assertIn('estimated_system_size_kw', quote_data)
        self.assertIn('estimated_cost', quote_data)
        self.assertIn('estimated_roi_months', quote_data)
