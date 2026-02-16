# backend/flows/services.py
"""
Flow processing services for flows app.

Adopts Hanna's proven function-based architecture with sophisticated features:
- Fall-through processing for automatic step progression
- Action registry system for extensible custom actions
- Rich condition types and Jinja2 template support
- Comprehensive fallback retry system
- WhatsApp Flow (NFM) integration support
- Performance optimizations with prefetch_related

Following conventions from morebnyemba/hanna (production-proven implementation).
"""
import logging
import re
import json
from typing import List, Dict, Any, Optional, Union, Literal
from django.utils import timezone
from django.db import transaction, models
from django.apps import apps
from django.db.models.fields.files import ImageFieldFile, FileField
from jinja2 import Environment, select_autoescape, Undefined
from pydantic import ValidationError
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from conversations.models import Contact, Message
from .models import Flow, FlowStep, FlowTransition, ContactFlowState
from .schemas import (
    StepConfigSendMessage, StepConfigQuestion, StepConfigAction,
    StepConfigSwitchFlow, StepConfigEndFlow, StepConfigHumanHandover,
    FallbackConfig, InteractiveMessagePayload
)
from .actions import flow_action_registry

logger = logging.getLogger(__name__)

# --- Jinja2 Environment Setup ---
class SilentUndefined(Undefined):
    """Jinja2 undefined handler that returns empty string instead of raising."""
    def _fail_with_undefined_error(self, *args, **kwargs):
        return ''

jinja_env = Environment(
    autoescape=select_autoescape(['html', 'xml'], disabled_extensions=('txt',), default_for_string=False),
    undefined=SilentUndefined,
    enable_async=False
)

# --- Helper Functions ---

def _make_context_json_serializable(context: dict) -> dict:
    """
    Recursively cleans a dictionary to ensure all its values are JSON serializable.
    Converts Django model instances to their string representation.
    """
    cleaned_context = {}
    for key, value in context.items():
        if isinstance(value, models.Model):
            cleaned_context[key] = str(value)
        elif isinstance(value, dict):
            cleaned_context[key] = _make_context_json_serializable(value)
        elif isinstance(value, (date, datetime)):
            cleaned_context[key] = value.isoformat()
        elif isinstance(value, Decimal):
            cleaned_context[key] = str(value)
        elif isinstance(value, (ImageFieldFile, FileField)):
            try:
                cleaned_context[key] = value.url if value else None
            except ValueError:
                cleaned_context[key] = None
        elif isinstance(value, list):
            cleaned_context[key] = value
        else:
            cleaned_context[key] = value
    return cleaned_context


def _resolve_value(template_value: Any, flow_context: dict, contact: Contact) -> Any:
    """
    Resolve a template value (string, dict, list, etc.) by rendering Jinja2 templates.
    Returns the resolved value with all {{variable}} expressions substituted.
    """
    if isinstance(template_value, str):
        try:
            template = jinja_env.from_string(template_value)
            context = {**flow_context, 'contact': contact, 'now': timezone.now}
            return template.render(context)
        except Exception as e:
            logger.warning(f"Jinja2 rendering failed for '{template_value}': {e}")
            return template_value
    elif isinstance(template_value, dict):
        return {k: _resolve_value(v, flow_context, contact) for k, v in template_value.items()}
    elif isinstance(template_value, list):
        return [_resolve_value(v, flow_context, contact) for v in template_value]
    else:
        return template_value


def _get_value_from_context_or_contact(variable_name: str, flow_context: dict, contact: Contact) -> Any:
    """
    Get a value from flow context or contact fields.
    Supports nested access like 'contact.name' or 'user.is_staff'.
    """
    if not variable_name:
        return None
    
    parts = variable_name.split('.')
    
    # First, try to get from context
    value = flow_context.get(parts[0])
    
    # If not in context, try contact.field
    if value is None and parts[0] == 'contact':
        obj = contact
        for part in parts[1:]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return None
        return obj
    
    # Handle nested dict access in context
    if isinstance(value, dict):
        for part in parts[1:]:
            value = value.get(part) if isinstance(value, dict) else None
            if value is None:
                break
    
    return value


def _clear_contact_flow_state(contact: Contact, error: bool = False):
    """Clear the active flow state for a contact."""
    ContactFlowState.objects.filter(contact=contact).delete()
    logger.info(f"Cleared flow state for contact {contact.id}. Error: {error}")


