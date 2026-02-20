"""
Flow processing services for flows app.

Functional, loop-based flow engine following conventions from morebnyemba/hanna.
Returns action lists instead of sending messages inline.

Key differences from the old FlowProcessor class:
- Functional instead of class-based
- Loop-based instead of recursive (prevents stack overflow)
- Returns action lists instead of sending messages inline (testable, transaction-safe)
- Uses Jinja2 for template resolution instead of fragile JSON string replacement
- Proper fallback handling with retry counts
- Internal message type system for flow continuation
- Query prefetching for transitions (avoids N+1)
- Proper wait_for_whatsapp_response step handling
"""
import logging
import re
import ast
import json
import operator
from typing import Optional, Dict, Any, List, Tuple

from django.utils import timezone
from django.db import models, transaction

from .models import Flow, FlowStep, FlowTransition, FlowSession
from .utils import render_string_with_context, resolve_value
from conversations.models import Contact

logger = logging.getLogger(__name__)

# Safe operators for AST-based condition evaluation
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


# ---------------------------------------------------------------------------
# Helper: Action builders
# ---------------------------------------------------------------------------

def _create_send_action(wa_id: str, message_config: dict) -> dict:
    """Create a send message action dict (hanna-compatible format).

    Takes a full message_config dict and extracts message_type + type-specific
    data to produce the flat action format used by hanna's flow engine.
    """
    msg_type = message_config.get('message_type', 'text')
    # Extract the type-specific payload (e.g., text.body, interactive data)
    data = message_config.get(msg_type, message_config)
    return {
        'type': 'send_whatsapp_message',
        'recipient_wa_id': wa_id,
        'message_type': msg_type,
        'data': data,
    }


def _create_typing_action(wa_id: str) -> dict:
    """Create a typing indicator action."""
    return {
        'type': 'send_typing_indicator',
        'recipient_wa_id': wa_id,
    }


# ---------------------------------------------------------------------------
# Helper: Flow state management
# ---------------------------------------------------------------------------

def _clear_flow_state(contact: 'Contact', error: bool = False):
    """End all active flow sessions for a contact."""
    status = 'error' if error else 'completed'
    FlowSession.objects.filter(
        contact=contact, status='active'
    ).update(
        status=status,
        completed_at=timezone.now()
    )
    logger.info(f"Cleared flow state for contact {contact.phone_number} (status={status})")


def _create_human_handover_actions(contact: 'Contact', message_text: str) -> List[dict]:
    """Create actions for handing over to a human agent."""
    return [
        _create_typing_action(contact.phone_number),
        _create_send_action(contact.phone_number, {
            'message_type': 'text',
            'text': {'body': message_text}
        }),
        {'type': '_internal_command_end_flow'},
    ]


# ---------------------------------------------------------------------------
# AST-based condition evaluation
# ---------------------------------------------------------------------------

