# Reference Repository Convention Alignment

## Overview

This document outlines how the Sungrip Solar Chatbot system has been restructured to follow the established conventions from the reference repositories (morebnyemba/hanna and morebnyemba/whatsappcrm).

## Key Changes Made

### 1. App Renaming: `whatsapp_integration` → `meta_integration`

**Rationale**: Both reference repos use `meta_integration` as the app name for WhatsApp Business API integration.

**Changes**:
- Renamed entire app directory
- Updated `apps.py`: `WhatsappIntegrationConfig` → `MetaAppConfigConfig`
- Updated `INSTALLED_APPS` in settings.py

### 2. Model Restructuring

#### MetaAppConfig (Previously WhatsAppConfig)

**New Fields Matching Reference Pattern**:
```python
name = CharField(unique=True)  # Descriptive name
verify_token = CharField()  # Webhook verification
access_token = TextField()  # API access token
app_secret = CharField()  # For signature verification
phone_number_id = CharField(unique=True)  # WhatsApp phone number ID
waba_id = CharField()  # WhatsApp Business Account ID
catalog_id = CharField()  # Optional catalog ID
api_version = CharField(default="v19.0")  # API version
is_active = BooleanField(default=False)  # Active status
```

**Custom Manager**:
```python
class MetaAppConfigManager(models.Manager):
    def get_active_config(self):
        """Get the single active configuration"""
        return self.get(is_active=True)
```

**Auto-deactivation Logic**:
```python
def save(self, *args, **kwargs):
    if self.is_active:
        # Deactivate all others
        MetaAppConfig.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
    super().save(*args, **kwargs)
```

#### WebhookEventLog (Previously WebhookLog)

**Enhanced Event Tracking**:
```python
EVENT_TYPE_CHOICES = [
    ('message', 'Message Received'),
    ('message_status', 'Message Status Update'),
    ('template_status', 'Message Template Status Update'),
    ('account_update', 'Account Update'),
    ('referral', 'Referral Event'),
    ('system', 'System Message'),
    ('flow_response', 'Flow Response'),
    ('security', 'Security Notification'),
    ('error', 'Error Notification'),
    ('unknown', 'Unknown Event Type'),
]
```

**New Fields**:
```python
event_identifier = CharField(db_index=True)  # e.g., wamid
app_config = ForeignKey(MetaAppConfig)  # Link to config
message = ForeignKey('conversations.Message')  # Link to message
waba_id_received = CharField()  # From webhook payload
phone_number_id_received = CharField()  # From webhook payload
payload_object_type = CharField()  # Object type from webhook
processing_status = CharField()  # pending, processed, error, ignored
processing_notes = TextField()  # Error messages, notes
```

### 3. New `flows` App

Following the exact pattern from reference repos for managing conversational flows.

#### Flow Model
```python
class Flow(models.Model):
    """Represents a complete conversational flow"""
    name = CharField(unique=True)
    friendly_name = CharField()
    description = TextField()
    is_active = BooleanField(default=False)
    trigger_keywords = JSONField(default=list)  # List of trigger words
    trigger_config = JSONField(default=dict)  # Advanced trigger config
```

**Example Usage**:
```python
# Solar Quote Request Flow
flow = Flow.objects.create(
    name="solar_quote_request",
    friendly_name="Solar Quote Request",
    description="Guides customers through solar system quote request",
    is_active=True,
    trigger_keywords=["quote", "price", "how much", "cost"]
)
```

#### FlowStep Model
```python
class FlowStep(models.Model):
    """Individual step in a conversational flow"""
    STEP_TYPE_CHOICES = [
        ('send_message', 'Send Message'),
        ('question', 'Ask Question'),
        ('condition', 'Conditional Branch'),
        ('action', 'Perform Action'),
        ('wait_for_reply', 'Wait for Reply'),
        ('end_flow', 'End Flow'),
        ('start_flow_node', 'Start Flow Node'),
        ('human_handover', 'Handover to Human Agent'),
        ('switch_flow', 'Switch to Another Flow'),
    ]
    
    flow = ForeignKey(Flow)
    name = CharField()
    step_type = CharField(choices=STEP_TYPE_CHOICES)
    config = JSONField(default=dict)  # Step-specific configuration
    is_entry_point = BooleanField(default=False)  # Flow entry point
```

**Example Usage**:
```python
# Welcome step
welcome_step = FlowStep.objects.create(
    flow=flow,
    name="Welcome Message",
    step_type="send_message",
    is_entry_point=True,
    config={
        "message_type": "text",
        "text": {
            "body": "Hello! I can help you get a quote for a solar system. May I know your average monthly electricity bill?"
        }
    }
)

# Question step
question_step = FlowStep.objects.create(
    flow=flow,
    name="Ask Monthly Bill",
    step_type="question",
    config={
        "message_config": {
            "message_type": "text",
            "text": {"body": "What is your average monthly electricity bill in USD?"}
        },
        "reply_config": {
            "expected_type": "number",
            "validation": {"min": 0, "max": 100000},
            "context_variable": "monthly_bill"
        }
    }
)
```

#### FlowTransition Model
```python
class FlowTransition(models.Model):
    """Defines transitions between flow steps"""
    current_step = ForeignKey(FlowStep, related_name='outgoing_transitions')
    next_step = ForeignKey(FlowStep, related_name='incoming_transitions')
    condition_config = JSONField(default=dict)  # Condition to trigger transition
    priority = IntegerField(default=0)  # Evaluation order
```