# ============================================================================
# MAIN FLOW PROCESSING FUNCTION
# ============================================================================

@transaction.atomic
def process_message_for_flow(contact: Contact, message_data: dict, incoming_message_obj: Message) -> List[Dict[str, Any]]:
    """
    Main entry point for processing an incoming message against flows.
    
    This function handles:
    1. Flow triggering (if contact not in active flow)
    2. Flow state management
    3. Step execution with fall-through processing
    4. Transition evaluation
    5. Fallback handling
    6. Internal commands (switch_flow, end_flow, etc.)
    
    Args:
        contact: Contact object
        message_data: Incoming message data dict
        incoming_message_obj: Message model instance
    
    Returns:
        List of actions to perform (send_whatsapp_message, etc.)
    """
    actions_to_perform = []
    
    try:
        # Optimize queries: fetch entire flow state with related data
        prefetch_query = models.Prefetch(
            'current_step__outgoing_transitions',
            queryset=FlowTransition.objects.select_related('next_step').order_by('priority')
        )
        contact_flow_state = ContactFlowState.objects.select_related(
            'current_flow', 'current_step'
        ).prefetch_related(prefetch_query).filter(contact=contact).first()
        
        # If no active flow, try to trigger one
        if not contact_flow_state:
            logger.info(f"No active flow state for contact {contact.whatsapp_id}. Attempting to trigger a new flow.")
            flow_was_triggered = _trigger_new_flow(contact, message_data, incoming_message_obj)
            
            if flow_was_triggered:
                # Fetch the newly created state and execute its entry step
                contact_flow_state = ContactFlowState.objects.select_related(
                    'current_flow', 'current_step'
                ).prefetch_related(prefetch_query).filter(contact=contact).first()
                
                if not contact_flow_state:
                    logger.warning(f"Flow was triggered for contact {contact.id} but no state was found immediately after.")
                    return []
                
                entry_step = contact_flow_state.current_step
                initial_context = contact_flow_state.flow_context_data or {}
                
                entry_actions, updated_context = _execute_step_actions(entry_step, contact, initial_context.copy())
                actions_to_perform.extend(entry_actions)
                
                contact_flow_state.flow_context_data = updated_context
                contact_flow_state.save(update_fields=['flow_context_data', 'last_updated_at'])
                
                # Check if entry step is a fall-through type
                if contact_flow_state.current_step.step_type not in ['question', 'end_flow', 'human_handover', 'wait_for_reply']:
                    # Continue processing with internal message
                    message_data = {'type': 'internal_flow_start'}
                else:
                    return actions_to_perform
            else:
                return []
        
        # --- Main Flow Processing Loop ---
        is_internal_message = message_data.get('type', '').startswith('internal_')
        just_triggered_flow = contact_flow_state is not None
        
        while True:
            # Re-fetch state for robustness
            contact_flow_state = ContactFlowState.objects.select_related(
                'current_flow', 'current_step'
            ).prefetch_related(prefetch_query).filter(contact=contact).first()
            
            if not contact_flow_state:
                logger.info(f"Flow state was cleared, exiting processing loop for contact {contact.id}.")
                break
            
            current_step = contact_flow_state.current_step
            flow_context = contact_flow_state.flow_context_data or {}
            
            # Validate that we have a valid current step
            if not current_step:
                logger.error(f"CRITICAL: Flow state exists for contact {contact.id} but current_step is None. Clearing state.")
                _clear_contact_flow_state(contact, error=True)
                break
            
            logger.debug(f"Loop iteration: Step '{current_step.name}', Message type: '{message_data.get('type')}'")
            
            # --- Step 1: Execute current step actions ---
            suppress_prompt = not is_internal_message  # Don't prompt on fallback re-execution
            step_actions, updated_context = _execute_step_actions(
                current_step, contact, flow_context.copy(), suppress_prompt=suppress_prompt
            )
            actions_to_perform.extend(step_actions)
            
            # Save context after step execution
            contact_flow_state.flow_context_data = updated_context
            contact_flow_state.save(update_fields=['flow_context_data', 'last_updated_at'])
            
            # Check for internal commands
            switch_action = next((a for a in step_actions if a.get('type') == '_internal_command_switch_flow'), None)
            if switch_action:
                logger.info(f"Contact {contact.id}: Processing internal command to switch flow.")
                try:
                    _clear_contact_flow_state(contact)
                    new_flow_name = switch_action.get('target_flow_name')
                    initial_context_for_new_flow = switch_action.get('initial_context', {})
                    
                    target_flow = Flow.objects.get(name=new_flow_name, is_active=True)
                    entry_point_step = FlowStep.objects.filter(flow=target_flow, is_entry_point=True).first()
                    
                    if not entry_point_step:
                        raise ValueError(f"Flow '{new_flow_name}' has no entry point step defined.")
                    
                    logger.info(f"Contact {contact.id}: Switching to flow '{target_flow.name}'.")
                    
                    new_contact_flow_state = ContactFlowState.objects.create(
                        contact=contact,
                        current_flow=target_flow,
                        current_step=entry_point_step,
                        flow_context_data=initial_context_for_new_flow,
                        started_at=timezone.now()
                    )
                    
                    # Execute entry step for new flow
                    entry_actions, updated_context = _execute_step_actions(
                        entry_point_step, contact, initial_context_for_new_flow.copy()
                    )
                    actions_to_perform.extend(entry_actions)
                    
                    new_contact_flow_state.flow_context_data = updated_context
                    new_contact_flow_state.save(update_fields=['flow_context_data'])
                    
                    # Continue loop with new flow
                    contact_flow_state = new_contact_flow_state
                    message_data = {'type': 'internal_fallthrough'}
                    is_internal_message = True
                    continue
                except Exception as e:
                    logger.error(f"Contact {contact.id}: Failed to switch flow: {e}", exc_info=True)
                    _clear_contact_flow_state(contact, error=True)
                    break
            
            # Check for clear_flow_state command
            if any(a.get('type') == '_internal_command_clear_flow_state' for a in step_actions):
                logger.info(f"Contact {contact.id}: Clearing flow state per internal command.")
                _clear_contact_flow_state(contact)
                break
            
            # Handle wait step with WhatsApp flow response
            if current_step.step_type == 'wait_for_reply':
                if message_data.get('type') != 'nfm_response':
                    logger.debug(f"At wait step '{current_step.name}' but no WhatsApp flow response. Breaking loop.")
                    break
                else:
                    logger.debug(f"At wait step '{current_step.name}' with WhatsApp flow response. Proceeding to evaluate transitions.")
            
            if not is_internal_message:
                just_triggered_flow = False
            
            # --- Step 2: Evaluate transitions from current step ---
            transitions = current_step.outgoing_transitions.all()
            
            if not transitions.exists():
                logger.warning(f"Step '{current_step.name}' has no outgoing transitions. Engaging fallback logic.")
            
            next_step_to_transition_to = None
            for transition in transitions:
                try:
                    condition_met = _evaluate_transition_condition(
                        transition, contact, message_data, updated_context, incoming_message_obj
                    )
                    if condition_met:
                        next_step_to_transition_to = transition.next_step
                        logger.info(
                            f"Transition condition met (ID: {transition.id}, Priority: {transition.priority}): "
                            f"From '{current_step.name}' to '{next_step_to_transition_to.name}'. "
                            f"Condition type: {transition.condition_config.get('type') if isinstance(transition.condition_config, dict) else 'unknown'}"
                        )
                        break
                except Exception as e:
                    logger.error(f"Error evaluating transition {transition.id}: {e}", exc_info=True)
                    continue
            
            if next_step_to_transition_to:
                # Transition to next step
                trans_actions, trans_context = _transition_to_step(
                    contact_flow_state, next_step_to_transition_to, updated_context, contact, message_data
                )
                actions_to_perform.extend(trans_actions)
                updated_context = trans_context
            else:
                # No transition matched - engage fallback logic
                logger.info(f"No transition met for step '{current_step.name}'. Engaging fallback logic.")
                try:
                    fallback_actions = _handle_fallback(current_step, contact, updated_context, contact_flow_state)
                    actions_to_perform.extend(fallback_actions)
                except Exception as e:
                    logger.error(f"Error in fallback handling: {e}", exc_info=True)
                    handover_message = "I've encountered a technical issue. Connecting you with a team member."
                    fallback_actions = _create_human_handover_actions(contact, handover_message)
                    actions_to_perform.extend(fallback_actions)
                break
            
            # --- Step 3: Loop Control ---
            new_state = ContactFlowState.objects.filter(contact=contact).first()
            if not new_state or new_state.current_step.step_type in ['question', 'end_flow', 'human_handover', 'wait_for_reply']:
                break
            
            # For fall-through steps, use empty message data
            message_data = {'type': 'internal_fallthrough'}
            is_internal_message = True
        
    except Exception as e:
        logger.error(f"Critical error in process_message_for_flow: {e}", exc_info=True)
        _clear_contact_flow_state(contact, error=True)
        actions_to_perform = [{
            'type': 'send_whatsapp_message',
            'recipient_wa_id': contact.whatsapp_id,
            'message_type': 'text',
            'data': {'body': 'I seem to be having some technical difficulties. Please try again in a moment.'}
        }]
    
    return actions_to_perform


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _trigger_new_flow(contact: Contact, message_data: dict, incoming_message_obj: Message) -> bool:
    """Attempt to trigger a new flow for a contact based on message content."""
    message_text_body = ""
    if message_data.get('type') == 'text' and isinstance(message_data.get('text'), dict):
        message_text_body = message_data.get('text', {}).get('body', '').strip()
    
    # Extract context keywords from message
    initial_context = {}
    if message_text_body:
        initial_context['trigger_keyword'] = message_text_body
    
    # Try to find matching flow by trigger keywords
    active_flows = Flow.objects.filter(is_active=True)
    triggered_flow = None
    
    for flow in active_flows:
        trigger_keywords = flow.trigger_keywords if isinstance(flow.trigger_keywords, list) else []
        if not trigger_keywords:
            continue
        
        for keyword in trigger_keywords:
            if keyword.lower() in message_text_body.lower():
                triggered_flow = flow
                break
        
        if triggered_flow:
            break
    
    if triggered_flow:
        entry_point_step = FlowStep.objects.filter(flow=triggered_flow, is_entry_point=True).first()
        if entry_point_step:
            logger.info(f"Triggering flow '{triggered_flow.name}' for contact {contact.whatsapp_id}.")
            _clear_contact_flow_state(contact)
            
            ContactFlowState.objects.create(
                contact=contact,
                current_flow=triggered_flow,
                current_step=entry_point_step,
                flow_context_data=initial_context,
                started_at=timezone.now()
            )
            return True
        else:
            logger.error(f"Flow '{triggered_flow.name}' has no entry point.")
            return False
    
    logger.info(f"No flow triggered for contact {contact.whatsapp_id}.")
    return False


