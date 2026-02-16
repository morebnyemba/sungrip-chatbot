"""Pydantic schemas for flows app validation.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Provides runtime validation for flow configurations and context data.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Dict, Any, Optional, List, Literal
import logging
import re
import ast

logger = logging.getLogger(__name__)


# ============================================================================
# Base Message Component Schemas
# ============================================================================

class TextContent(BaseModel):
    """Text message content."""
    body: str
    preview_url: bool = False

class MediaMessageContent(BaseModel):
    """Media message content (image, document, video, audio, sticker)."""
    model_config = ConfigDict(extra='allow')
    
    id: Optional[str] = None  # Media ID from WhatsApp
    link: Optional[str] = None  # URL to media
    caption: Optional[str] = None
    filename: Optional[str] = None  # Specific to documents

# Interactive Message Schemas
class InteractiveButton(BaseModel):
    """Interactive button."""
    type: Literal['reply'] = 'reply'
    reply: Dict[str, str]  # e.g., {"id": "unique-id", "title": "Click me"}

class InteractiveAction(BaseModel):
    """Interactive message action."""
    model_config = ConfigDict(extra='allow')
    
    buttons: Optional[List[InteractiveButton]] = None
    # For flow type
    name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

class InteractiveBody(BaseModel):
    """Interactive message body."""
    text: str

class InteractiveHeader(BaseModel):
    """Interactive message header."""
    type: Literal['text', 'video', 'image', 'document']
    text: Optional[str] = None

class InteractiveFooter(BaseModel):
    """Interactive message footer."""
    text: str

class InteractiveMessagePayload(BaseModel):
    """Complete interactive message payload."""
    type: Literal['button', 'list', 'flow']
    action: InteractiveAction
    body: InteractiveBody
    header: Optional[InteractiveHeader] = None
    footer: Optional[InteractiveFooter] = None

class LocationPayload(BaseModel):
    """Location message payload."""
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None

# ============================================================================
# Step Configuration Schemas (following hanna conventions)
# ============================================================================

class StepConfigSendMessage(BaseModel):
    """Configuration for send_message step - WhatsApp format only."""
    model_config = ConfigDict(extra='allow')
    
    message_type: Literal['text', 'image', 'document', 'audio', 'video', 'sticker', 'interactive', 'location']
    text: Optional[TextContent] = None
    image: Optional[MediaMessageContent] = None
    document: Optional[MediaMessageContent] = None
    audio: Optional[MediaMessageContent] = None
    video: Optional[MediaMessageContent] = None
    sticker: Optional[MediaMessageContent] = None
    interactive: Optional[InteractiveMessagePayload] = None
    location: Optional[LocationPayload] = None

class ReplyConfig(BaseModel):
    """Configuration for expected reply."""
    save_to_variable: str
    expected_type: Literal['text', 'email', 'number', 'interactive_id', 'image', 'location', 'nfm_reply'] = 'text'
    validation_regex: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None


class FallbackConfig(BaseModel):
    """Configuration for what happens when a user's reply is invalid."""
    model_config = ConfigDict(extra='allow')

    max_retries: int = Field(2, ge=0)
    re_prompt_message_text: Optional[str] = None
    action_after_retries: Optional[Literal['human_handover', 'end_flow', 'switch_flow']] = 'human_handover'
    config_after_retries: Optional[Dict[str, Any]] = None

class StepConfigQuestion(BaseModel):
    """Configuration for question step - WhatsApp format only."""
    model_config = ConfigDict(extra='allow')
    
    message_config: Dict[str, Any]  # Should validate against StepConfigSendMessage
    reply_config: ReplyConfig