def _eval_ast_node(node, context: dict):
    """Safely evaluate an AST node against flow context."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name):
        return context.get(node.id, None)
    elif isinstance(node, ast.BinOp):
        left = _eval_ast_node(node.left, context)
        right = _eval_ast_node(node.right, context)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported operator: {op_type}")
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_ast_node(node.operand, context)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type}")
    elif isinstance(node, ast.Compare):
        left = _eval_ast_node(node.left, context)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_ast_node(comparator, context)
            op_type = type(op)
            if op_type in SAFE_OPERATORS:
                if not SAFE_OPERATORS[op_type](left, right):
                    return False
                left = right
            else:
                raise ValueError(f"Unsupported comparison: {op_type}")
        return True
    elif isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_eval_ast_node(v, context) for v in node.values)
        elif isinstance(node.op, ast.Or):
            return any(_eval_ast_node(v, context) for v in node.values)
        raise ValueError(f"Unsupported boolean op: {type(node.op)}")
    elif isinstance(node, ast.List):
        return [_eval_ast_node(elt, context) for elt in node.elts]
    elif isinstance(node, ast.Tuple):
        return tuple(_eval_ast_node(elt, context) for elt in node.elts)
    else:
        raise ValueError(f"Unsupported AST node: {type(node)}")


def _evaluate_expression(expression: str, context: dict) -> bool:
    """Safely evaluate a condition expression using AST."""
    try:
        tree = ast.parse(expression, mode='eval')
        return bool(_eval_ast_node(tree.body, context))
    except SyntaxError as e:
        logger.error(f"Invalid expression syntax '{expression}': {e}")
        return False
    except Exception as e:
        logger.error(f"Error evaluating expression '{expression}': {e}")
        return False


def _parse_reply(reply_text: str, expected_type: str, validation: dict = None):
    """Parse and validate user reply. Raises ValueError on invalid input."""
    validation = validation or {}

    if expected_type == 'number':
        try:
            value = float(reply_text)
            if 'min' in validation and value < validation['min']:
                raise ValueError(f"Value must be at least {validation['min']}")
            if 'max' in validation and value > validation['max']:
                raise ValueError(f"Value must be at most {validation['max']}")
            return value
        except ValueError as e:
            if 'Value must be' in str(e):
                raise
            raise ValueError("Please enter a valid number")
    elif expected_type == 'email':
        if not re.match(r'^[\w\.\+\-]+@[\w\.-]+\.\w+$', reply_text):
            raise ValueError("Please enter a valid email address")
        return reply_text
    else:
        return reply_text


# ---------------------------------------------------------------------------
# Step execution - returns (actions, updated_context) without side effects
# ---------------------------------------------------------------------------

def _execute_step_actions(
    step: FlowStep,
    contact: 'Contact',
    flow_context: dict,
    suppress_prompt: bool = False
) -> Tuple[List[dict], dict]:
    """
    Execute a step's actions. Returns (action_list, updated_context).
    Does NOT send messages or modify DB - caller handles that.
    """
    actions = []
    context = flow_context.copy()
    config = step.config or {}
    phone = contact.phone_number

    logger.debug(f"Executing step '{step.name}' (type={step.step_type}) for {phone}")

    if step.step_type == 'send_message':
        try:
            resolved_config = resolve_value(config, context, contact)
            actions.append(_create_typing_action(phone))
            actions.append(_create_send_action(phone, resolved_config))
        except Exception as e:
            logger.error(f"Error in send_message step '{step.name}': {e}")

    elif step.step_type == 'question':
        try:
            message_config = config.get('message_config', {})
            reply_config = config.get('reply_config', {})
            if not suppress_prompt:
                resolved_msg = resolve_value(message_config, context, contact)
                actions.append(_create_typing_action(phone))
                actions.append(_create_send_action(phone, resolved_msg))
            # Set question expectation in context
            if reply_config:
                context['_question_awaiting_reply_for'] = {
                    'variable_name': reply_config.get(
                        'save_to_variable',
                        reply_config.get('context_variable')
                    ),
                    'expected_type': reply_config.get('expected_type', 'text'),
                    'validation_regex': reply_config.get('validation_regex'),
                    'validation': reply_config.get('validation', {}),
                    'original_step_id': step.id,
                    'valid_interactive_ids': _extract_valid_interactive_ids(
                        message_config
                    ),
                }
        except Exception as e:
            logger.error(f"Error in question step '{step.name}': {e}")

    elif step.step_type == 'action':
        try:
            from .actions import flow_action_registry

            actions_to_run = config.get('actions_to_run', [])
            # Also support legacy config where action_type is at top level
            if not actions_to_run and config.get('action_type'):
                actions_to_run = [{
                    'action_type': config.get('action_type'),
                    'parameters': config.get('parameters', {}),
                }]

            for action_item in actions_to_run:
                action_type = action_item.get('action_type')
                parameters = action_item.get(
                    'parameters',
                    action_item.get('params_template', {})
                )
                resolved_params = resolve_value(parameters, context, contact)

                # Check registry first
                action_func = flow_action_registry.get(action_type)
                if action_func:
                    context = action_func(contact, context, resolved_params)
                    # Consume _dynamic_messages queued by the action
                    # (matches hanna pattern where actions return action dicts)
                    dynamic_msgs = context.pop('_dynamic_messages', [])
                    for dm in dynamic_msgs:
                        actions.append(dm)
                elif action_type == 'update_context':
                    context.update(resolved_params)
                elif action_type == 'send_whatsapp_flow':
                    wa_actions = _build_whatsapp_flow_actions(
                        contact, context, resolved_params
                    )
                    actions.extend(wa_actions)
                elif action_type == 'send_dynamic_message':
                    # Reads a pre-built message_config from a context variable
                    # and dispatches it. Allows actions to build dynamic
                    # interactive lists/buttons and have the engine send them.
                    msg_var = resolved_params.get('message_variable')
                    if msg_var and msg_var in context:
                        dynamic_msg = context[msg_var]
                        actions.append(_create_typing_action(phone))
                        actions.append(_create_send_action(phone, dynamic_msg))
                    else:
                        logger.warning(
                            f"send_dynamic_message: variable '{msg_var}' "
                            f"not found in context"
                        )
                else:
                    logger.warning(f"Unknown action type: {action_type}")
        except Exception as e:
            logger.error(
                f"Error in action step '{step.name}': {e}", exc_info=True
            )

    elif step.step_type == 'end_flow':
        try:
            msg_config = config.get('message_config')
            if msg_config and not suppress_prompt:
                resolved = resolve_value(msg_config, context, contact)
                actions.append(_create_send_action(phone, resolved))
            actions.append({'type': '_internal_command_end_flow'})
        except Exception as e:
            logger.error(f"Error in end_flow step '{step.name}': {e}")
            actions.append({'type': '_internal_command_end_flow'})

    elif step.step_type == 'human_handover':
        message = config.get('message', 'Connecting you with a team member...')
        resolved_msg = resolve_value(message, context, contact)
        actions.append(_create_typing_action(phone))
        actions.append(_create_send_action(phone, {
            'message_type': 'text',
            'text': {'body': resolved_msg}
        }))
        actions.append({'type': '_internal_command_end_flow'})

    elif step.step_type == 'switch_flow':
        target_name = config.get('target_flow_name', config.get('target_flow'))
        if target_name:
            resolved_name = (
                resolve_value(target_name, context, contact)
                if isinstance(target_name, str) else target_name
            )
            initial_ctx = resolve_value(
                config.get('initial_context_template', {}), context, contact
            )
            switch_msg = config.get('message')
            if switch_msg and not suppress_prompt:
                resolved = resolve_value(switch_msg, context, contact)
                actions.append(_create_send_action(phone, {
                    'message_type': 'text',
                    'text': {'body': resolved}
                }))
            actions.append({
                'type': '_internal_command_switch_flow',
                'target_flow_name': resolved_name,
                'initial_context': initial_ctx if isinstance(initial_ctx, dict) else {},
            })
        else:
            logger.error(f"switch_flow step '{step.name}' has no target_flow_name")

    elif step.step_type in ('condition', 'wait_for_reply', 'start_flow_node'):
        logger.debug(f"Step type '{step.step_type}' for '{step.name}' - no direct actions")

    else:
        logger.warning(f"Unhandled step_type '{step.step_type}' for step '{step.name}'")

    return actions, context


def _build_whatsapp_flow_actions(
    contact: 'Contact', context: dict, params: dict
) -> List[dict]:
    """Build WhatsApp interactive flow message actions."""
    phone = contact.phone_number
    flow_data_var = params.get(
        'flow_data_variable', params.get('flow_variable', 'wa_flow_data')
    )
    flow_data = context.get(flow_data_var, {})
    flow_id = flow_data.get('flow_id')

    if not flow_id:
        logger.error(f"No flow_id in context variable '{flow_data_var}'")
        return []

    cta_text = params.get('cta_text', 'Start Form')
    body_text = params.get('body_text', 'Please complete the form below.')
    screen = params.get('initial_screen', 'WELCOME')

    flow_msg = {
        'message_type': 'interactive',
        'interactive': {
            'type': 'flow',
            'body': {'text': body_text},
            'action': {
                'name': 'flow',
                'parameters': {
                    'flow_message_version': '3',
                    'flow_token': (
                        f"{contact.id}-{flow_data.get('name', 'flow')}"
                        f"-{timezone.now().timestamp()}"
                    ),
                    'flow_id': flow_id,
                    'flow_cta': cta_text,
                    'flow_action': 'navigate',
                    'flow_action_payload': {'screen': screen},
                }
            }
        }
    }
    return [
        _create_typing_action(phone),
        _create_send_action(phone, flow_msg),
    ]


# ---------------------------------------------------------------------------
# Transition evaluation
# ---------------------------------------------------------------------------

def _evaluate_transition_condition(
    transition: FlowTransition,
    contact: 'Contact',
    message_data: dict,
    flow_context: dict,
) -> bool:
    """Evaluate whether a transition's condition is met."""
    config = transition.condition_config
    if not config:
        return True  # No condition = auto transition

    condition_type = config.get('type', 'auto')

    # Extract message info
    user_text = ''
    interactive_reply_id = None

    msg_type = message_data.get('type', '')
    if msg_type == 'text':
        user_text = message_data.get('text', {}).get('body', '').strip()
    elif msg_type == 'interactive':
        interactive_payload = message_data.get('interactive', {})
        interactive_type = interactive_payload.get('type')
        if interactive_type == 'button_reply':
            interactive_reply_id = interactive_payload.get(
                'button_reply', {}
            ).get('id')
        elif interactive_type == 'list_reply':
            interactive_reply_id = interactive_payload.get(
                'list_reply', {}
            ).get('id')

    # Fallback: use _last_user_reply from context
    if not user_text:
        user_text = str(flow_context.get('_last_user_reply', ''))

    # --- Evaluate condition types ---

    if condition_type in ('auto', 'always_true'):
        return True

    elif condition_type == 'condition_true':
        condition_expr = config.get('condition')
        if condition_expr:
            return _evaluate_expression(condition_expr, flow_context)
        return False

    elif condition_type == 'condition_false':
        condition_expr = config.get('condition')
        if condition_expr:
            return not _evaluate_expression(condition_expr, flow_context)
        return False

    elif condition_type == 'expression':
        expr = config.get('expression')
        return _evaluate_expression(expr, flow_context) if expr else False

    elif condition_type == 'user_reply_matches':
        return _check_user_reply_matches(config, flow_context)

    elif condition_type == 'user_reply_matches_keyword':
        keyword = str(config.get('keyword', '')).strip()
        if not keyword:
            return False
        case_sensitive = config.get('case_sensitive', False)
        if case_sensitive:
            return keyword == user_text
        return keyword.lower() == user_text.lower()

    elif condition_type == 'interactive_reply_id_equals':
        expected = config.get('value', config.get('reply_id'))
        if interactive_reply_id and expected:
            return str(interactive_reply_id) == str(expected)
        # Also check _last_user_reply for button replies forwarded as text
        return str(flow_context.get('_last_user_reply', '')) == str(expected)

    elif condition_type == 'context_variable_equals':
        var_name = config.get('variable', config.get('variable_name'))
        expected_value = config.get('value')
        actual_value = flow_context.get(var_name)
        return actual_value == expected_value

    elif condition_type == 'variable_exists':
        var_name = config.get('variable_name')
        return var_name is not None and var_name in flow_context

    elif condition_type == 'whatsapp_flow_response_received':
        return flow_context.get('whatsapp_flow_response_received') is True

    elif condition_type == 'variable_equals':
        var_name = config.get('variable_name')
        if var_name is None:
            return False
        actual = flow_context.get(var_name)
        expected = config.get('value')
        if actual is not None and expected is not None:
            try:
                if isinstance(expected, (int, float)):
                    return float(actual) == float(expected)
            except (ValueError, TypeError):
                pass
        return (
            str(actual) == str(expected) if actual is not None else False
        )

    elif condition_type == 'message_type_is':
        return msg_type == str(config.get('value'))

    elif condition_type == 'user_reply_matches_regex':
        regex = config.get('regex')
        if regex and user_text:
            try:
                return bool(re.match(regex, user_text))
            except re.error as e:
                logger.error(f"Invalid regex in transition {transition.id}: {e}")
        return False

    else:
        logger.warning(
            f"Unknown condition type '{condition_type}' in transition {transition.id}"
        )
        return False