def _execute_step_actions(step: FlowStep, contact: Contact, flow_context: dict, suppress_prompt: bool = False) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Execute actions for a step based on its type."""
    actions_to_perform = []
    raw_step_config = step.config or {}
    current_step_context = flow_context.copy()
    
    logger.debug(f"Contact {contact.id}: Executing step '{step.name}' (Type: {step.step_type}).")
    
    if step.step_type == 'send_message':
        try:
            message_config_data = raw_step_config
            if not message_config_data:
                logger.error(f"'send_message' step '{step.name}' has empty config.")
                return actions_to_perform, current_step_context
            
            send_message_config = StepConfigSendMessage.model_validate(message_config_data)
            actual_message_type = send_message_config.message_type
            final_api_data_structure = {}
            
            if actual_message_type == "text" and send_message_config.text:
                text_content = send_message_config.text
                resolved_body = _resolve_value(text_content.body, current_step_context, contact)
                final_api_data_structure = {'body': resolved_body, 'preview_url': text_content.preview_url}
            elif actual_message_type == "interactive" and send_message_config.interactive:
                interactive_payload = send_message_config.interactive.model_dump(exclude_none=True, by_alias=True)
                final_api_data_structure = _resolve_value(interactive_payload, current_step_context, contact)
            
            if final_api_data_structure:
                actions_to_perform.append({
                    'type': 'send_whatsapp_message',
                    'recipient_wa_id': contact.whatsapp_id,
                    'message_type': actual_message_type,
                    'data': final_api_data_structure
                })
        except ValidationError as e:
            logger.error(f"Pydantic validation error for send_message step: {e.errors()}")
    
    elif step.step_type == 'question':
        try:
            question_config = StepConfigQuestion.model_validate(raw_step_config)
            
            # Send the question message
            if question_config.message_config and not suppress_prompt:
                try:
                    msg_pydantic = StepConfigSendMessage.model_validate(question_config.message_config)
                    dummy_config = msg_pydantic.model_dump(exclude_none=True, by_alias=True)
                    dummy_send_step = FlowStep(
                        name=f"{step.name}_prompt", step_type="send_message", config=dummy_config
                    )
                    send_actions, _ = _execute_step_actions(dummy_send_step, contact, current_step_context)
                    actions_to_perform.extend(send_actions)
                except ValidationError as ve:
                    logger.error(f"Message config validation error in question step: {ve.errors()}")
            
            # Set up question expectation in context
            if question_config.reply_config:
                current_step_context['_question_awaiting_reply_for'] = {
                    'variable_name': question_config.reply_config.save_to_variable,
                    'expected_type': question_config.reply_config.expected_type,
                    'validation_regex': question_config.reply_config.validation_regex,
                    'original_question_step_id': step.id
                }
                logger.debug(f"Step '{step.name}' awaiting reply for: {question_config.reply_config.save_to_variable}")
        except ValidationError as e:
            logger.error(f"Pydantic validation for question step failed: {e.errors()}")
    
    elif step.step_type == 'action':
        try:
            action_step_config = StepConfigAction.model_validate(raw_step_config)
            for action_item_conf in action_step_config.actions_to_run:
                action_type = action_item_conf.action_type
                
                # Check action registry for custom actions
                custom_action_func = flow_action_registry.get(action_type)
                if custom_action_func:
                    resolved_params = _resolve_value(action_item_conf.params_template or {}, current_step_context, contact)
                    custom_actions = custom_action_func(contact, current_step_context, resolved_params)
                    if custom_actions:
                        actions_to_perform.extend(custom_actions if isinstance(custom_actions, list) else [custom_actions])
                else:
                    logger.warning(f"Unknown action type: {action_type}")
        except ValidationError as e:
            logger.error(f"Pydantic validation for action step failed: {e.errors()}")
    
    elif step.step_type == 'switch_flow':
        try:
            switch_config = StepConfigSwitchFlow.model_validate(raw_step_config)
            initial_context = _resolve_value(switch_config.initial_context_template or {}, current_step_context, contact)
            if not isinstance(initial_context, dict):
                initial_context = {}
            
            if switch_config.trigger_keyword_to_pass:
                initial_context['simulated_trigger_keyword'] = switch_config.trigger_keyword_to_pass
            
            resolved_target_flow_name = _resolve_value(switch_config.target_flow_name, current_step_context, contact)
            if not resolved_target_flow_name:
                logger.error(f"'switch_flow' step target_flow_name resolved to empty value.")
                return actions_to_perform, current_step_context
            
            actions_to_perform.append({
                'type': '_internal_command_switch_flow',
                'target_flow_name': resolved_target_flow_name,
                'initial_context': initial_context
            })
            logger.info(f"Step '{step.name}' queued switch to flow '{resolved_target_flow_name}'.")
        except ValidationError as e:
            logger.error(f"Pydantic validation for switch_flow step failed:{e.errors()}")
    
    elif step.step_type == 'end_flow':
        try:
            end_flow_config = StepConfigEndFlow.model_validate(raw_step_config)
            if end_flow_config.message_config:
                try:
                    final_msg_config = StepConfigSendMessage.model_validate(end_flow_config.message_config)
                    dummy_config = final_msg_config.model_dump(exclude_none=True, by_alias=True)
                    dummy_end_step = FlowStep(
                        name=f"{step.name}_final_msg", step_type="send_message", config=dummy_config
                    )
                    send_actions, _ = _execute_step_actions(dummy_end_step, contact, current_step_context)
                    actions_to_perform.extend(send_actions)
                except ValidationError as ve:
                    logger.error(f"Message config validation in end_flow step: {ve.errors()}")
            
            logger.info(f"'end_flow' step executed for contact {contact.id}.")
            actions_to_perform.append({'type': '_internal_command_clear_flow_state'})
        except ValidationError as e:
            logger.error(f"Pydantic validation for end_flow step failed: {e.errors()}")
    
    elif step.step_type == 'human_handover':
        try:
            handover_config = StepConfigHumanHandover.model_validate(raw_step_config)
            if handover_config.pre_handover_message_text and not suppress_prompt:
                resolved_msg = _resolve_value(handover_config.pre_handover_message_text, current_step_context, contact)
                actions_to_perform.append({
                    'type': 'send_whatsapp_message',
                    'recipient_wa_id': contact.whatsapp_id,
                    'message_type': 'text',
                    'data': {'body': resolved_msg}
                })
            
            logger.info(f"'human_handover' step executed for contact {contact.id}.")
            actions_to_perform.append({'type': '_internal_command_clear_flow_state'})
        except ValidationError as e:
            logger.error(f"Pydantic validation for human_handover step failed: {e.errors()}")
    
    elif step.step_type in ['condition', 'wait_for_reply', 'start_flow_node']:
        logger.debug(f"'{step.step_type}' step '{step.name}' processed. Logic handled by transitions.")
    else:
        logger.warning(f"Unhandled step_type: '{step.step_type}'")
    
    return actions_to_perform, current_step_context


def _evaluate_transition_condition(transition: FlowTransition, contact: Contact, message_data: dict, flow_context: dict, incoming_message_obj: Message) -> bool:
    """Evaluate if a transition's condition is met."""
    config = transition.condition_config
    if not isinstance(config, dict):
        logger.warning(f"Transition {transition.id} has invalid condition_config")
        return False
    
    condition_type = config.get('type')
    logger.debug(f"Contact {contact.id}: Evaluating condition type '{condition_type}' for transition {transition.id}")
    
    if not condition_type:
        return False
    if condition_type == 'always_true':
        return True
    
    # Extract user reply from message data
    user_text = ""
    if message_data.get('type') == 'text' and isinstance(message_data.get('text'), dict):
        user_text = message_data.get('text', {}).get('body', '').strip()
    
    # Interactive reply ID
    interactive_reply_id = None
    if message_data.get('type') == 'interactive' and isinstance(message_data.get('interactive'), dict):
        interactive_data = message_data.get('interactive', {})
        if isinstance(interactive_data.get('button_reply'), dict):
            interactive_reply_id = interactive_data['button_reply'].get('id')
    
    value_for_condition = config.get('value')
    
    # Rich condition types
    if condition_type == 'user_reply_matches_keyword':
        keyword = config.get('keyword')
        return keyword and keyword.lower() in user_text.lower()
    
    elif condition_type == 'user_reply_matches_regex':
        regex = config.get('regex')
        if regex and user_text:
            try:
                return bool(re.match(regex, user_text))
            except re.error:
                logger.error(f"Invalid regex in transition {transition.id}")
                return False
        return False
    
    elif condition_type == 'interactive_reply_equals':
        return interactive_reply_id and interactive_reply_id == str(value_for_condition)
    
    elif condition_type == 'message_type_is':
        return message_data.get('type') == str(value_for_condition)
    
    elif condition_type == 'variable_equals':
        variable_name = config.get('variable_name')
        if not variable_name:
            return False
        actual_value = _get_value_from_context_or_contact(variable_name, flow_context, contact)
        
        # Handle empty string comparison
        if value_for_condition == "" and actual_value is None:
            return True
        
        return str(actual_value) == str(value_for_condition)
    
    elif condition_type == 'variable_exists':
        variable_name = config.get('variable_name')
        if not variable_name:
            return False
        actual_value = _get_value_from_context_or_contact(variable_name, flow_context, contact)
        return actual_value is not None
    
    elif condition_type == 'variable_contains':
        variable_name = config.get('variable_name')
        if not variable_name:
            return False
        actual_value = _get_value_from_context_or_contact(variable_name, flow_context, contact)
        expected_item = value_for_condition
        
        if isinstance(actual_value, str) and isinstance(expected_item, str):
            return expected_item in actual_value
        elif isinstance(actual_value, list) and expected_item is not None:
            return expected_item in actual_value
        
        return False
    
    elif condition_type == 'contact_is_admin':
        is_admin = hasattr(contact, 'user') and contact.user and contact.user.is_staff and contact.user.is_active
        return is_admin
    
    logger.warning(f"Unknown condition type: '{condition_type}' for transition {transition.id}")
    return False


