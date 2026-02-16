# Flow Services Comparison: sungrip-chatbot vs hanna

## Architecture Comparison

### Current Implementation (sungrip-chatbot)
- **Approach**: Class-based (`FlowProcessor` class)
- **Model**: `FlowSession` for tracking flow state
- **Processing**: Method-based execution per step type
- **~738 lines**

### Hanna Implementation
- **Approach**: Function-based with helper functions
- **Model**: `ContactFlowState` for tracking flow state  
- **Processing**: Loop-based with fall-through step support
- **~1900+ lines** (much more comprehensive)

## Key Differences

### 1. **Main Entry Point**
**Ours**: Class instantiation + method calls
```python
processor = FlowProcessor(session)
processor.execute_current_step()
processor.process_user_reply(reply_text)
```

**Hanna**: Single function with transaction
```python
@transaction.atomic
def process_message_for_flow(contact: Contact, message_data: dict, incoming_message_obj: Message) -> List[Dict[str, Any]]
```

### 2. **Flow State Management**
**Ours**: `FlowSession` model
- `contact`, `flow`, `current_step`, `status`, `context_data`
- Status: active, completed, abandoned, error

**Hanna**: `ContactFlowState` model
- `contact`, `current_flow`, `current_step`, `flow_context_data`
- Simpler, focused on active state only
- Cleared when flow ends

### 3. **Step Execution Pattern**
**Ours**: Individual methods per step type
- `_execute_send_message()`
- `_execute_question()`
- `_execute_condition()`
- etc.

**Hanna**: Single unified function
- `_execute_step_actions(step, contact, flow_context, suppress_prompt=False)`
- Returns: `(actions_to_perform, updated_context)`
- Handles all step types in one function using Pydantic validation

### 4. **Processing Loop**
**Ours**: No automatic fall-through
- Each step execution stops
- Requires user interaction to continue

**Hanna**: Sophisticated while loop
```python
while True:
    # Execute current step
    # Evaluate transitions
    # If action/condition step, continue immediately (fall-through)
    # If question/wait step, break and wait for user
    # If end_flow/human_handover, break
```

### 5. **Transition Evaluation**
**Ours**: Simple condition types
- `auto`, `condition_true`, `condition_false`
- `user_reply_matches`, `context_variable_equals`

**Hanna**: Rich condition types
- `always_true`
- `whatsapp_flow_response_received`
- `nfm_response_field_equals`
- `user_reply_matches_keyword`
- `user_reply_matches_regex`
- `message_type_is`
- `variable_equals`
- `variable_exists`
- `variable_contains`
- `contact_is_admin`
- `question_reply_is_valid`

### 6. **Variable Resolution**
**Ours**: Simple regex replacement `{{variable}}`
```python
variables = re.findall(r'\{\{([\w\.]+)\}\}', config_str)
```

**Hanna**: Jinja2 template engine
```python
from jinja2 import Environment, StrictUndefined
template = jinja_env.from_string(template_str)
rendered = template.render(**context)
```

### 7. **Fallback Handling**
**Ours**: Simple error message on invalid input

**Hanna**: Sophisticated retry system
- Tracks `_fallback_count` in context
- Configurable `max_retries`
- Different messages per retry attempt
- Human handover after max retries
- Separate handling for question steps vs flow dead-ends

### 8. **Actions System**
**Ours**: Hardcoded action types
- `create_order`, `send_email`, `update_context`

**Hanna**: Action Registry Pattern
```python
from .actions import flow_action_registry

custom_action_func = flow_action_registry.get(action_type)
if custom_action_func:
    custom_actions = custom_action_func(contact, context, params)
```

### 9. **WhatsApp Integration**
**Ours**: Basic text messages only

**Hanna**: Full WhatsApp Flow support
- NFM (Native Flow Messages) integration
- Interactive lists and buttons
- Flow response processing
- `_handle_whatsapp_flow_response()`
- nfm_response_data parsing

### 10. **Performance Optimizations**
**Ours**: Basic queries

**Hanna**: Extensive optimizations
```python
prefetch_query = models.Prefetch(
    'current_step__outgoing_transitions',
    queryset=FlowTransition.objects.select_related('next_step').order_by('priority')
)
contact_flow_state = ContactFlowState.objects.select_related(
    'current_flow', 'current_step'
).prefetch_related(prefetch_query).filter(contact=contact).first()
```

