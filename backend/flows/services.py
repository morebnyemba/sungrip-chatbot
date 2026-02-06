"""
Flow processing services for flows app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Handles flow execution, step processing, and transition evaluation.
"""
import logging
from typing import Optional, Dict, Any
from django.utils import timezone

from .models import Flow, FlowStep, FlowTransition, FlowSession
from conversations.models import Contact, Message

logger = logging.getLogger(__name__)


class FlowProcessor:
    """
    Core flow processing engine.
    Executes flow steps, evaluates transitions, and manages flow sessions.
    """

    def __init__(self, session: FlowSession):
        """
        Initialize processor with a flow session.

        Args:
            session: FlowSession instance
        """
        self.session = session
        self.flow = session.flow
        self.contact = session.contact

    @classmethod
    def start_flow(cls, flow: Flow, contact: Contact) -> 'FlowProcessor':
        """
        Start a new flow session for a contact.

        Args:
            flow: Flow to start
            contact: Contact to start the flow for

        Returns:
            FlowProcessor: Initialized processor with new session
        """
        # Check for existing active session
        existing_session = FlowSession.objects.filter(
            contact=contact,
            status='active'
        ).first()

        if existing_session:
            logger.warning(f"Contact {contact.phone_number} already has an active flow session")
            # End the existing session
            existing_session.status = 'abandoned'
            existing_session.completed_at = timezone.now()
            existing_session.save()

        # Find entry point
        entry_step = flow.steps.filter(is_entry_point=True).first()
        if not entry_step:
            logger.error(f"Flow {flow.name} has no entry point")
            raise ValueError(f"Flow {flow.name} has no entry point")

        # Create new session
        session = FlowSession.objects.create(
            contact=contact,
            flow=flow,
            current_step=entry_step,
            status='active',
            context_data={}
        )

        logger.info(f"Started flow {flow.name} for contact {contact.phone_number}")

        # Create processor and execute entry step
        processor = cls(session)
        processor.execute_current_step()
        return processor

    def execute_current_step(self):
        """
        Execute the current step of the flow.
        """
        if not self.session.current_step:
            logger.warning(f"No current step for session {self.session.id}")
            return

        step = self.session.current_step
        logger.info(f"Executing step: {step.name} ({step.step_type})")

        # Execute based on step type
        if step.step_type == 'send_message':
            self._execute_send_message(step)
        elif step.step_type == 'question':
            self._execute_question(step)
        elif step.step_type == 'condition':
            self._execute_condition(step)
        elif step.step_type == 'action':
            self._execute_action(step)
        elif step.step_type == 'wait_for_reply':
            self._execute_wait_for_reply(step)
        elif step.step_type == 'end_flow':
            self._execute_end_flow(step)
        elif step.step_type == 'human_handover':
            self._execute_human_handover(step)
        elif step.step_type == 'switch_flow':
            self._execute_switch_flow(step)
        else:
            logger.warning(f"Unknown step type: {step.step_type}")

    def _execute_send_message(self, step: FlowStep):
        """
        Execute a send_message step.

        Config structure:
        {
            "message_type": "text",
            "text": {"body": "Hello!"}
        }
        """
        from meta_integration.utils import send_whatsapp_message

        message_config = step.config
        phone_number = self.contact.phone_number

        try:
            # Replace variables in message with context data
            message_config = self._replace_variables(message_config)

            # Send message
            result = send_whatsapp_message(phone_number, message_config)
            logger.info(f"Message sent in step {step.name}: {result}")

            # Move to next step automatically
            self._transition_to_next_step()
        except Exception as e:
            logger.error(f"Error sending message in step {step.name}: {str(e)}")
            self._handle_error(str(e))

    def _execute_question(self, step: FlowStep):
        """
        Execute a question step (sends message and waits for reply).

        Config structure:
        {
            "message_config": {
                "message_type": "text",
                "text": {"body": "What is your monthly bill?"}
            },
            "reply_config": {
                "expected_type": "number",
                "validation": {"min": 0, "max": 100000},
                "context_variable": "monthly_bill"
            }
        }
        """
        from meta_integration.utils import send_whatsapp_message

        message_config = step.config.get("message_config", {})
        phone_number = self.contact.phone_number

        try:
            # Replace variables
            message_config = self._replace_variables(message_config)

            # Send question
            result = send_whatsapp_message(phone_number, message_config)
            logger.info(f"Question sent in step {step.name}: {result}")

            # Wait for user reply (don't auto-transition)
            # Reply will be processed in process_user_reply()
        except Exception as e:
            logger.error(f"Error sending question in step {step.name}: {str(e)}")
            self._handle_error(str(e))

    def _execute_condition(self, step: FlowStep):
        """
        Execute a conditional branch step.

        Config structure:
        {
            "condition": "context_data.monthly_bill > 100"
        }
        """
        condition = step.config.get("condition", "")

        try:
            # Evaluate condition
            result = self._evaluate_condition(condition)
            logger.info(f"Condition {condition} evaluated to {result}")

            # Transition based on result
            self._transition_to_next_step(condition_result=result)
        except Exception as e:
            logger.error(f"Error evaluating condition in step {step.name}: {str(e)}")
            self._handle_error(str(e))

    def _execute_action(self, step: FlowStep):
        """
        Execute an action step (e.g., create order, send email).

        Config structure:
        {
            "action_type": "create_order",
            "parameters": {...}
        }
        """
        action_type = step.config.get("action_type")
        parameters = step.config.get("parameters", {})

        logger.info(f"Executing action: {action_type}")

        try:
            # Execute action based on type
            if action_type == "create_order":
                self._action_create_order(parameters)
            elif action_type == "send_email":
                self._action_send_email(parameters)
            elif action_type == "update_context":
                self._action_update_context(parameters)
            else:
                logger.warning(f"Unknown action type: {action_type}")

            # Move to next step
            self._transition_to_next_step()
        except Exception as e:
            logger.error(f"Error executing action in step {step.name}: {str(e)}")
            self._handle_error(str(e))

    def _execute_wait_for_reply(self, step: FlowStep):
        """
        Execute a wait_for_reply step (pauses flow until user responds).
        """
        logger.info(f"Waiting for user reply at step {step.name}")
        # Flow pauses here until process_user_reply() is called

    def _execute_end_flow(self, step: FlowStep):
        """
        Execute an end_flow step (completes the flow session).
        """
        logger.info(f"Ending flow {self.flow.name} for contact {self.contact.phone_number}")

        self.session.status = 'completed'
        self.session.completed_at = timezone.now()
        self.session.current_step = None
        self.session.save()

    def _execute_human_handover(self, step: FlowStep):
        """
        Execute a human_handover step (transfers to human agent).

        Config structure:
        {
            "message": "Connecting you to an agent...",
            "team": "sales"
        }
        """
        from meta_integration.utils import send_text_message

        message = step.config.get("message", "Connecting you to an agent...")

        try:
            # Send handover message
            send_text_message(self.contact.phone_number, message)

            # Mark session as requiring human intervention
            self.session.status = 'completed'
            self.session.completed_at = timezone.now()
            self.session.save()

            logger.info(f"Human handover initiated for contact {self.contact.phone_number}")
        except Exception as e:
            logger.error(f"Error in human handover: {str(e)}")
            self._handle_error(str(e))

    def _execute_switch_flow(self, step: FlowStep):
        """
        Execute a switch_flow step (switches to another flow).

        Config structure:
        {
            "target_flow": "installation_scheduling"
        }
        """
        target_flow_name = step.config.get("target_flow")

        try:
            target_flow = Flow.objects.get(name=target_flow_name, is_active=True)

            # End current session
            self.session.status = 'completed'
            self.session.completed_at = timezone.now()
            self.session.save()

            # Start new flow
            FlowProcessor.start_flow(target_flow, self.contact)
            logger.info(f"Switched to flow {target_flow_name}")
        except Flow.DoesNotExist:
            logger.error(f"Target flow {target_flow_name} not found")
            self._handle_error(f"Flow {target_flow_name} not found")

    def process_user_reply(self, reply_text: str):
        """
        Process a user reply within the current flow.

        Args:
            reply_text: User's message text
        """
        if not self.session.current_step:
            logger.warning(f"No current step for session {self.session.id}")
            return

        step = self.session.current_step

        # Handle based on step type
        if step.step_type == 'question':
            self._process_question_reply(step, reply_text)
        elif step.step_type == 'wait_for_reply':
            self._process_wait_reply(step, reply_text)
        else:
            logger.warning(f"Unexpected reply at step type {step.step_type}")

    def _process_question_reply(self, step: FlowStep, reply_text: str):
        """
        Process reply to a question step.
        """
        reply_config = step.config.get("reply_config", {})
        context_variable = reply_config.get("context_variable")
        expected_type = reply_config.get("expected_type", "text")

        # Validate and parse reply
        try:
            parsed_value = self._parse_reply(reply_text, expected_type, reply_config.get("validation", {}))

            # Store in context
            if context_variable:
                self.session.context_data[context_variable] = parsed_value
                self.session.save()
                logger.info(f"Stored {context_variable} = {parsed_value}")

            # Move to next step
            self._transition_to_next_step()
        except ValueError as e:
            # Invalid input, ask again or handle error
            logger.warning(f"Invalid reply: {str(e)}")
            from meta_integration.utils import send_text_message
            send_text_message(
                self.contact.phone_number,
                f"Invalid input: {str(e)}. Please try again."
            )

    def _process_wait_reply(self, step: FlowStep, reply_text: str):
        """
        Process reply during wait_for_reply step.
        """
        # Store reply in context
        self.session.context_data['last_reply'] = reply_text
        self.session.save()

        # Move to next step
        self._transition_to_next_step()

    def _transition_to_next_step(self, condition_result: Optional[bool] = None):
        """
        Transition to the next step based on transitions.

        Args:
            condition_result: Result of condition evaluation (for conditional steps)
        """
        current_step = self.session.current_step
        if not current_step:
            return

        # Get outgoing transitions ordered by priority
        transitions = current_step.outgoing_transitions.order_by('priority')

        # Find matching transition
        next_step = None
        for transition in transitions:
            if self._evaluate_transition(transition, condition_result):
                next_step = transition.next_step
                break

        if next_step:
            self.session.current_step = next_step
            self.session.save()
            logger.info(f"Transitioned to step: {next_step.name}")

            # Execute the next step
            self.execute_current_step()
        else:
            logger.warning(f"No valid transition found from step {current_step.name}")
            # End flow if no valid transition
            self._execute_end_flow(current_step)

    def _evaluate_transition(self, transition: FlowTransition, condition_result: Optional[bool]) -> bool:
        """
        Evaluate if a transition should be taken.

        Args:
            transition: FlowTransition to evaluate
            condition_result: Result of previous condition evaluation

        Returns:
            bool: True if transition should be taken
        """
        condition_config = transition.condition_config

        if not condition_config:
            # Auto transition
            return True

        condition_type = condition_config.get("type", "auto")

        if condition_type == "auto":
            return True
        elif condition_type == "condition_true" and condition_result is True:
            return True
        elif condition_type == "condition_false" and condition_result is False:
            return True
        elif condition_type == "user_reply_matches":
            # Check if user reply matches pattern
            # This would need the actual reply context
            return True
        else:
            return False

    def _replace_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace variables in config with context data.

        Variables format: {{variable_name}}
        """
        import json
        import re

        config_str = json.dumps(config)

        # Find all variables
        variables = re.findall(r'\{\{(\w+)\}\}', config_str)

        for var in variables:
            value = self.session.context_data.get(var, '')
            config_str = config_str.replace(f'{{{{{var}}}}}', str(value))

        return json.loads(config_str)

    def _parse_reply(self, reply_text: str, expected_type: str, validation: Dict[str, Any]):
        """
        Parse and validate user reply.

        Args:
            reply_text: User's reply
            expected_type: Expected type (text, number, email, etc.)
            validation: Validation rules

        Returns:
            Parsed value

        Raises:
            ValueError: If validation fails
        """
        if expected_type == "number":
            try:
                value = float(reply_text)
                if "min" in validation and value < validation["min"]:
                    raise ValueError(f"Value must be at least {validation['min']}")
                if "max" in validation and value > validation["max"]:
                    raise ValueError(f"Value must be at most {validation['max']}")
                return value
            except ValueError as e:
                if "Value must be" in str(e):
                    raise
                raise ValueError("Please enter a valid number")
        elif expected_type == "email":
            import re
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', reply_text):
                raise ValueError("Please enter a valid email address")
            return reply_text
        else:
            # Text type or other
            return reply_text

    def _evaluate_condition(self, condition: str) -> bool:
        """
        Evaluate a condition expression.

        Args:
            condition: Condition string (e.g., "context_data.monthly_bill > 100")

        Returns:
            bool: Evaluation result
        """
        # Simple condition evaluation
        # In production, use a safe expression evaluator
        try:
            # Replace context_data with actual data
            context_data = self.session.context_data
            # Evaluate safely (in production, use ast.literal_eval or similar)
            # For now, just log and return True
            logger.info(f"Condition evaluation: {condition} with context {context_data}")
            return True
        except Exception as e:
            logger.error(f"Error evaluating condition: {str(e)}")
            return False

    def _action_create_order(self, parameters: Dict[str, Any]):
        """Execute create_order action."""
        logger.info(f"Creating order with parameters: {parameters}")
        # Implementation would create an Order record

    def _action_send_email(self, parameters: Dict[str, Any]):
        """Execute send_email action."""
        logger.info(f"Sending email with parameters: {parameters}")
        # Implementation would send an email

    def _action_update_context(self, parameters: Dict[str, Any]):
        """Execute update_context action."""
        self.session.context_data.update(parameters)
        self.session.save()
        logger.info(f"Updated context with: {parameters}")

    def _handle_error(self, error_message: str):
        """
        Handle flow execution error.

        Args:
            error_message: Error description
        """
        logger.error(f"Flow error for session {self.session.id}: {error_message}")

        self.session.status = 'error'
        self.session.context_data['error'] = error_message
        self.session.save()

        # Optionally notify user
        try:
            from meta_integration.utils import send_text_message
            send_text_message(
                self.contact.phone_number,
                "Sorry, an error occurred. Please try again or contact support."
            )
        except:
            pass