**Example Usage**:
```python
# Transition from welcome to question
FlowTransition.objects.create(
    current_step=welcome_step,
    next_step=question_step,
    condition_config={"type": "auto"},  # Automatic transition
    priority=1
)

# Conditional transition based on reply
FlowTransition.objects.create(
    current_step=question_step,
    next_step=calculate_system_step,
    condition_config={
        "type": "user_reply_matches",
        "pattern": "number",
        "min_value": 1
    },
    priority=1
)
```

#### FlowSession Model
```python
class FlowSession(models.Model):
    """Tracks active flow sessions for contacts"""
    contact = ForeignKey('conversations.Contact')
    flow = ForeignKey(Flow)
    current_step = ForeignKey(FlowStep, null=True)
    context_data = JSONField(default=dict)  # Session data
    status = CharField(choices=[...])  # active, completed, abandoned, error
    started_at = DateTimeField(auto_now_add=True)
    completed_at = DateTimeField(null=True)
```

**Context Data Example**:
```python
{
    "monthly_bill": 150,
    "system_size_kw": 5,
    "roof_type": "tile",
    "customer_name": "John Doe",
    "customer_phone": "+263771234567"
}
```

## Naming Conventions

### Field Names
- `waba_id` - WhatsApp Business Account ID (not `business_account_id`)
- `phone_number_id` - Phone Number ID (not `phone_id`)
- `catalog_id` - Catalog ID (not `catalogue_id`)
- `api_version` - API version (not `version`)
- `event_identifier` - Event identifier (not `event_id`)
- `trigger_keywords` - Trigger keywords list (not `triggers`)
- `context_data` - Session context (not `session_data`)

### Model Names
- `MetaAppConfig` (not `WhatsAppConfig`)
- `WebhookEventLog` (not `WebhookLog`)
- `FlowStep` (not `Step`)
- `FlowTransition` (not `Transition`)
- `FlowSession` (not `Session`)

### Method Names
- `get_active_config()` - Get active configuration
- `get_event_type_display()` - Get human-readable event type
- `clean()` - Model validation
- `save()` - Override with custom logic

## Admin Interface

All models have comprehensive Django admin configurations:

### MetaAppConfig Admin
- List display: name, phone_number_id, waba_id, api_version, is_active
- Fieldsets: Basic Info, Credentials, Authentication, Metadata
- Auto-handling of active status

### WebhookEventLog Admin
- List display: event_identifier, event_type, processing_status, received_at
- Filters: event_type, processing_status, app_config
- Read-only payload display
- No add permission (auto-created)

### Flow Admin
- Inline FlowStep management
- Trigger keyword configuration
- Active status management

### FlowStep Admin
- Inline FlowTransition management
- Step type selection
- JSON config editor

### FlowSession Admin
- Session tracking
- Context data display
- Status monitoring

## Integration Points

### 1. Webhook Handler (To Implement)
```python
# meta_integration/views.py
class MetaWebhookAPIView(View):
    def post(self, request):
        # 1. Parse webhook payload
        # 2. Find matching MetaAppConfig by phone_number_id
        # 3. Verify signature using app_secret
        # 4. Log to WebhookEventLog
        # 5. Process message/status update
        # 6. Trigger flow if needed
```

### 2. Flow Processing (To Implement)
```python
# flows/services.py
class FlowProcessor:
    def process_message(self, contact, message):
        # 1. Check for active FlowSession
        # 2. Evaluate current step
        # 3. Check transitions
        # 4. Execute next step
        # 5. Update session context
```

### 3. Message Sending (To Implement)
```python
# meta_integration/utils.py
def send_whatsapp_message(phone_number, message_config, config=None):
    # 1. Get active config if not provided
    # 2. Build WhatsApp API request
    # 3. Send via Meta Graph API
    # 4. Log response
```

## Benefits of This Structure

1. **Consistency**: Matches team's existing codebases
2. **Proven Patterns**: Uses battle-tested conventions
3. **Extensibility**: Easy to add new flow types and transitions
4. **Audit Trail**: Comprehensive logging of all webhook events
5. **Flexibility**: JSON configs allow dynamic flow definitions
6. **Maintainability**: Clear separation of concerns

## Migration Path

1. ✅ **Phase 1**: Rename apps and restructure models (COMPLETED)
2. **Phase 2**: Implement webhook views following reference pattern
3. **Phase 3**: Implement flow services and processors
4. **Phase 4**: Add Celery tasks for async processing
5. **Phase 5**: Create utility functions for WhatsApp API calls
6. **Phase 6**: Build flow definitions for solar business use cases

## Next Steps

1. Create `meta_integration/views.py` with webhook handler
2. Create `meta_integration/tasks.py` for background processing
3. Create `meta_integration/utils.py` for API utilities
4. Create `flows/services.py` for flow processing logic
5. Create sample flow definitions for solar inquiries
6. Update URL configurations
7. Run migrations

## Reference Files to Study

From morebnyemba/hanna:
- `whatsappcrm_backend/meta_integration/models.py` - Model patterns
- `whatsappcrm_backend/meta_integration/views.py` - Webhook handling
- `whatsappcrm_backend/flows/models.py` - Flow structure
- `whatsappcrm_backend/flows/services.py` - Flow processing

From morebnyemba/whatsappcrm:
- `whatsappcrm_backend/meta_integration/models.py` - Alternative patterns
- `whatsappcrm_backend/flows/*.py` - Flow examples
