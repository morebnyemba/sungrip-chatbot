"""Pydantic schemas for flows app validation.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Provides runtime validation for flow configurations and context data.
"""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, field_validator, ConfigDict
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Step Configuration Schemas
# ============================================================================

class SendMessageConfig(BaseModel):
    """Configuration for send_message step."""

    model_config = ConfigDict(extra='allow')  # Allow extra fields for variables

    message: str  # Message text (supports {{variables}})
    media_url: Optional[str] = None
    quick_replies: Optional[List[str]] = None

    @field_validator('message')
    @classmethod
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("message cannot be empty")
        return v.strip()


class QuestionConfig(BaseModel):
    """Configuration for question step."""

    model_config = ConfigDict(extra='allow')

    question_text: str
    input_type: Literal['text', 'options', 'phone', 'email'] = 'text'
    options: Optional[List[str]] = None
    required: bool = True
    validation_pattern: Optional[str] = None  # Regex pattern for validation

    @field_validator('question_text')
    @classmethod
    def question_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("question_text cannot be empty")
        return v.strip()

    @field_validator('options')
    @classmethod
    def validate_options(cls, v, info):
        input_type = info.data.get('input_type')
        if input_type == 'options' and not v:
            raise ValueError("options required when input_type is 'options'")
        return v


class WaitForReplyConfig(BaseModel):
    """Configuration for wait_for_reply step."""

    model_config = ConfigDict(extra='allow')

    timeout_seconds: int = 300
    timeout_message: Optional[str] = None
    max_retries: int = 3


class TriggerFlowConfig(BaseModel):
    """Configuration for trigger_flow step."""

    model_config = ConfigDict(extra='allow')

    target_flow_id: int
    pass_context: bool = True


class WhatsAppTemplateConfig(BaseModel):
    """Configuration for whatsapp_template step."""

    model_config = ConfigDict(extra='allow')

    template_name: str
    template_language_code: str = 'en'
    parameters: Optional[Dict[str, str]] = None


class WebhookCallConfig(BaseModel):
    """Configuration for webhook_call step."""

    model_config = ConfigDict(extra='allow')

    webhook_url: str
    method: Literal['GET', 'POST', 'PUT', 'DELETE'] = 'POST'
    headers: Optional[Dict[str, str]] = None
    timeout_seconds: int = 30


class StepConfigUnion(BaseModel):
    """Union of all step configs - validates based on step_type."""

    model_config = ConfigDict(extra='allow')

    step_type: Literal[
        'send_message',
        'question',
        'wait_for_reply',
        'trigger_flow',
        'whatsapp_template',
        'webhook_call',
    ]
    config: Dict[str, Any]

    @field_validator('config', mode='before')
    @classmethod
    def validate_config_by_type(cls, v, info):
        """Validate config dictionary based on step_type."""
        step_type = info.data.get('step_type')

        if not isinstance(v, dict):
            raise ValueError("config must be a dictionary")

        try:
            if step_type == 'send_message':
                SendMessageConfig(**v)
            elif step_type == 'question':
                QuestionConfig(**v)
            elif step_type == 'wait_for_reply':
                WaitForReplyConfig(**v)
            elif step_type == 'trigger_flow':
                TriggerFlowConfig(**v)
            elif step_type == 'whatsapp_template':
                WhatsAppTemplateConfig(**v)
            elif step_type == 'webhook_call':
                WebhookCallConfig(**v)
        except Exception as e:
            logger.error(f"Config validation failed for {step_type}: {str(e)}")
            raise ValueError(f"Invalid config for step_type '{step_type}': {str(e)}")

        return v


# ============================================================================
# Transition Configuration Schemas
# ============================================================================

