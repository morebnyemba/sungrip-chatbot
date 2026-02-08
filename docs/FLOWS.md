# Conversational Flows System

Complete guide to using the conversational flows system in the Sungrip chatbot.

## Overview

The flows system enables building complex, branching conversational experiences with:
- **Sequential steps** (send messages, ask questions, webhooks)
- **Conditional transitions** (based on user input, context, or expressions)
- **Context management** (collect and use data throughout flow)
- **WhatsApp Flows** (interactive forms for Meta's native flow UI)
- **Schema validation** (Pydantic-based config validation)
- **Safe expression evaluation** (AST-based condition evaluation)

## Architecture

### Core Models

#### Flow
Represents a complete conversational flow.

```python
Flow(
    name='solar_quote',                        # Unique identifier
    friendly_name='Solar Panel Quote',         # User-friendly name
    description='Guide users to get a quote',  # Help text
    is_active=True,                            # Enable/disable flow
    trigger_keywords=['quote', 'solar'],       # Keywords that trigger this flow
    trigger_config={}                          # Advanced trigger config
)
```

#### FlowStep
A single node/step in a flow.

```python
FlowStep(
    flow=flow,
    name='welcome_message',
    step_type='send_message',  # send_message, question, wait_for_reply, webhook_call, etc.
    config={
        'message': 'Welcome to our solar program! {{user_name}}',
        'media_url': 'https://example.com/image.jpg'
    },
    is_entry_point=True  # Set for first step
)
```

**Step Types:**

1. **send_message** - Send a text/media message to user
   ```python
   config = {
       'message': 'Static or {{variable}} text',
       'media_url': 'https://example.com/image.jpg',  # optional
       'quick_replies': ['Yes', 'No']  # optional
   }
   ```

2. **question** - Ask user a question and collect response
   ```python
   config = {
       'question_text': 'What is your roof type?',
       'input_type': 'options',  # text|options|phone|email
       'options': ['Asphalt', 'Tile', 'Metal'],
       'required': True,
       'validation_pattern': r'^\d+$'  # optional regex validation
   }
   ```

3. **wait_for_reply** - Wait for user to reply (timeout handling)
   ```python
   config = {
       'timeout_seconds': 300,
       'timeout_message': 'I did not hear from you...',
       'max_retries': 3
   }
   ```

4. **whatsapp_template** - Send a WhatsApp template message
   ```python
   config = {
       'template_name': 'solar_quote_template',
       'template_language_code': 'en',
       'parameters': {'user_name': 'John'}  # optional
   }
   ```

5. **webhook_call** - Call an external webhook
   ```python
   config = {
       'webhook_url': 'https://api.example.com/calculate',
       'method': 'POST',
       'headers': {'Authorization': 'Bearer token'},
       'timeout_seconds': 30
   }
   ```

6. **trigger_flow** - Trigger another flow
   ```python
   config = {
       'target_flow_id': 5,
       'pass_context': True  # Pass context to target flow
   }
   ```

#### FlowTransition
Defines how to move between steps.

```python
FlowTransition(
    current_step=step1,
    next_step=step2,
    condition_config={
        'type': 'auto',  # auto|condition_true|condition_false|user_reply_matches|context_variable_equals
        # Additional config depends on type
    },
    priority=0  # Order of evaluation for multiple transitions
)
```

**Transition Condition Types:**

1. **auto** - Always transition
   ```python
   {'type': 'auto'}
   ```

2. **condition_true/condition_false** - Based on expression evaluation
   ```python
   {'type': 'condition_true', 'condition': 'monthly_bill > 100'}
   ```

3. **user_reply_matches** - Check if user input matches pattern
   ```python
   {
       'type': 'user_reply_matches',
       'pattern': r'yes|ok|sure',  # Regex pattern
       'keywords': ['yes', 'ok'],   # OR simple keywords
       'match_type': 'contains'     # exact|contains
   }
   ```

4. **context_variable_equals** - Check context variable value
   ```python
   {
       'type': 'context_variable_equals',
       'variable': 'roof_type',
       'value': 'tile'
   }
   ```

#### FlowSession
Tracks an active flow session for a user.

```python
FlowSession(
    contact=contact,
    flow=flow,
    current_step=step,
    context_data={
        'user_name': 'John',
        'monthly_bill': 150,
        'roof_type': 'tile',
        'timestamp': '2024-01-15T10:30:00Z'
    },
    status='active'  # active|completed|abandoned|error
)
```

### WhatsApp Interactive Flows

For rich interactive experiences, use WhatsAppFlow models:

```python
WhatsAppFlow(
    name='solar_calculator',
    friendly_name='Solar Calculator',
    flow_json={...},  # Meta's flow JSON format
    sync_status='published',  # draft|syncing|published|deprecated|error
    meta_app_config=app_config,
    is_active=True
)
```

## Usage Guide

### 1. Create Flows Programmatically

```python
from flows.models import Flow, FlowStep, FlowTransition

# Create flow
flow = Flow.objects.create(
    name='quote_request',
    friendly_name='Request a Solar Quote',
    is_active=True,
    trigger_keywords=['quote', 'solar']
)

# Create steps
step1 = FlowStep.objects.create(
    flow=flow,
    name='welcome',
    step_type='send_message',
    config={'message': 'Welcome to Solar Quotes!'},
    is_entry_point=True
)

step2 = FlowStep.objects.create(
    flow=flow,
    name='ask_name',
    step_type='question',
    config={
        'question_text': 'What is your name?',
        'input_type': 'text'
    }
)

# Create transition
FlowTransition.objects.create(
    current_step=step1,
    next_step=step2,
    condition_config={'type': 'auto'}
)
```

### 2. Create Flows with Interactive CLI

Use the management command for quick flow creation:

```bash
# Interactive mode - wizard guides you through creation
python manage.py create_flow

# Quick mode with defaults
python manage.py create_flow --name=my_flow --auto

# Specify name upfront
python manage.py create_flow --name=solar_quote --friendly-name="Solar Quote Request"
```

**Example Interactive Session:**

```
🚀 Flow Creation Wizard

Flow name (unique identifier): solar_quote
Friendly name [Solar Quote]: Solar Quote Request
Description (optional): Guide users to get a solar quote

📍 Trigger Configuration
Trigger keywords (comma-separated): quote,solar,panel
Make flow active? [y/N]: y

✓ Created flow: Solar Quote Request

📝 Add Flow Steps

Add step #1? [Y/n]: y
Step 1 name: welcome
Step types:
  1. send_message - Send a text/media message
  2. question - Ask user a question
  3. wait_for_reply - Wait for user reply
  4. whatsapp_template - Send WhatsApp template
  5. webhook_call - Call external webhook
  6. trigger_flow - Trigger another flow
Step type (1-6): 1
Message text: Welcome! Let's get you a solar quote.
  ✓ Created step: welcome

Add step #2? [Y/n]: y
Step 2 name: ask_name
Step type (1-6): 2
Question text: What is your name?
Input type (text/options/phone/email) [text]: text
  ✓ Created step: ask_name

Add step #2? [Y/n]: n

🔀 Add Transitions

Auto-create sequential transitions? [Y/n]: y
  ✓ welcome → ask_name

🎉 Flow Created Successfully!

Name: solar_quote
Friendly Name: Solar Quote Request
Steps: 2
Active: True

View in admin: /admin/flows/flow/1/change/
API endpoint: /api/flows/flows/1/
```

### 3. Load Flow Definitions from Code

Define flows in `flows/definitions/solar_flows.py`:

```python
QUOTE_REQUEST_FLOW = {
    'name': 'quote_request',
    'friendly_name': 'Request a Solar Quote',
    'description': 'Guide users through getting a solar quote',
    'is_active': True,
    'trigger_keywords': ['quote', 'solar'],
    'trigger_config': {},
    'steps': [
        {
            'name': 'welcome',
            'step_type': 'send_message',
            'config': {'message': 'Welcome!'},
            'is_entry_point': True
        },
        {
            'name': 'ask_name',
            'step_type': 'question',
            'config': {
                'question_text': 'What is your name?',
                'input_type': 'text'
            }
        },
        # ... more steps
    ]
}
```

Load with management command:

```bash
# Load all definitions
python manage.py load_flow_definitions

# Load specific flow
python manage.py load_flow_definitions --flow=solar_flows

# Preview without saving
python manage.py load_flow_definitions --dry-run
```

### 4. Process Flows

```python
from flows.services import FlowProcessor

# Start a flow for a contact
processor = FlowProcessor.start_flow(contact, flow)

# Execute current step (send message, ask question, etc.)
processor.execute_current_step()

# Process user reply
processor.process_user_reply('yes, interested')

# Access session
print(processor.session.context_data)
```

### 5. Use REST API

```bash
# List flows
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/flows/flows/

# Start a session
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"contact": 1, "flow": 1}' \
  http://localhost:8000/api/flows/sessions/

# Get session context
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/flows/sessions/1/context/

# Move to next transition
curl -X POST -H "Authorization: Bearer <token>" \
  -d '{"action": "next"}' \
  http://localhost:8000/api/flows/sessions/1/next_step/
```

## Advanced Features

### Context Variables

Use `{{variable}}` syntax in configs to reference context data:

```python
config = {
    'message': 'Hello {{user_name}}, your monthly bill is ${{monthly_bill}}/month'
}
```

Supports nested access: `{{address.city}}`

### Conditional Expressions

Evaluate complex expressions in transitions:

```python
condition_config = {
    'type': 'condition_true',
    'condition': '(monthly_bill > 100 and roof_type == "tile") or has_shade == False'
}
```

Supported operators:
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Logical: `and`, `or`, `not`
- Membership: `in`, `not in`
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `**`

### Schema Validation

All step and transition configs are validated with Pydantic:

```python
from flows.schemas import validate_step_config

# Validates config structure and types
config = validate_step_config('question', {
    'question_text': 'How many panels?',
    'input_type': 'text'
})
# Raises ValueError if invalid
```

### WhatsApp Interactive Flows

Sync flows with Meta's API:

```bash
# Publish a flow to Meta
python manage.py sync_whatsapp_flows --action=publish --flow=123

# Validate flow JSON
python manage.py sync_whatsapp_flows --action=validate

# Sync all draft flows
python manage.py sync_whatsapp_flows --status=draft --action=publish
```

## Admin Interface

### Django Admin

Manage flows in Django admin at `/admin/flows/`:

- **Flows**: Create/edit flows with inline steps
- **Flow Steps**: Manage individual steps with config validation
- **Transitions**: Define step connections and conditions
- **Sessions**: Monitor active user sessions and context
- **WhatsApp Flows**: Manage interactive flows and sync status

### Features

- Inline editing of related models
- Real-time validation with helpful error messages
- Date hierarchy for sessions (organized by date)
- Filter by status, type, and date
- Search by name, phone number, etc.

## Testing

Run tests:

```bash
# All flow tests
python manage.py test flows.tests

# Specific test class
python manage.py test flows.tests.FlowProcessorTests

# With verbose output
python manage.py test flows.tests -v 2

# Coverage
coverage run --source='flows' manage.py test flows.tests
coverage report
```

## Monitoring

### Check Active Sessions

```python
from flows.models import FlowSession

# Get active sessions
active = FlowSession.objects.filter(status='active')

# Count by flow
from django.db.models import Count
sessions_by_flow = FlowSession.objects.values('flow__name').annotate(
    count=Count('id')
).filter(status='active')
```

### Error Handling

Sessions automatically marked as `error` if:
- Step execution raises exception
- Condition evaluation fails
- External webhook times out

Check error sessions:

```python
errors = FlowSession.objects.filter(status='error')
```

## Best Practices

1. **Always set entry point** - Mark the first step as `is_entry_point=True`

2. **Validate JSON configs** - Use Pydantic schemas or Django admin validation

3. **Use meaningful variable names** - `{{monthly_bill}}` instead of `{{var1}}`

4. **Test conditions** - Verify expressions with sample context data

5. **Handle timeouts** - Add `wait_for_reply` steps with proper timeout config

6. **Track important data** - Store calculated values in context for reporting

7. **Log transitions** - Use flow logs for debugging and analytics

8. **Secure webhooks** - Always use HTTPS and authentication for webhook calls

9. **Version flows** - Use version numbers to track changes

10. **Monitor conversations** - Check active sessions and error rates regularly

## Troubleshooting

### Issue: Condition always evaluates to False

**Solution**: Check variable names and types. Use the conditions test endpoint:

```bash
curl -X POST /api/flows/conditions/evaluate/ \
  -d '{"condition": "monthly_bill > 100", "context": {"monthly_bill": 150}}'
```

### Issue: Variables not replacing

**Solution**: Ensure variables match exactly (case-sensitive). Use {{variable_name}} format. Check context data exists.

### Issue: WhatsApp Flow not syncing

**Solution**: 
1. Verify Meta app credentials in MetaAppConfig
2. Check flow_json is valid (validate with Pydantic)
3. Review sync errors in admin UI
4. Run: `python manage.py sync_whatsapp_flows --flow=<id> --dry-run`

### Issue: Sessions getting stuck

**Solution**: Check for exceptions in server logs. Manually mark abandoned:

```python
from flows.models import FlowSession
from django.utils import timezone

session = FlowSession.objects.get(pk=1)
session.status = 'abandoned'
session.completed_at = timezone.now()
session.save()
```

## API Reference

See `/api/flows/` after running server for interactive API documentation.

### Endpoints

- `GET/POST /api/flows/flows/` - List/create flows
- `GET /api/flows/flows/<id>/` - Get flow details
- `POST /api/flows/flows/<id>/activate/` - Activate flow
- `POST /api/flows/flows/<id>/deactivate/` - Deactivate flow
- `GET /api/flows/flows/<id>/sessions/` - Get flow sessions
- `GET/POST /api/flows/sessions/` - Manage sessions
- `GET /api/flows/sessions/<id>/context/` - Get session context
- `POST /api/flows/sessions/<id>/abandon/` - Abandon session
- `GET/POST /api/flows/whatsapp-flows/` - Manage WhatsApp flows
- `POST /api/flows/whatsapp-flows/<id>/sync/` - Sync with Meta API

## Related Documentation

- [Flows Services](./flows_services.md) - Flow processor implementation
- [Schema Validation](./schemas.md) - Pydantic schemas
- [Meta Integration](../meta_integration/README.md) - WhatsApp API integration
- [API Documentation](../../docs/API.md) - Full API reference

## Contributing

To add new step types or conditions:

1. Add to `STEP_TYPE_CHOICES` in `Flow Step` model
2. Create Pydantic schema in `flows/schemas.py`
3. Implement handler in `FlowProcessor` class
4. Add tests to `flows/tests.py`
5. Document in README

## License

Part of Sungrip Chatbot. See LICENSE for details.
