"""
Flow processing services for flows app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Handles flow execution, step processing, and transition evaluation.
"""
import logging
import re
import ast
import operator
from typing import Optional, Dict, Any
from django.utils import timezone
from django.db import transaction

from .models import Flow, FlowStep, FlowTransition, FlowSession
from conversations.models import Contact, Message

logger = logging.getLogger(__name__)

# Safe operators for condition evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: operator.and_,
    ast.Or: operator.or_,
    ast.Not: operator.not_,
    ast.In: lambda x, y: x in y,
    ast.NotIn: lambda x, y: x not in y,
}


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
        # Check for existing active session with row lock
        existing_session = FlowSession.objects.select_for_update().filter(
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
        from meta_integration.utils import send_whatsapp_message, send_typing_indicator

        message_config = step.config
        phone_number = self.contact.phone_number

        try:
            # Replace variables in message with context data
            message_config = self._replace_variables(message_config)

            # Send typing indicator for a more natural experience
            try:
                send_typing_indicator(phone_number)
            except Exception as e:
                # Don't fail the whole message if typing indicator fails
                logger.warning(f"Failed to send typing indicator: {str(e)}")

            # Send message (interactive messages pass config directly like other types)
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
        from meta_integration.utils import send_whatsapp_message, send_typing_indicator

        message_config = step.config.get("message_config", {})
        phone_number = self.contact.phone_number

        try:
            # Replace variables
            message_config = self._replace_variables(message_config)

            # Send typing indicator for a more natural experience
            try:
                send_typing_indicator(phone_number)
            except Exception as e:
                # Don't fail the whole message if typing indicator fails
                logger.warning(f"Failed to send typing indicator: {str(e)}")

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
            elif action_type == "check_whatsapp_flow":
                self._action_check_whatsapp_flow(parameters)
            elif action_type == "send_whatsapp_flow":
                self._action_send_whatsapp_flow(step, parameters)
            else:
                # Try the action registry for custom actions
                from .actions import flow_action_registry
                action_func = flow_action_registry.get(action_type)
                if action_func:
                    self.session.context_data = action_func(
                        self.contact, self.session.context_data, parameters
                    )
                    self.session.save()
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

    @transaction.atomic
    def process_user_reply(self, reply_text: str):
        """
        Process a user reply within the current flow.

        Args:
            reply_text: User's message text
        """
        # Reload session with lock to prevent race conditions
        self.session = FlowSession.objects.select_for_update().get(pk=self.session.pk)
        
        if not self.session.current_step:
            logger.warning(f"No current step for session {self.session.id}")
            return

        step = self.session.current_step
        
        # Store the last reply in context for transition evaluation
        self.session.context_data['_last_user_reply'] = reply_text
        self.session.save()

        # Handle based on step type
        if step.step_type == 'question':
            self._process_question_reply(step, reply_text)
        elif step.step_type == 'wait_for_reply':
            self._process_wait_reply(step, reply_text)
        else:
            logger.warning(f"Unexpected reply at step type {step.step_type}")

    def _process_question_reply(self, step: FlowStep, reply_text: str):
        """
        Process reply to a question step with configurable fallback handling.
        
        Following hanna pattern: supports re-prompt with max retries
        and configurable fallback messages.
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
                # Reset fallback counter on successful input
                fallback_key = f"_fallback_count_{step.name}"
                self.session.context_data.pop(fallback_key, None)
                self.session.save()
                logger.info(f"Stored {context_variable} = {parsed_value}")

            # Move to next step
            self._transition_to_next_step()
        except ValueError as e:
            # Invalid input - apply fallback/re-prompt handling
            from meta_integration.utils import send_text_message

            # Get fallback configuration from step config
            fallback_config = step.config.get("fallback_config", {})
            max_retries = fallback_config.get("max_retries", 3)
            fallback_message = fallback_config.get(
                "fallback_message",
                f"Invalid input: {str(e)}. Please try again."
            )

            # Track re-prompt count
            fallback_key = f"_fallback_count_{step.name}"
            current_count = self.session.context_data.get(fallback_key, 0)
            current_count += 1
            self.session.context_data[fallback_key] = current_count
            self.session.save()

            if current_count < max_retries:
                # Re-prompt the question
                logger.info(
                    f"Re-prompting question step '{step.name}' "
                    f"(attempt {current_count}/{max_retries}) for contact {self.contact.phone_number}"
                )
                send_text_message(self.contact.phone_number, fallback_message)
            else:
                # Max retries exceeded
                logger.warning(
                    f"Max retries ({max_retries}) exceeded for step '{step.name}' "
                    f"for contact {self.contact.phone_number}"
                )
                exceeded_message = fallback_config.get(
                    "max_retries_message",
                    "Too many invalid attempts. Please send 'menu' to start over."
                )
                send_text_message(self.contact.phone_number, exceeded_message)

                # End the flow session
                self.session.status = 'abandoned'
                self.session.completed_at = timezone.now()
                self.session.save()

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
        elif condition_type == "always_true":
            return True
        elif condition_type == "condition_true" and condition_result is True:
            return True
        elif condition_type == "condition_false" and condition_result is False:
            return True
        elif condition_type == "user_reply_matches":
            # Check if user reply matches pattern
            return self._check_user_reply_matches(condition_config)
        elif condition_type == "context_variable_equals":
            # Check if a context variable equals a specific value
            var_name = condition_config.get("variable")
            expected_value = condition_config.get("value")
            actual_value = self.session.context_data.get(var_name)
            return actual_value == expected_value
        elif condition_type == "variable_exists":
            var_name = condition_config.get("variable_name")
            return var_name is not None and var_name in self.session.context_data
        elif condition_type == "whatsapp_flow_response_received":
            return self.session.context_data.get("whatsapp_flow_response_received") is True
        elif condition_type == "interactive_reply_id_equals":
            expected_value = condition_config.get("value")
            last_reply = self.session.context_data.get("_last_user_reply", "")
            return last_reply == expected_value
        elif condition_type == "expression":
            expr = condition_config.get("expression")
            if expr:
                return self._evaluate_condition(expr)
            return False
        else:
            return False
    
    def _check_user_reply_matches(self, condition_config: Dict[str, Any]) -> bool:
        """
        Check if the last user reply matches the specified pattern.
        
        Args:
            condition_config: Condition configuration with pattern/keywords
            
        Returns:
            bool: True if reply matches
        """
        last_reply = self.session.context_data.get('_last_user_reply', '')
        if not last_reply:
            return False
        
        last_reply_lower = last_reply.lower().strip()
        
        # Check pattern match (regex)
        pattern = condition_config.get("pattern")
        if pattern:
            try:
                if re.search(pattern, last_reply, re.IGNORECASE):
                    return True
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
                return False
        
        # Check keyword match (exact or contains)
        keywords = condition_config.get("keywords", [])
        if keywords:
            match_type = condition_config.get("match_type", "contains")  # "exact" or "contains"
            if match_type == "exact":
                return last_reply_lower in [k.lower() for k in keywords]
            else:  # contains
                return any(k.lower() in last_reply_lower for k in keywords)
        
        return False

    def _replace_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace variables in config with context data.

        Variables format: {{variable_name}} or {{nested.key}}
        """
        import json

        config_str = json.dumps(config)

        # Find all variables (supports nested keys like {{user.name}})
        variables = re.findall(r'\{\{([\w\.]+)\}\}', config_str)

        for var in variables:
            # Support nested key access
            value = self._get_nested_value(var)
            
            # Escape special JSON characters in value
            if isinstance(value, str):
                # Escape quotes and backslashes for JSON safety
                value = value.replace('\\', '\\\\').replace('"', '\\"')
            
            config_str = config_str.replace(f'{{{{{var}}}}}', str(value))

        return json.loads(config_str)
    
    def _get_nested_value(self, key_path: str) -> Any:
        """
        Get a value from context data supporting nested keys.
        
        Args:
            key_path: Key path like "user.name" or "monthly_bill"
            
        Returns:
            Value from context or empty string if not found
        """
        keys = key_path.split('.')
        value = self.session.context_data
        
        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, '')
                else:
                    return ''
            return value if value is not None else ''
        except (KeyError, AttributeError, TypeError):
            return ''

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
        elif expected_type == "location":
            # Store location data as-is
            return reply_text
        elif expected_type == "interactive_id":
            # Store interactive button reply ID
            return reply_text
        else:
            # Text type or other
            return reply_text

    def _evaluate_condition(self, condition: str) -> bool:
        """
        Safely evaluate a condition expression using AST.

        Args:
            condition: Condition string (e.g., "monthly_bill > 100" or "monthly_bill > 100 and roof_type == 'tile'")

        Returns:
            bool: Evaluation result
            
        Supported operators:
            - Comparisons: ==, !=, <, <=, >, >=
            - Logical: and, or, not
            - Membership: in, not in
            - Arithmetic: +, -, *, /, %, **
        """
        try:
            # Parse condition to AST
            tree = ast.parse(condition, mode='eval')
            
            # Evaluate the AST safely
            result = self._eval_ast_node(tree.body)
            
            logger.info(f"Condition '{condition}' evaluated to {result}")
            return bool(result)
            
        except SyntaxError as e:
            logger.error(f"Invalid condition syntax '{condition}': {e}")
            return False
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {str(e)}")
            return False
    
    def _eval_ast_node(self, node):
        """
        Safely evaluate an AST node.
        
        This implementation only allows safe operations and prevents code execution.
        """
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Fallback for older Python
            return node.n
        elif isinstance(node, ast.Str):  # Fallback for older Python
            return node.s
        elif isinstance(node, ast.Name):
            # Look up variable in context data
            return self.session.context_data.get(node.id, None)
        elif isinstance(node, ast.BinOp):
            # Binary operation (e.g., +, -, *, /)
            left = self._eval_ast_node(node.left)
            right = self._eval_ast_node(node.right)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](left, right)
            else:
                raise ValueError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            # Unary operation (e.g., not, -)
            operand = self._eval_ast_node(node.operand)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](operand)
            else:
                raise ValueError(f"Unsupported unary operator: {op_type}")
        elif isinstance(node, ast.Compare):
            # Comparison (e.g., <, >, ==)
            left = self._eval_ast_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_ast_node(comparator)
                op_type = type(op)
                if op_type in SAFE_OPERATORS:
                    result = SAFE_OPERATORS[op_type](left, right)
                    if not result:
                        return False
                    left = right  # Chain comparisons
                else:
                    raise ValueError(f"Unsupported comparison operator: {op_type}")
            return True
        elif isinstance(node, ast.BoolOp):
            # Boolean operation (and, or)
            op_type = type(node.op)
            if op_type == ast.And:
                return all(self._eval_ast_node(val) for val in node.values)
            elif op_type == ast.Or:
                return any(self._eval_ast_node(val) for val in node.values)
            else:
                raise ValueError(f"Unsupported boolean operator: {op_type}")
        elif isinstance(node, ast.List):
            # List literal
            return [self._eval_ast_node(elt) for elt in node.elts]
        elif isinstance(node, ast.Tuple):
            # Tuple literal
            return tuple(self._eval_ast_node(elt) for elt in node.elts)
        else:
            raise ValueError(f"Unsupported AST node type: {type(node)}")

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

    def _action_check_whatsapp_flow(self, parameters: Dict[str, Any]):
        """
        Check if a published WhatsApp interactive flow exists.
        Sets a context variable with flow data if found.
        """
        from .actions import check_whatsapp_flow
        self.session.context_data = check_whatsapp_flow(
            self.contact, self.session.context_data, parameters
        )
        self.session.save()

    def _action_send_whatsapp_flow(self, step: FlowStep, parameters: Dict[str, Any]):
        """
        Send a WhatsApp interactive flow message to the user.
        Uses flow data from context to construct the interactive flow message.
        """
        from meta_integration.utils import send_whatsapp_message, send_typing_indicator

        flow_data_var = parameters.get('flow_data_variable', 'wa_flow_data')
        flow_data = self.session.context_data.get(flow_data_var, {})
        flow_id = flow_data.get('flow_id')

        if not flow_id:
            logger.error(f"No flow_id in context variable '{flow_data_var}'")
            return

        phone_number = self.contact.phone_number
        cta_text = parameters.get('cta_text', 'Start Form')
        body_text = parameters.get('body_text', 'Please complete the form below.')
        screen = parameters.get('initial_screen', 'WELCOME')

        try:
            send_typing_indicator(phone_number)
        except Exception as e:
            logger.warning(f"Failed to send typing indicator: {str(e)}")

        message_config = {
            "message_type": "interactive",
            "interactive": {
                "type": "flow",
                "body": {"text": body_text},
                "action": {
                    "name": "flow",
                    "parameters": {
                        "flow_message_version": "3",
                        "flow_token": f"{self.contact.id}-{flow_data.get('name', 'flow')}-{timezone.now().timestamp()}",
                        "flow_id": flow_id,
                        "flow_cta": cta_text,
                        "flow_action": "navigate",
                        "flow_action_payload": {"screen": screen}
                    }
                }
            }
        }

        try:
            result = send_whatsapp_message(phone_number, message_config)
            logger.info(f"WhatsApp flow message sent in step {step.name}: {result}")
        except Exception as e:
            logger.error(f"Error sending WhatsApp flow message: {str(e)}")

    def _handle_error(self, error_message: str):
        """
        Handle flow execution error with detailed logging.

        Following hanna pattern: includes contact ID and step info in logs.

        Args:
            error_message: Error description
        """
        step_name = self.session.current_step.name if self.session.current_step else 'Unknown'
        logger.error(
            f"Flow error for session {self.session.id}, "
            f"contact {self.contact.id} ({self.contact.phone_number}), "
            f"flow '{self.flow.name}', step '{step_name}': {error_message}",
            exc_info=True
        )

        self.session.status = 'error'
        self.session.context_data['error'] = error_message
        self.session.completed_at = timezone.now()
        self.session.save()

        # Notify user of error
        try:
            from meta_integration.utils import send_text_message
            send_text_message(
                self.contact.phone_number,
                "Sorry, an error occurred. Please send 'menu' to start over or contact support."
            )
        except Exception:
            logger.exception("Failed to send error notification to contact %s", self.contact.id)