class ActionItem(BaseModel):
    """Individual action item."""
    model_config = ConfigDict(extra='allow', protected_namespaces=())
    
    action_type: str
    # Common fields
    variable_name: Optional[str] = None
    value_template: Optional[Any] = None
    save_to_variable: Optional[str] = None
    params_template: Optional[Dict[str, Any]] = None
    # For model operations
    app_label: Optional[str] = None
    model_name: Optional[str] = None
    filters_template: Optional[Dict[str, Any]] = None
    fields_template: Optional[Dict[str, Any]] = None
    order_by: Optional[List[str]] = None
    fields_to_return: Optional[List[str]] = None
    limit: Optional[int] = None

class StepConfigAction(BaseModel):
    """Configuration for action step."""
    model_config = ConfigDict(extra='allow')
    
    actions_to_run: List[ActionItem]

class StepConfigSwitchFlow(BaseModel):
    """Configuration for switch_flow step."""
    model_config = ConfigDict(extra='allow')
    
    target_flow_name: str
    initial_context_template: Optional[Dict[str, Any]] = None

class StepConfigEndFlow(BaseModel):
    """Configuration for end_flow step."""
    model_config = ConfigDict(extra='allow')
    
    message_config: Optional[Dict[str, Any]] = None


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

# ============================================================================
# Step Config Union
# ============================================================================

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
                StepConfigSendMessage(**v)
            elif step_type == 'question':
                StepConfigQuestion(**v)
            elif step_type == 'wait_for_reply':
                WaitForReplyConfig(**v)
            elif step_type == 'trigger_flow':
                TriggerFlowConfig(**v)
            elif step_type == 'whatsapp_template':
                WhatsAppTemplateConfig(**v)
            elif step_type == 'webhook_call':
                WebhookCallConfig(**v)
            elif step_type == 'action':
                StepConfigAction(**v)
            elif step_type == 'switch_flow':
                StepConfigSwitchFlow(**v)
            elif step_type == 'end_flow':
                StepConfigEndFlow(**v)
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
        'user_reply_matches_keyword',
    ] = 'auto'
    condition: Optional[str] = None
    variable: Optional[str] = None
    variable_name: Optional[str] = None
    value: Optional[Any] = None
    expression: Optional[str] = None
    pattern: Optional[str] = None
    keyword: Optional[str] = None
    keywords: Optional[List[str]] = None
    match_type: Literal['exact', 'contains'] = 'contains'
    
    @field_validator('condition')
    @classmethod
    def validate_expression(cls, v, info):
        """Validate condition expression syntax."""
        if v is None:
            return v
        
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
    
    @field_validator('contact_phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v and not v.replace(' ', '').replace('+', '').isdigit():
            pass
        return v

# ============================================================================
# Validation Helper Functions
# ============================================================================

def validate_step_config(step_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate step configuration and return validated dict."""
    schema = StepConfigUnion(step_type=step_type, config=config)
    return schema.config


def validate_condition_config(condition_config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate condition configuration (for transitions)."""
    try:
        schema = ConditionConfig(**condition_config)
        return schema.model_dump(exclude_unset=True)
    except Exception as e:
        logger.error(f"Condition config validation failed: {str(e)}")
        raise ValueError(f"Invalid condition config: {str(e)}")


def validate_transition_config(transition_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate transition configuration.
    
    Auto-detects whether this is a condition config or full transition config.
    """
    has_condition_type = 'type' in transition_config
    has_target_step = 'target_step_id' in transition_config
    
    if has_condition_type and not has_target_step:
        # This is a condition config
        return validate_condition_config(transition_config)
    
    # This is a full transition config
    try:
        schema = TransitionConfigSchema(**transition_config)
        return schema.model_dump(exclude_unset=True)
    except Exception as e:
        logger.error(f"Transition config validation failed: {str(e)}")
        raise ValueError(f"Invalid transition config: {str(e)}")


def validate_context_data(context: Dict[str, Any]) -> Dict[str, Any]:
    """Validate flow session context data (permissive — allows extra keys)."""
    if not isinstance(context, dict):
        raise ValueError("Context data must be a dictionary")
    return context