def _check_user_reply_matches(config: dict, flow_context: dict) -> bool:
    """Check if last user reply matches pattern/keywords."""
    last_reply = str(flow_context.get('_last_user_reply', '')).strip().lower()
    if not last_reply:
        return False

    pattern = config.get('pattern')
    if pattern:
        try:
            if re.search(pattern, last_reply, re.IGNORECASE):
                return True
        except re.error:
            return False

    keywords = config.get('keywords', [])
    if keywords:
        match_type = config.get('match_type', 'contains')
        kw_lower = [k.lower() for k in keywords]
        if match_type == 'exact':
            return last_reply in kw_lower
        return any(k in last_reply for k in kw_lower)

    return False


# ---------------------------------------------------------------------------
# Fallback handling
# ---------------------------------------------------------------------------

def _handle_fallback(
    current_step: FlowStep,
    contact: 'Contact',
    flow_context: dict,
    session: FlowSession,
) -> Tuple[List[dict], dict]:
    """
    Handle when no transition condition matches.

    For question steps:
      1. Sends a short "I didn't understand" nudge.
      2. Re-sends the *original* question message (buttons, list, etc.)
         so the user sees the interactive options again.
      3. Preserves the _question_awaiting_reply_for expectation so the
         engine continues waiting for the correct reply.
      4. After max retries, hands over to a human or ends the flow.

    Returns (actions, updated_context).
    """
    actions = []
    context = flow_context.copy()
    config = current_step.config or {}

    fallback_cfg = config.get('fallback_config', {})
    max_retries = fallback_cfg.get('max_retries', 3)
    re_prompt_text = fallback_cfg.get('re_prompt_message_text')
    action_after = fallback_cfg.get('action_after_retries', 'human_handover')

    if current_step.step_type == 'question':
        fallback_count = context.get('_fallback_count', 0)
        fallback_count += 1
        context['_fallback_count'] = fallback_count

        if fallback_count <= max_retries:
            phone = contact.phone_number

            # --- 1. Send a short nudge explaining what went wrong ---
            nudge = re_prompt_text or _default_nudge_for_question(config)
            resolved_nudge = resolve_value(nudge, context, contact)
            actions.append(_create_send_action(phone, {
                'message_type': 'text',
                'text': {'body': resolved_nudge}
            }))

            # --- 2. Re-send the original question (buttons / list / text) ---
            message_config = config.get('message_config', {})
            if message_config:
                resolved_msg = resolve_value(message_config, context, contact)
                actions.append(_create_typing_action(phone))
                actions.append(_create_send_action(phone, resolved_msg))

            # --- 3. Ensure the question expectation is still set ---
            reply_config = config.get('reply_config', {})
            if reply_config and '_question_awaiting_reply_for' not in context:
                context['_question_awaiting_reply_for'] = {
                    'variable_name': reply_config.get(
                        'save_to_variable',
                        reply_config.get('context_variable')
                    ),
                    'expected_type': reply_config.get('expected_type', 'text'),
                    'validation_regex': reply_config.get('validation_regex'),
                    'validation': reply_config.get('validation', {}),
                    'original_step_id': current_step.id,
                    'valid_interactive_ids': _extract_valid_interactive_ids(
                        message_config
                    ),
                }

            logger.info(
                f"Fallback re-prompt ({fallback_count}/{max_retries}) "
                f"at step '{current_step.name}'"
            )
        else:
            logger.info(
                f"Fallback retries exhausted at '{current_step.name}', "
                f"action: {action_after}"
            )
            if action_after == 'end_flow':
                actions.append(_create_send_action(contact.phone_number, {
                    'message_type': 'text',
                    'text': {'body': "I wasn't able to process your request. Please try again later."}
                }))
                actions.append({'type': '_internal_command_end_flow'})
            else:
                # Default: human handover
                msg = "I'm having trouble understanding. Let me connect you with a team member."
                actions.extend(_create_human_handover_actions(contact, msg))
    else:
        # Non-question dead end
        logger.error(
            f"Dead end at step '{current_step.name}' (type={current_step.step_type}). "
            f"No valid transition. Initiating handover."
        )
        msg = "I've encountered a technical issue. Let me connect you with a team member."
        actions.extend(_create_human_handover_actions(contact, msg))

    return actions, context


