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
    """Configuration for send_message step.
    
    Supports both simple format and WhatsApp native format:
    - Simple: {"message": "Hello!"}
    - WhatsApp: {"message_type": "text", "text": {"body": "Hello!"}}
    """

    model_config = ConfigDict(extra='allow')  # Allow extra fields for variables

    # Simple format
    message: Optional[str] = None  # Message text (supports {{variables}})
    media_url: Optional[str] = None
    quick_replies: Optional[List[str]] = None
    
    # WhatsApp native format
    message_type: Optional[str] = None
    text: Optional[Dict[str, Any]] = None
    interactive: Optional[Dict[str, Any]] = None
    image: Optional[Dict[str, Any]] = None
    document: Optional[Dict[str, Any]] = None
    video: Optional[Dict[str, Any]] = None

    @field_validator('message')
    @classmethod
    def message_not_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("message cannot be empty")
        return v.strip() if v else v
    
    def model_post_init(self, __context):
        """Validate that at least one format is provided."""
        has_simple = self.message is not None
        has_whatsapp = self.message_type is not None and (
            self.text is not None or 
            self.interactive is not None or 
            self.image is not None or 
            self.document is not None or 
            self.video is not None
        )
        
        if not has_simple and not has_whatsapp:
            raise ValueError("Either 'message' or WhatsApp format (message_type + content) is required")


class QuestionConfig(BaseModel):
    """Configuration for question step.
    
    Supports both simple format and WhatsApp native format:
    - Simple: {"question_text": "What is your name?", "input_type": "text"}
    - WhatsApp: {"message_config": {"message_type": "text", "text": {"body": "..."}}, "reply_config": {...}}
    """

    model_config = ConfigDict(extra='allow')

    # Simple format
    question_text: Optional[str] = None
    input_type: Literal['text', 'options', 'phone', 'email'] = 'text'
    options: Optional[List[str]] = None
    required: bool = True
    validation_pattern: Optional[str] = None  # Regex pattern for validation
    
    # WhatsApp native format
    message_config: Optional[Dict[str, Any]] = None
    reply_config: Optional[Dict[str, Any]] = None

    @field_validator('question_text')
    @classmethod
    def question_not_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("question_text cannot be empty")
        return v.strip() if v else v

    def model_post_init(self, __context):
        """Validate that at least one format is provided and check options requirement."""
        has_simple = self.question_text is not None
        has_whatsapp = self.message_config is not None
        
        if not has_simple and not has_whatsapp:
            raise ValueError("Either 'question_text' or 'message_config' is required")
        
        # Check options requirement for simple format
        if has_simple and self.input_type == 'options' and not self.options:
            raise ValueError("options required when input_type is 'options'")


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


class ActionConfig(BaseModel):
    """Configuration for action step."""

    model_config = ConfigDict(extra='allow')

    action_type: str
    parameters: Optional[Dict[str, Any]] = None


class SwitchFlowConfig(BaseModel):
    """Configuration for switch_flow step."""

    model_config = ConfigDict(extra='allow')

    target_flow: str  # Flow name to switch to
    message: Optional[str] = None  # Optional message before switching


class EndFlowConfig(BaseModel):
    """Configuration for end_flow step."""

    model_config = ConfigDict(extra='allow')

    # end_flow typically has no required config, but allow extra fields


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
        'action',
        'switch_flow',
        'end_flow',
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
            elif step_type == 'action':
                ActionConfig(**v)
            elif step_type == 'switch_flow':
                SwitchFlowConfig(**v)
            elif step_type == 'end_flow':
                EndFlowConfig(**v)
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
        'always_true',
        'variable_exists',
        'whatsapp_flow_response_received',
        'interactive_reply_id_equals',
        'expression',
    ] = 'auto'
    condition: Optional[str] = None  # Expression like "monthly_bill > 100"
    variable: Optional[str] = None  # Variable name for context checks
    variable_name: Optional[str] = None  # Variable name for existence checks
    value: Optional[Any] = None  # Expected value
    expression: Optional[str] = None  # Python expression to evaluate
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
    schema = StepConfigUnion(step_type=step_type, config=config)
    return schema.config


def validate_condition_config(condition_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate condition configuration (for transitions).

    Args:
        condition_config: Condition configuration dictionary

    Returns:
        Validated configuration

    Raises:
        ValueError: If validation fails
    """
    try:
        schema = ConditionConfig(**condition_config)
        return schema.model_dump(exclude_unset=True)
    except Exception as e:
        logger.error(f"Condition config validation failed: {str(e)}")
        raise ValueError(f"Invalid condition config: {str(e)}")


def validate_transition_config(
    transition_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate transition configuration.

    This can validate either:
    1. A full transition config with type, target_step_id, and condition_config
    2. A condition config only (for backward compatibility)

    Args:
        transition_config: Transition configuration dictionary

    Returns:
        Validated configuration

    Raises:
        ValueError: If validation fails
    """
    # Check if this is a condition config (has 'type' but not 'target_step_id')
    # or a full transition config
    has_condition_type = 'type' in transition_config
    has_target_step = 'target_step_id' in transition_config
    
    if has_condition_type and not has_target_step:
        # This is a condition config, not a full transition config
        return validate_condition_config(transition_config)
    
    # This is a full transition config
    try:
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