def _transition_to_step(contact_flow_state: ContactFlowState, next_step: FlowStep, current_flow_context: dict, contact: Contact, message_data: dict) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Transition to a new step and execute its actions."""
    logger.info(
        f"Transitioning contact {contact.whatsapp_id} from '{contact_flow_state.current_step.name}' "
        f"to '{next_step.name}'."
    )
    
    # Clear question-specific context from previous step
    if contact_flow_state.current_step.step_type == 'question':
        current_flow_context.pop('_question_awaiting_reply_for', None)
        current_flow_context.pop('_fallback_count', None)
    
    # Update to new step
    contact_flow_state.current_step = next_step
    contact_flow_state.flow_context_data = current_flow_context
    contact_flow_state.save()
    
    # Execute the new step's actions
    actions_from_new_step, context_after_new_step = _execute_step_actions(
        next_step, contact, current_flow_context.copy()
    )
    
    # Re-fetch state to check for changes
    with transaction.atomic():
        current_db_state = ContactFlowState.objects.select_for_update().filter(contact=contact).first()
        
        if current_db_state and current_db_state.pk == contact_flow_state.pk:
            if current_db_state.flow_context_data != context_after_new_step:
                current_db_state.flow_context_data = context_after_new_step
                current_db_state.save(update_fields=['flow_context_data', 'last_updated_at'])
                logger.debug(f"Saved updated context after executing step '{next_step.name}'.")
        elif not current_db_state:
            logger.info(f"ContactFlowState was cleared during step execution. No final context to save.")
        else:
            logger.info(f"ContactFlowState changed during step execution (e.g., switched flow).")
    
    return actions_from_new_step, context_after_new_step


def _handle_fallback(current_step: FlowStep, contact: Contact, flow_context: dict, contact_flow_state: ContactFlowState) -> List[Dict[str, Any]]:
    """Handle fallback logic when no transition matches (e.g., invalid question reply)."""
    actions_to_perform = []
    updated_context = flow_context.copy()
    
    try:
        fallback_config = FallbackConfig.model_validate(
            current_step.config.get('fallback_config', {}) if isinstance(current_step.config, dict) else {}
        )
    except ValidationError:
        logger.warning(f"Invalid fallback_config for step {current_step.id}. Using defaults.")
        fallback_config = FallbackConfig()
    
    # Question step with invalid reply
    if current_step.step_type == 'question':
        max_retries = fallback_config.max_retries
        current_fallback_count = updated_context.get('_fallback_count', 0)
        
        if fallback_config.action == 're_prompt' and current_fallback_count < max_retries:
            logger.info(f"Re-prompting question step '{current_step.name}' (Attempt {current_fallback_count + 1}/{max_retries}).")
            updated_context['_fallback_count'] = current_fallback_count + 1
            
            # Send prefix message
            prefix_message_text = fallback_config.re_prompt_message_text or "That wasn't a valid response. Let's try again."
            resolved_prefix = _resolve_value(prefix_message_text, updated_context, contact)
            actions_to_perform.append({
                'type': 'send_whatsapp_message',
                'recipient_wa_id': contact.whatsapp_id,
                'message_type': 'text',
                'data': {'body': resolved_prefix}
            })
            
            # Re-execute the question step
            step_actions, re_executed_context = _execute_step_actions(
                current_step, contact, updated_context, suppress_prompt=False
            )
            actions_to_perform.extend(step_actions)
            updated_context = re_executed_context
            
            # Save state and return to wait for next attempt
            contact_flow_state.flow_context_data = updated_context
            contact_flow_state.save(update_fields=['flow_context_data', 'last_updated_at'])
            return actions_to_perform
    
    # Fallback: human handover
    handover_message = "I couldn't understand that. Connecting you to a team member."
    return _create_human_handover_actions(contact, handover_message)


def _create_human_handover_actions(contact: Contact, message_text: str) -> List[Dict[str, Any]]:
    """Create actions for human handover."""
    logger.info(f"Initiating human handover for contact {contact.id}.")
    _clear_contact_flow_state(contact)
    
    return [{
        'type': 'send_whatsapp_message',
        'recipient_wa_id': contact.whatsapp_id,
        'message_type': 'text',
        'data': {'body': message_text}
    }]