def _default_nudge_for_question(config: dict) -> str:
    """
    Generate a contextual nudge message based on the question's expected
    reply type, so the user knows *what* kind of answer is expected.
    """
    reply_config = config.get('reply_config', {})
    expected_type = reply_config.get('expected_type', 'text')
    message_config = config.get('message_config', {})
    interactive = message_config.get('interactive', {})
    itype = interactive.get('type', '')

    if expected_type == 'number':
        return "⚠️ That doesn't look like a valid number. Please enter a number."
    elif expected_type == 'email':
        return "⚠️ That doesn't look like a valid email address. Please try again."
    elif expected_type == 'location':
        return (
            "📍 I need your location pin to continue.\n"
            "Tap 📎 → 📍 Location → Send your current location."
        )
    elif expected_type == 'interactive_id':
        if itype == 'button':
            return "👆 Please tap one of the buttons above to continue."
        elif itype == 'list':
            return "👆 Please select an option from the list above to continue."
        return "👆 Please select one of the options above to continue."
    elif expected_type == 'image':
        return "📷 I need an image to continue. Please send a photo."
    else:
        validation_regex = reply_config.get('validation_regex')
        if validation_regex:
            return "⚠️ Your response didn't match the expected format. Please try again."
        return "I didn't quite understand that. Please try again."


def _extract_valid_interactive_ids(message_config: dict) -> list:
    """
    Extract all valid interactive reply IDs (button IDs and list-row IDs)
    from a question step's message_config.

    Used to detect stale button/list taps from previously sent messages:
    if the incoming reply ID is not in this list, the tap came from an
    old message and should be rejected.

    Returns an empty list when the config contains no static interactive
    options (e.g. dynamically generated content) — in that case all
    interactive replies are accepted (backward-compatible).
    """
    ids: list[str] = []
    interactive = message_config.get('interactive', {})
    action = interactive.get('action', {})

    # WhatsApp buttons
    for btn in action.get('buttons', []):
        btn_id = btn.get('reply', {}).get('id')
        if btn_id:
            ids.append(str(btn_id))

    # WhatsApp list rows
    for section in action.get('sections', []):
        for row in section.get('rows', []):
            row_id = row.get('id')
            if row_id:
                ids.append(str(row_id))

    return ids


# ---------------------------------------------------------------------------
# Flow triggering
# ---------------------------------------------------------------------------

def _trigger_new_flow(
    contact: 'Contact', message_text: str
) -> Optional[FlowSession]:
    """
    Try to trigger a new flow from message text.
    Uses proper keyword matching (iterates keywords in Python, not __icontains).
    Returns the new FlowSession if triggered, None otherwise.
    """
    if not message_text:
        return None

    text_lower = message_text.lower().strip()

    active_flows = Flow.objects.filter(is_active=True).only(
        'id', 'name', 'trigger_keywords'
    )

    matched_flow = None
    for flow in active_flows:
        keywords = flow.trigger_keywords or []
        for keyword in keywords:
            if isinstance(keyword, str) and keyword.lower() in text_lower:
                matched_flow = flow
                break
        if matched_flow:
            break

    if not matched_flow:
        return None

    entry_step = FlowStep.objects.filter(
        flow=matched_flow, is_entry_point=True
    ).first()

    if not entry_step:
        logger.error(f"Flow '{matched_flow.name}' has no entry point")
        return None

    # End any existing active sessions
    FlowSession.objects.filter(
        contact=contact, status='active'
    ).update(
        status='abandoned',
        completed_at=timezone.now()
    )

    session = FlowSession.objects.create(
        contact=contact,
        flow=matched_flow,
        current_step=entry_step,
        status='active',
        context_data={}
    )

    logger.info(f"Triggered flow '{matched_flow.name}' for {contact.phone_number}")
    return session


# ---------------------------------------------------------------------------
# Transition helper
# ---------------------------------------------------------------------------

def _transition_to_step(
    session: FlowSession,
    next_step: FlowStep,
    flow_context: dict,
    contact: 'Contact',
) -> Tuple[List[dict], dict]:
    """
    Transition to a new step: update session, execute step actions.
    Returns (actions, updated_context).
    """
    # Clear question-specific context from previous step
    if session.current_step and session.current_step.step_type == 'question':
        flow_context.pop('_question_awaiting_reply_for', None)
        flow_context.pop('_fallback_count', None)

    logger.info(
        f"Transitioning from "
        f"'{session.current_step.name if session.current_step else 'None'}' "
        f"to '{next_step.name}'"
    )

    session.current_step = next_step
    session.context_data = flow_context
    session.save(update_fields=['current_step', 'context_data', 'updated_at'])

    step_actions, updated_context = _execute_step_actions(
        next_step, contact, flow_context.copy()
    )

    # Persist context changes made by the step (e.g. action steps that
    # set variables like package_found, _package_id_map, etc.).
    # Without this, the loop's re-fetch of session.context_data would
    # lose any variables the step just set.
    if updated_context != flow_context:
        session.context_data = updated_context
        session.save(update_fields=['context_data', 'updated_at'])

    return step_actions, updated_context


# ---------------------------------------------------------------------------
# Internal command processor
# ---------------------------------------------------------------------------

def _process_internal_commands(
    actions: List[dict],
    contact: 'Contact',
    session: FlowSession,
    context: dict,
) -> List[dict]:
    """Process _internal_command_* actions and return only external actions."""
    result = []
    for action in actions:
        action_type = action.get('type', '')
        if action_type == '_internal_command_end_flow':
            _clear_flow_state(contact)
        elif action_type == '_internal_command_switch_flow':
            _clear_flow_state(contact)
            try:
                target_flow = Flow.objects.get(
                    name=action['target_flow_name'], is_active=True
                )
                entry = FlowStep.objects.filter(
                    flow=target_flow, is_entry_point=True
                ).first()
                if entry:
                    new_session = FlowSession.objects.create(
                        contact=contact,
                        flow=target_flow,
                        current_step=entry,
                        status='active',
                        context_data=action.get('initial_context', {}),
                    )
                    entry_actions, ctx = _execute_step_actions(
                        entry, contact, new_session.context_data.copy()
                    )
                    result.extend(
                        a for a in entry_actions
                        if not a.get('type', '').startswith('_internal_')
                    )
                    new_session.context_data = ctx
                    new_session.save(update_fields=['context_data', 'updated_at'])
            except Flow.DoesNotExist:
                logger.error(
                    f"Switch target flow '{action.get('target_flow_name')}' not found"
                )
        elif not action_type.startswith('_internal_'):
            result.append(action)
    return result