### 11. **Flow Switching**
**Ours**: Simple flow switch, loses context
```python
def _execute_switch_flow(self, step: FlowStep):
    target_flow = Flow.objects.get(name=target_flow_name)
    self.session.status = 'completed'
    FlowProcessor.start_flow(target_flow, self.contact)
```

**Hanna**: Context-preserving switch
- Transfer context between flows
- Support for `simulated_trigger_keyword`
- `initial_context_template` configuration
- Internal command system: `_internal_command_switch_flow`

### 12. **Schema Validation**
**Ours**: Manual config parsing

**Hanna**: Pydantic schemas for everything
```python
from .schemas import (
    StepConfigSendMessage,
    StepConfigQuestion,
    StepConfigAction,
    StepConfigSwitchFlow,
    StepConfigEndFlow,
    StepConfigHumanHandover,
    FallbackConfig
)
```

### 13. **Return Values**
**Ours**: Direct side effects (sends messages immediately)

**Hanna**: Action queue pattern
```python
def process_message_for_flow(...) -> List[Dict[str, Any]]:
    actions_to_perform = []
    # ... processing ...
    actions_to_perform.append({
        'type': 'send_whatsapp_message',
        'recipient_wa_id': contact.whatsapp_id,
        'message_type': 'text',
        'data': {'body': resolved_msg}
    })
    return actions_to_perform
```

### 14. **Error Handling**
**Ours**: Try-catch per method, generic error message

**Hanna**: Comprehensive error handling
- Per-transition error catching (continues to next transition)
- State cleanup on critical errors: `_clear_contact_flow_state(contact, error=True)`
- Detailed logging with context
- Human handover as last resort fallback

### 15. **Internal Commands**
**Ours**: None

**Hanna**: Command system for flow control
- `_internal_command_clear_flow_state`
- `_internal_command_switch_flow`
- `_internal_fallthrough` message type
- Processed after main loop

## Critical Missing Features in Our Implementation

1. ❌ **Fall-through processing** - Action steps don't auto-continue
2. ❌ **Action registry** - Can't extend with custom actions
3. ❌ **WhatsApp Flow support** - No NFM integration
4. ❌ **Pydantic validation** - Manual config parsing prone to errors
5. ❌ **Fallback retry system** - No graceful degradation
6. ❌ **Jinja2 templates** - Limited variable resolution
7. ❌ **Performance optimizations** - N+1 query issues
8. ❌ **Context preservation** - Flow switches lose data
9. ❌ **Action queue pattern** - Immediate execution not testable
10. ❌ **Robust error handling** - Single failure breaks flow

## Recommendations

### Phase 1: Critical Alignment (Week 1)
1. Rename `FlowSession` → `ContactFlowState` (align models)
2. Change from class-based to function-based approach
3. Implement action queue pattern (return actions vs execute immediately)
4. Add Pydantic schemas for all step configs

### Phase 2: Core Features (Week 2)
5. Implement fall-through processing loop
6. Add fallback retry system with max_retries
7. Create action registry system
8. Add Jinja2 template support for variables

### Phase 3: Advanced Features (Week 3)
9. Add rich condition types (10+ types from hanna)
10. Implement context-preserving flow switching
11. Add performance optimizations (prefetch_related)
12. Implement internal command system

### Phase 4: WhatsApp Integration (Week 4)
13. Add WhatsApp Flow (NFM) support
14. Implement interactive list/button handling
15. Add flow response processing

## Code Structure Recommendation

```
flows/
├── services.py           # Main: process_message_for_flow()
├── actions.py            # FlowActionRegistry + custom actions
├── utils.py              # Jinja2 setup, helper functions
├── schemas.py            # Pydantic models (from hanna)
└── definitions/          # Flow definitions
    ├── solar_flows.py
    └── solar_quote_whatsapp_flow.py
```

## Conclusion

The hanna implementation is **production-grade** with 2+ years of battle-testing, while our current implementation is a **proof-of-concept**. We need significant work to reach feature parity. The most critical gaps are:

1. **Fall-through processing** - Breaks user experience
2. **Action registry** - Limits extensibility  
3. **Fallback handling** - Poor error recovery
4. **Pydantic validation** - Unreliable config parsing

Recommend: Follow hanna's architecture completely for consistency and maintainability.