class ConditionConfig(BaseModel):
    """Configuration for transition condition."""

    model_config = ConfigDict(extra='allow')

    type: Literal[
        'auto',
        'condition_true',
        'condition_false',
        'user_reply_matches',
        'context_variable_equals',
    ] = 'auto'
    condition: Optional[str] = None  # Expression like "monthly_bill > 100"
    variable: Optional[str] = None  # Variable name for context checks
    value: Optional[Any] = None  # Expected value
    pattern: Optional[str] = None  # Regex pattern for reply matching
    keywords: Optional[List[str]] = None  # Keywords for reply matching
    match_type: Literal['exact', 'contains'] = 'contains'

    @field_validator('condition')
    @classmethod
    def validate_expression(cls, v, info):
        """Validate condition expression syntax."""
        if v is None:
            return v

        import ast
        try:
            ast.parse(v, mode='eval')
        except SyntaxError as e:
            raise ValueError(f"Invalid condition expression: {str(e)}")

        return v

    @field_validator('pattern')
    @classmethod
    def validate_regex(cls, v):
        """Validate regex pattern."""
        if v is None:
            return v

        import re
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {str(e)}")

        return v


class TransitionConfigSchema(BaseModel):
    """Configuration for flow transition."""

    model_config = ConfigDict(extra='allow')

    type: Literal['sequential', 'conditional', 'loop', 'end'] = 'sequential'
    target_step_id: Optional[int] = None
    condition_config: Optional[ConditionConfig] = None

    @field_validator('target_step_id')
    @classmethod
    def validate_target(cls, v, info):
        transition_type = info.data.get('type')
        if transition_type in ['sequential', 'conditional', 'loop'] and not v:
            raise ValueError(
                f"target_step_id required for transition type '{transition_type}'"
            )
        return v


# ============================================================================
# Flow Session Context Schemas
# ============================================================================

class FlowSessionContext(BaseModel):
    """Schema for flow session context data."""

    model_config = ConfigDict(extra='allow')

    # Standard fields
    contact_phone: Optional[str] = None
    contact_name: Optional[str] = None

    # Flow progress
    current_step_id: Optional[int] = None

    # Custom fields allowed (extra='allow')
    # These represent business context like monthly_bill, roof_type, etc.

    @field_validator('contact_phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v and not v.replace(' ', '').replace('+', '').isdigit():
            # Allow phone-like strings
            pass
        return v


# ============================================================================
# Factory Functions for Schema Validation
# ============================================================================


def validate_step_config(step_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate step configuration and return validated dict.

    Args:
        step_type: Type of step
        config: Configuration dictionary

    Returns:
        Validated configuration

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(config, dict):
        raise ValueError("config must be a dictionary")

    known_step_types = {
        'send_message',
        'question',
        'wait_for_reply',
        'trigger_flow',
        'whatsapp_template',
        'webhook_call',
    }

    # Pass through configs for extended step types not covered by the union schema
    if step_type not in known_step_types:
        return config

    try:
        schema = StepConfigUnion(step_type=step_type, config=config)
        return schema.config
    except Exception as e:
        logger.error(f"Step config validation failed: {str(e)}")
        raise ValueError(f"Invalid step config for type '{step_type}': {str(e)}")


def validate_transition_config(
    transition_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate transition configuration.

    Args:
        transition_config: Transition configuration dictionary

    Returns:
        Validated configuration

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(transition_config, dict):
        raise ValueError("Transition config must be a dictionary")

    condition_types = {'auto', 'condition_true', 'condition_false', 'user_reply_matches', 'context_variable_equals'}

    try:
        # If this already looks like a condition config (common in our flows), validate it directly.
        if 'condition_config' not in transition_config and (
            transition_config.get('type') in condition_types or 'type' not in transition_config
        ):
            condition = ConditionConfig(**transition_config)
            return condition.model_dump(exclude_unset=True)

        schema = TransitionConfigSchema(**transition_config)
        return schema.model_dump(exclude_unset=True)
    except Exception as e:
        logger.error(f"Transition config validation failed: {str(e)}")
        raise ValueError(f"Invalid transition config: {str(e)}")


def validate_context_data(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate flow session context data.

    Args:
        context: Context dictionary

    Returns:
        Validated context

    Raises:
        ValueError: If validation fails
    """
    try:
        schema = FlowSessionContext(**context)
        return schema.model_dump(exclude_unset=True)
    except Exception as e:
        logger.error(f"Context data validation failed: {str(e)}")
        raise ValueError(f"Invalid context data: {str(e)}")