# ---------------------------------------------------------------------------
# Reply processing helper
# ---------------------------------------------------------------------------

def _process_question_reply(
    message_data: dict,
    flow_context: dict,
    question_expectation: dict,
) -> Tuple[bool, Any]:
    """
    Process a user's reply to a question step.
    Returns (is_valid, parsed_value).
    """
    variable_name = question_expectation.get('variable_name')
    expected_type = question_expectation.get('expected_type', 'text')
    validation = question_expectation.get('validation', {})
    validation_regex = question_expectation.get('validation_regex')

    msg_type = message_data.get('type', '')

    # Text-based replies
    if msg_type == 'text':
        user_text = message_data.get('text', {}).get('body', '').strip()
        if not user_text:
            return False, None

        if expected_type == 'number':
            try:
                return True, _parse_reply(user_text, 'number', validation)
            except ValueError:
                return False, None
        elif expected_type == 'email':
            try:
                return True, _parse_reply(user_text, 'email')
            except ValueError:
                return False, None
        elif expected_type == 'interactive_id':
            # When expecting an interactive reply (button/list tap), free-form
            # text is NOT valid — the user needs to pick an option.
            # Return invalid so the fallback re-prompts with the buttons/list.
            return False, None
        elif expected_type == 'location':
            # Text is not a valid location
            return False, None
        elif expected_type == 'image':
            # Text is not a valid image
            return False, None
        else:
            # text type
            if validation_regex:
                if re.match(validation_regex, user_text):
                    return True, user_text
                return False, None
            return True, user_text

    # Interactive replies
    elif msg_type == 'interactive':
        interactive = message_data.get('interactive', {})
        itype = interactive.get('type')

        if itype in ('button_reply', 'list_reply'):
            if itype == 'button_reply':
                reply_id = interactive.get('button_reply', {}).get('id')
            else:
                reply_id = interactive.get('list_reply', {}).get('id')

            # Guard against stale taps from previously sent messages.
            # If the question step defined static button/list options we
            # know which IDs are valid.  An ID that does not appear in
            # that list came from an old message and must be rejected so
            # the engine re-prompts the current question instead of
            # letting an always_true catch-all transition misroute.
            valid_ids = question_expectation.get('valid_interactive_ids')
            if valid_ids and str(reply_id) not in valid_ids:
                logger.info(
                    f"Stale interactive tap rejected: '{reply_id}' "
                    f"not in valid IDs {valid_ids}"
                )
                return False, None

            return True, reply_id

        elif itype == 'nfm_reply':
            nfm = interactive.get('nfm_reply', {})
            resp_json = nfm.get('response_json')
            if resp_json:
                try:
                    return True, json.loads(resp_json)
                except json.JSONDecodeError:
                    return True, nfm
            return True, nfm

    # Internal WhatsApp flow response
    elif msg_type == 'internal_whatsapp_flow_response':
        if expected_type == 'nfm_reply':
            return True, flow_context.get('whatsapp_flow_data')
        # The data was already merged into context by the response processor
        return True, flow_context.get('whatsapp_flow_data')

    # Location
    elif msg_type == 'location':
        return True, message_data.get('location')

    # Image
    elif msg_type == 'image':
        img_id = message_data.get('image', {}).get('id')
        if img_id:
            return True, img_id

    return False, None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

@transaction.atomic
def process_message_for_flow(
    contact: 'Contact', message_data: dict
) -> List[Dict[str, Any]]:
    """
    Process a message within the flow system.

    Args:
        contact: The Contact sending the message
        message_data: Structured message data, e.g.:
            {'type': 'text', 'text': {'body': 'hello'}}
            {'type': 'interactive', 'interactive': {'type': 'button_reply', ...}}
            {'type': 'internal_flow_start'}
            {'type': 'internal_whatsapp_flow_response'}

    Returns:
        List of action dicts to execute (send messages, typing indicators, etc.)
    """
    actions_to_perform = []

    # Prefetch transitions for efficient querying
    prefetch_query = models.Prefetch(
        'outgoing_transitions',
        queryset=FlowTransition.objects.select_related(
            'next_step'
        ).order_by('priority'),
    )

    # Get active session
    session = (
        FlowSession.objects
        .select_related('flow', 'current_step')
        .prefetch_related(
            models.Prefetch(
                'current_step__outgoing_transitions',
                queryset=FlowTransition.objects.select_related(
                    'next_step'
                ).order_by('priority'),
            )
        )
        .filter(contact=contact, status='active')
        .first()
    )

    try:
        if not session:
            # No active flow - try to trigger one
            msg_type = message_data.get('type', '')
            text = ''
            if msg_type == 'text':
                text = message_data.get('text', {}).get('body', '')

            session = _trigger_new_flow(contact, text)
            if not session:
                return []

            # Re-fetch with prefetch
            session = (
                FlowSession.objects
                .select_related('flow', 'current_step')
                .prefetch_related(
                    models.Prefetch(
                        'current_step__outgoing_transitions',
                        queryset=FlowTransition.objects.select_related(
                            'next_step'
                        ).order_by('priority'),
                    )
                )
                .get(pk=session.pk)
            )

            # Execute entry step
            entry_step = session.current_step
            initial_context = session.context_data or {}
            entry_actions, updated_context = _execute_step_actions(
                entry_step, contact, initial_context.copy()
            )
            actions_to_perform.extend(entry_actions)

            session.context_data = updated_context
            session.save(update_fields=['context_data', 'updated_at'])

            # If entry step needs user input, return now
            if entry_step.step_type in ('question', 'end_flow', 'human_handover'):
                actions_to_perform = _process_internal_commands(
                    actions_to_perform, contact, session, updated_context
                )
                return actions_to_perform

            # Fall through to main loop for action/send_message steps
            message_data = {'type': 'internal_flow_start'}

        # --- Main Processing Loop ---
        max_iterations = 50
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            is_internal = message_data.get('type', '').startswith('internal_')

            # Re-fetch session state each iteration
            session = (
                FlowSession.objects
                .select_related('flow', 'current_step')
                .prefetch_related(
                    models.Prefetch(
                        'current_step__outgoing_transitions',
                        queryset=FlowTransition.objects.select_related(
                            'next_step'
                        ).order_by('priority'),
                    )
                )
                .filter(contact=contact, status='active')
                .first()
            )

            if not session:
                logger.info(
                    f"Flow state cleared for {contact.phone_number}, "
                    f"exiting loop"
                )
                break

            current_step = session.current_step
            flow_context = session.context_data or {}

            if not current_step:
                logger.error(
                    f"Session {session.id} has no current_step. Clearing state."
                )
                _clear_flow_state(contact, error=True)
                break

            logger.debug(
                f"Loop #{iteration}: step='{current_step.name}' "
                f"type={current_step.step_type} msg_type={message_data.get('type')}"
            )

            # --- CRITICAL: Early conversion of already-processed WhatsApp Flow responses ---
            # If we receive an nfm_reply but context already has whatsapp_flow_response_received,
            # convert to internal type to prevent re-processing (matches hanna pattern).
            if (message_data.get('type') == 'interactive'
                    and message_data.get('interactive', {}).get('type') == 'nfm_reply'
                    and flow_context.get('whatsapp_flow_response_received')):
                logger.info(
                    f"Converting already-processed nfm_reply to "
                    f"internal_whatsapp_flow_response for {contact.phone_number}"
                )
                message_data = {'type': 'internal_whatsapp_flow_response'}
                is_internal = True

            # --- Handle question step awaiting reply ---
            _stale_interactive_tap = False

            if (current_step.step_type == 'question'
                    and '_question_awaiting_reply_for' in flow_context):

                # If internal (not user reply), break to wait
                if (is_internal
                        and message_data.get('type') != 'internal_whatsapp_flow_response'):
                    logger.debug(
                        f"Reached question '{current_step.name}' via internal. "
                        f"Waiting for user reply."
                    )
                    break

                # Process the user's reply
                question_exp = flow_context['_question_awaiting_reply_for']
                reply_valid, value_to_save = _process_question_reply(
                    message_data, flow_context, question_exp
                )

                variable_name = question_exp.get('variable_name')

                if reply_valid and variable_name:
                    flow_context[variable_name] = value_to_save
                    flow_context['_last_user_reply'] = (
                        str(value_to_save) if value_to_save is not None else ''
                    )
                    flow_context.pop('_question_awaiting_reply_for', None)
                    flow_context.pop('_fallback_count', None)
                    logger.info(f"Saved reply '{variable_name}' = {value_to_save}")
                elif not reply_valid:
                    # Store raw text for transition evaluation (keyword
                    # escape hatches like "menu" should still work).
                    if message_data.get('type') == 'text':
                        flow_context['_last_user_reply'] = (
                            message_data.get('text', {}).get('body', '')
                        )
                    # Interactive button/list taps that failed validation are
                    # stale clicks from previously sent messages.  Skip
                    # transition evaluation entirely to prevent always_true
                    # catch-all transitions from misrouting the flow.
                    elif message_data.get('type') == 'interactive':
                        itype = message_data.get(
                            'interactive', {}
                        ).get('type', '')
                        if itype in ('button_reply', 'list_reply'):
                            _stale_interactive_tap = True
                    logger.info(
                        f"Reply not valid for expected_type="
                        f"{question_exp.get('expected_type')}"
                    )

                session.context_data = flow_context
                session.save(update_fields=['context_data', 'updated_at'])

            # --- Handle wait_for_whatsapp_response action step ---
            if (current_step.step_type == 'action'
                    and (current_step.config or {}).get('wait_for') == 'whatsapp_flow_response'):
                if (is_internal
                        and message_data.get('type') != 'internal_whatsapp_flow_response'):
                    logger.debug(
                        f"At wait step '{current_step.name}'. "
                        f"Pausing for WhatsApp flow response."
                    )
                    break

            # --- Store last user reply for transition evaluation ---
            if (not is_internal
                    and message_data.get('type') == 'text'
                    and '_last_user_reply' not in flow_context):
                flow_context['_last_user_reply'] = (
                    message_data.get('text', {}).get('body', '')
                )
                session.context_data = flow_context
                session.save(update_fields=['context_data', 'updated_at'])

            # --- Stale interactive tap: skip transitions, re-prompt ---
            # A button/list tap from a previously sent message should never
            # be routed through transitions (an always_true catch-all would
            # misroute the flow).  Go straight to fallback re-prompt.
            if _stale_interactive_tap:
                logger.info(
                    f"Stale interactive tap at step '{current_step.name}'. "
                    f"Skipping transitions — re-prompting."
                )
                fallback_actions, flow_context = _handle_fallback(
                    current_step, contact, flow_context, session
                )
                actions_to_perform.extend(
                    a for a in fallback_actions
                    if not a.get('type', '').startswith('_internal_')
                )
                if any(
                    a.get('type') == '_internal_command_end_flow'
                    for a in fallback_actions
                ):
                    _clear_flow_state(contact)
                session.context_data = flow_context
                session.save(update_fields=['context_data', 'updated_at'])
                break

            # --- Evaluate transitions ---
            transitions = current_step.outgoing_transitions.all()

            next_step = None
            for transition in transitions:
                try:
                    if _evaluate_transition_condition(
                        transition, contact, message_data, flow_context
                    ):
                        next_step = transition.next_step
                        logger.info(
                            f"Transition matched: '{current_step.name}' → "
                            f"'{next_step.name}' "
                            f"(condition={transition.condition_config.get('type', 'auto') if transition.condition_config else 'auto'})"
                        )
                        break
                except Exception as e:
                    logger.error(
                        f"Error evaluating transition {transition.id}: {e}",
                        exc_info=True,
                    )
                    continue

            if next_step:
                # Execute transition
                step_actions, flow_context = _transition_to_step(
                    session, next_step, flow_context, contact
                )

                # Separate internal commands from external actions
                switch_action = next(
                    (a for a in step_actions
                     if a.get('type') == '_internal_command_switch_flow'),
                    None,
                )
                end_action = next(
                    (a for a in step_actions
                     if a.get('type') == '_internal_command_end_flow'),
                    None,
                )

                actions_to_perform.extend(
                    a for a in step_actions
                    if not a.get('type', '').startswith('_internal_')
                )

                if end_action:
                    _clear_flow_state(contact)
                    break

                if switch_action:
                    _clear_flow_state(contact)

                    new_flow_name = switch_action.get('target_flow_name')
                    initial_context = switch_action.get('initial_context', {})

                    try:
                        target_flow = Flow.objects.get(
                            name=new_flow_name, is_active=True
                        )
                        entry_point = FlowStep.objects.filter(
                            flow=target_flow, is_entry_point=True
                        ).first()

                        if not entry_point:
                            raise ValueError(
                                f"Flow '{new_flow_name}' has no entry point"
                            )

                        new_session = FlowSession.objects.create(
                            contact=contact,
                            flow=target_flow,
                            current_step=entry_point,
                            status='active',
                            context_data=initial_context,
                        )

                        entry_actions, updated_ctx = _execute_step_actions(
                            entry_point, contact, initial_context.copy()
                        )
                        actions_to_perform.extend(
                            a for a in entry_actions
                            if not a.get('type', '').startswith('_internal_')
                        )

                        new_session.context_data = updated_ctx
                        new_session.save(
                            update_fields=['context_data', 'updated_at']
                        )

                        session = new_session
                        flow_context = updated_ctx

                        if entry_point.step_type in (
                            'question', 'end_flow', 'human_handover'
                        ):
                            break

                        message_data = {'type': 'internal_flow_start'}
                        continue

                    except Flow.DoesNotExist:
                        logger.error(
                            f"Switch target flow '{new_flow_name}' not found"
                        )
                        actions_to_perform.append(
                            _create_send_action(contact.phone_number, {
                                'message_type': 'text',
                                'text': {
                                    'body': 'Sorry, an error occurred. Please try again.'
                                }
                            })
                        )
                        break
                    except Exception as e:
                        logger.error(
                            f"Error switching to flow '{new_flow_name}': {e}",
                            exc_info=True,
                        )
                        break

                # Loop control: break if next step needs user input
                if next_step.step_type in (
                    'question', 'end_flow', 'human_handover'
                ):
                    break

                # For fall-through steps, use internal message
                if not is_internal:
                    message_data = {'type': 'internal_fallthrough'}

            else:
                # No transition matched - engage fallback
                logger.info(
                    f"No transition matched from step '{current_step.name}'. "
                    f"Engaging fallback."
                )
                fallback_actions, flow_context = _handle_fallback(
                    current_step, contact, flow_context, session
                )
                actions_to_perform.extend(
                    a for a in fallback_actions
                    if not a.get('type', '').startswith('_internal_')
                )

                if any(
                    a.get('type') == '_internal_command_end_flow'
                    for a in fallback_actions
                ):
                    _clear_flow_state(contact)

                session.context_data = flow_context
                session.save(update_fields=['context_data', 'updated_at'])
                break

        if iteration >= max_iterations:
            logger.error(
                f"Max iterations ({max_iterations}) reached for "
                f"{contact.phone_number}. Clearing state."
            )
            _clear_flow_state(contact, error=True)
            actions_to_perform.append(
                _create_send_action(contact.phone_number, {
                    'message_type': 'text',
                    'text': {
                        'body': 'Sorry, something went wrong. Please try again.'
                    }
                })
            )

    except Exception as e:
        logger.error(
            f"Critical error in process_message_for_flow for "
            f"{contact.phone_number}: {e}",
            exc_info=True,
        )
        _clear_flow_state(contact, error=True)
        actions_to_perform = [
            _create_send_action(contact.phone_number, {
                'message_type': 'text',
                'text': {
                    'body': (
                        'I seem to be having technical difficulties. '
                        'Please try again in a moment.'
                    )
                }
            })
        ]

    return actions_to_perform


# ---------------------------------------------------------------------------
# Action executor - sends the actions returned by process_message_for_flow
# ---------------------------------------------------------------------------

def execute_actions(actions: List[Dict[str, Any]]):
    """
    Execute a list of actions (send messages, typing indicators, etc.).
    Called by the task layer after process_message_for_flow returns.

    Actions use hanna-compatible format:
    - send_whatsapp_message: {recipient_wa_id, message_type, data}
    - send_typing_indicator: {recipient_wa_id}
    """
    from meta_integration.utils import send_whatsapp_message

    for action in actions:
        action_type = action.get('type')
        try:
            if action_type == 'send_whatsapp_message':
                wa_id = action.get('recipient_wa_id')
                msg_type = action.get('message_type')
                data = action.get('data')
                if wa_id and msg_type and data is not None:
                    # Call with hanna-compatible signature (to_phone_number, message_type, data)
                    send_whatsapp_message(wa_id, msg_type, data)
            elif action_type == 'send_typing_indicator':
                wa_id = action.get('recipient_wa_id')
                if wa_id:
                    try:
                        from meta_integration.services import WhatsAppAPIService
                        service = WhatsAppAPIService()
                        service.send_typing_indicator(wa_id)
                    except Exception as e:
                        logger.warning(f"Typing indicator failed: {e}")
            elif action_type and action_type.startswith('_internal_'):
                pass  # Skip internal commands
            else:
                logger.warning(f"Unknown action type: {action_type}")
        except Exception as e:
            logger.error(
                f"Error executing action {action_type}: {e}", exc_info=True
            )


# Alias for hanna compatibility
_clear_contact_flow_state = _clear_flow_state


def process_whatsapp_flow_response(msg_data: dict, contact: 'Contact', app_config=None) -> tuple:
    """
    Process WhatsApp Flow response messages (nfm_reply type).
    Updates the flow context with response data.
    Follows hanna's process_whatsapp_flow_response pattern.

    Args:
        msg_data: The message data from Meta webhook containing the flow response
        contact: The Contact instance who submitted the flow
        app_config: Optional MetaAppConfig instance

    Returns:
        tuple: (success: bool, notes: str)
    """
    from .models import WhatsAppFlow
    from .whatsapp_flow_response_processor import WhatsAppFlowResponseProcessor

    try:
        interactive_data = msg_data.get('interactive', {})
        nfm_reply = interactive_data.get('nfm_reply', {})
        response_json = nfm_reply.get('response_json')

        if not response_json:
            logger.warning(f"Flow response has no response_json: {msg_data}")
            return False, 'No response_json in flow response'

        try:
            response_data = (
                json.loads(response_json)
                if isinstance(response_json, str)
                else response_json
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse flow response JSON: {e}")
            return False, f'Invalid JSON: {e}'

        # Find matching WhatsApp flow
        filter_kwargs = {'is_active': True, 'sync_status': 'published'}
        if app_config:
            filter_kwargs['meta_app_config'] = app_config

        whatsapp_flows = WhatsAppFlow.objects.filter(**filter_kwargs)
        whatsapp_flow = whatsapp_flows.first()

        if not whatsapp_flow:
            logger.error("No active WhatsApp flow found to process response")
            return False, 'No matching WhatsApp flow found'

        # Call WhatsAppFlowResponseProcessor to update context only
        logger.info(f"Processing flow response for {whatsapp_flow.name}")
        result = WhatsAppFlowResponseProcessor.process_response(
            whatsapp_flow=whatsapp_flow,
            contact=contact,
            response_data=response_data,
        )

        if result and result.get('success'):
            logger.info("Successfully updated flow context for WhatsApp flow response.")
            # Note: Flow continuation will be triggered asynchronously by the calling code
            # via process_flow_for_message_task to ensure reliable transaction handling
            return True, 'Flow context updated with WhatsApp flow data.'
        else:
            error_note = result.get('notes') if result else 'Unknown error'
            logger.error(f"Flow response processing failed: {error_note}")
            return False, f'Flow processing failed: {error_note}'

    except Exception as e:
        logger.error(f"Error handling flow response: {e}", exc_info=True)
        return False, f'Exception processing flow: {str(e)[:200]}'


# ---------------------------------------------------------------------------
# WhatsApp Catalog order processing  (matches hanna pattern)
# ---------------------------------------------------------------------------

def process_order_from_catalog(
    msg_data: dict,
    contact: 'Contact',
) -> Tuple[bool, str]:
    """
    Process an incoming ``order`` message from the WhatsApp Commerce Catalog.

    WhatsApp sends this payload when a customer submits their cart:

        {
            "type": "order",
            "order": {
                "catalog_id": "...",
                "product_items": [
                    {
                        "product_retailer_id": "SKU-001",
                        "quantity": "2",
                        "item_price": "15000",
                        "currency": "USD"
                    }
                ],
                "text": "optional customer note"
            }
        }

    The function:
    1. Gets or creates a Customer record for the contact.
    2. Looks up each product by SKU (``product_retailer_id``).
    3. Creates an Order + OrderItems.
    4. Sends a confirmation message back to the customer.
    5. Sends a team notification about the new order.

    Returns (success: bool, notes: str).
    """
    import random
    from decimal import Decimal, InvalidOperation

    from customers.models import Customer
    from orders.models import Order, OrderItem
    from products.models import Product
    from meta_integration.utils import send_whatsapp_message

    order_data = msg_data.get('order', {})
    catalog_id = order_data.get('catalog_id', '')
    product_items = order_data.get('product_items', [])
    customer_note = order_data.get('text', '')

    if not product_items:
        logger.warning(
            f"process_order_from_catalog: No product_items in order "
            f"from {contact.phone_number}"
        )
        return False, 'No product items in order'

    try:
        # 1. Get or create Customer
        customer, _ = Customer.objects.get_or_create(
            phone_number=contact.phone_number,
            defaults={
                'full_name': contact.profile_name or contact.phone_number,
                'whatsapp_number': contact.phone_number,
            },
        )

        # 2. Resolve products by SKU
        skus = [
            item.get('product_retailer_id', '')
            for item in product_items
            if item.get('product_retailer_id')
        ]
        products_by_sku = {
            p.sku: p
            for p in Product.objects.filter(sku__in=skus)
        }

        # 3. Calculate totals and build line items
        line_items = []
        total_amount = Decimal('0')
        currency = 'USD'
        item_lines = []  # for the confirmation message

        for item in product_items:
            sku = item.get('product_retailer_id', '')
            try:
                qty = int(item.get('quantity', 1))
            except (ValueError, TypeError):
                qty = 1

            # Meta sends price in cents (minor currency units)
            try:
                raw_price = Decimal(str(item.get('item_price', '0')))
                unit_price = raw_price / Decimal('100')
            except (InvalidOperation, TypeError):
                unit_price = Decimal('0')

            currency = item.get('currency', 'USD')
            line_total = unit_price * qty
            total_amount += line_total

            product_obj = products_by_sku.get(sku)
            product_name = product_obj.name if product_obj else sku

            line_items.append({
                'product': product_obj,
                'sku': sku,
                'name': product_name,
                'quantity': qty,
                'unit_price': unit_price,
                'total_price': line_total,
            })
            item_lines.append(f"  • {product_name} × {qty} = ${line_total:.2f}")

        # 4. Generate unique order number
        order_number = f"WA-{random.randint(10000, 99999)}"
        while Order.objects.filter(order_number=order_number).exists():
            order_number = f"WA-{random.randint(10000, 99999)}"

        # 5. Create Order
        order = Order.objects.create(
            customer=customer,
            order_number=order_number,
            subtotal=total_amount,
            total_amount=total_amount,
            currency=currency,
            status='pending',
            payment_status='unpaid',
            customer_notes=(
                f"Order placed via WhatsApp Catalog.\n"
                f"Catalog ID: {catalog_id}\n"
                f"Customer Note: {customer_note}"
            ),
        )

        # 6. Create OrderItems
        for li in line_items:
            OrderItem.objects.create(
                order=order,
                product=li['product'] or Product.objects.filter(sku=li['sku']).first(),
                quantity=li['quantity'],
                unit_price=li['unit_price'],
                total_price=li['total_price'],
            )

        logger.info(
            f"Created catalog order {order_number} for "
            f"{contact.phone_number}: {len(line_items)} items, "
            f"total ${total_amount:.2f} {currency}"
        )

        # 7. Send confirmation message to customer
        items_text = '\n'.join(item_lines)
        confirmation = (
            f"🎉 *Thank you for your order!*\n\n"
            f"📦 *Order Number:* {order_number}\n"
            f"📋 *Items:*\n{items_text}\n\n"
            f"💰 *Total:* ${total_amount:.2f} {currency}\n\n"
            f"Our team will contact you shortly to confirm "
            f"payment and delivery details."
        )

        try:
            send_whatsapp_message(
                to_phone_number=contact.phone_number,
                message_type='text',
                data={'body': confirmation},
            )
        except Exception as exc:
            logger.error(
                f"Failed to send order confirmation to "
                f"{contact.phone_number}: {exc}"
            )

        # 8. Send payment method selection buttons
        try:
            payment_message = {
                "type": "button",
                "header": {"type": "text", "text": "💳 Select Payment Method"},
                "body": {
                    "text": (
                        f"How would you like to pay for order "
                        f"#{order_number}?\n\n"
                        f"Total: ${total_amount:.2f} {currency}"
                    )
                },
                "footer": {"text": "Choose your preferred payment option"},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"pay_paynow_{order_number}",
                                "title": "💰 Pay with Paynow",
                            },
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"pay_manual_{order_number}",
                                "title": "🏦 Manual Payment",
                            },
                        },
                    ]
                },
            }
            send_whatsapp_message(
                to_phone_number=contact.phone_number,
                message_type='interactive',
                data=payment_message,
            )
            logger.info(f"Sent payment method selection for order {order_number}")
        except Exception as exc:
            logger.warning(
                f"Could not send payment method selection: {exc}. "
                f"Order was still created successfully."
            )

        # 9. Notify team via notification system
        try:
            from notifications.tasks import send_notification_task

            notification_context = {
                'customer_name': customer.full_name,
                'customer_phone': contact.phone_number,
                'order_number': order_number,
                'items_summary': items_text,
                'total_amount': f"${total_amount:.2f} {currency}",
                'customer_note': customer_note or '(none)',
            }
            send_notification_task.delay(
                template_name='new_catalog_order',
                context=notification_context,
                group='sales_team',
            )
        except Exception as exc:
            # Notification failure should not block order creation
            logger.warning(f"Team notification failed for order {order_number}: {exc}")

        return True, f'Order {order_number} created with {len(line_items)} items'

    except Exception as exc:
        logger.error(
            f"process_order_from_catalog error for "
            f"{contact.phone_number}: {exc}",
            exc_info=True,
        )
        # Try to inform the customer
        try:
            send_whatsapp_message(
                to_phone_number=contact.phone_number,
                message_type='text',
                data={
                    'body': "Sorry, we couldn't process your order right now. "
                    "Please try again or contact us for assistance."
                },
            )
        except Exception:
            pass
        return False, f'Error: {str(exc)[:200]}'
