# Hanna vs Sungrip-Chatbot: Detailed Comparison Report

## Overview

This report compares `morebnyemba/hanna` (reference implementation) with the local `sungrip-chatbot` repository across three key areas: **Session Expiry**, **WhatsApp UI Flows & Navigation**, and **Robust Information Handling**.

---

## 1. SESSION EXPIRY

### 1.1 Celery Beat Scheduled Cleanup Task

**Hanna has, Sungrip is MISSING:**

**Hanna** (`whatsappcrm_backend/flows/tasks.py`, lines 777–835):
```python
@shared_task(name="flows.cleanup_idle_conversations_task")
def cleanup_idle_conversations_task():
    idle_threshold = timezone.now() - timedelta(minutes=5)
    # Finds idle flow states AND idle AI-mode contacts
    idle_flow_states = ContactFlowState.objects.filter(
        last_updated_at__lt=idle_threshold
    ).select_related('contact', 'current_flow')
    idle_ai_contacts = Contact.objects.filter(
        conversation_mode__startswith='ai_',
        last_seen__lt=idle_threshold
    )
    # Clears flow state, resets AI mode, sends timeout notification
    for state in idle_flow_states:
        _clear_contact_flow_state(contact)
    for contact in idle_ai_contacts:
        contact.conversation_mode = 'flow'
        contact.conversation_context = {}
        contact.save(...)
    # Sends "session expired" message to each timed-out contact
    notification_text = "Your session has expired due to inactivity. Please send 'menu' to start over."
```

**Hanna** (`whatsappcrm_backend/whatsappcrm_backend/settings.py`, CELERY_BEAT_SCHEDULE):
```python
'cleanup-idle-conversations': {
    'task': 'flows.cleanup_idle_conversations_task',
    'schedule': crontab(minute='*/5'),  # Every 5 minutes
},
```

**Sungrip** has:
- `backend/flows/tasks.py` — **DOES NOT EXIST** (no file at all)
- `backend/sungrip_backend/settings.py` — **No `CELERY_BEAT_SCHEDULE`** defined anywhere
- No `cleanup_idle_conversations_task` or equivalent

**What sungrip needs to add:**
1. Create `backend/flows/tasks.py` with a `cleanup_idle_conversations_task` that:
   - Queries `FlowSession.objects.filter(status='active', updated_at__lt=idle_threshold)`
   - Sets sessions to `status='expired'` and `completed_at=timezone.now()`
   - Sends a notification message to the user
2. Add `CELERY_BEAT_SCHEDULE` to `backend/sungrip_backend/settings.py`:
   ```python
   from celery.schedules import crontab
   CELERY_BEAT_SCHEDULE = {
       'cleanup-idle-sessions': {
           'task': 'flows.tasks.cleanup_idle_sessions_task',
           'schedule': crontab(minute='*/5'),
       },
   }
   ```

### 1.2 `_clear_contact_flow_state` helper

**Hanna** (`whatsappcrm_backend/flows/services.py`, lines 338–348):
```python
def _clear_contact_flow_state(contact: Contact, error: bool = False):
    import traceback
    deleted_count, _ = ContactFlowState.objects.filter(contact=contact).delete()
    if deleted_count > 0:
        stack = ''.join(traceback.format_stack(limit=8))
        logger.info(f"Contact {contact.id}: Cleared flow state. Error: {error}. Stack:\n{stack}")
```
This helper is called in **14+ places** throughout hanna's `services.py` for session cleanup on: errors, end_flow, human_handover, switch_flow, exit keywords, and idle cleanup.

**Sungrip** has a different architecture using `FlowSession` model with `status` field (active/completed/abandoned/error). The equivalent is setting `session.status = 'abandoned'` or `'completed'`. Sungrip does this in `FlowProcessor.start_flow()` (line 80) and `_execute_end_flow()` (line 309). However:

**Gap:** Sungrip lacks the robust multi-point cleanup pattern. Hanna clears state at every possible exit point (14+ locations). Sungrip only clears at 2 locations.

### 1.3 Contact conversation_mode / conversation_context fields

**Hanna** uses `Contact.conversation_mode` (values: `'flow'`, `'ai_troubleshooting'`, `'ai_shopping'`) and `Contact.conversation_context` (JSON dict) to track whether a contact is in flow mode or AI mode.

**Sungrip** `Contact` model (in `conversations/models.py`) may not have these fields. The `FlowSession` model with `status` field serves a similar role but doesn't support AI conversation modes.

**What sungrip needs:** If AI conversation modes are desired, add `conversation_mode` and `conversation_context` fields to the `Contact` model.

---

## 2. WHATSAPP UI FLOWS AND NAVIGATION

### 2.1 WhatsApp Flow Service — Missing Features

**Hanna** (`whatsappcrm_backend/flows/whatsapp_flow_service.py`) has these methods that **Sungrip is missing**:

| Method | Hanna Lines | Sungrip | Gap |
|--------|-------------|---------|-----|
| `list_flows()` | Lines 42–75 | ❌ Missing | List all flows from Meta with pagination |
| `find_flow_by_name()` | Lines 77–95 | ❌ Missing | Find existing flow on Meta by name |
| `sync_flow()` | Lines 244–293 | ❌ Missing | Smart sync: finds existing or creates new |
| `update_flow_json()` retry logic | Lines 128–225 | ❌ Missing | Exponential backoff retry (3 attempts, 5/10/20s delay) for Meta error 139001/4016012 |
| `upload_flows_public_key()` | Lines 350–430 | ❌ Missing | Upload signing key with WABA + phone fallback |
| `create_flow_message_data()` | Lines 295–340 | ❌ Missing | Static helper for WhatsApp Flow interactive messages |
| `process_flow_response()` | Lines 342–370 | ❌ Missing | Create `WhatsAppFlowResponse` record |

**Specific code differences:**

**Hanna `update_flow_json` retry logic (lines 128–225):**
```python
def update_flow_json(self, whatsapp_flow, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, data=data, files=files, timeout=30)
            response.raise_for_status()
            ...
        except requests.exceptions.RequestException as e:
            error_obj = error_details.get('error', {})
            if error_obj.get('code') == 139001 and error_obj.get('error_subcode') == 4016012:
                is_retryable = True
            if is_retryable and attempt < max_retries - 1:
                delay = 5 * (2 ** attempt)  # Exponential backoff: 5s, 10s, 20s
                time.sleep(delay)
                continue
```

**Sungrip `update_flow_json` (lines 110–184):** No retry logic at all. Single attempt, fails immediately on error.

### 2.2 Flow Definitions — Scope Difference

**Hanna** has **28 flow definition files** covering:
- `main_menu_flow.py` — Conversational main menu
- `admin_main_menu_flow.py` — Admin menu
- `admin_add_order_flow.py`, `admin_update_order_status_flow.py`, `admin_update_assessment_status_flow.py`
- `solar_installation_flow.py` + `solar_installation_whatsapp_flow.py` (both conversational and WhatsApp Flow JSON)
- `solar_cleaning_flow.py` + `solar_cleaning_whatsapp_flow.py`
- `custom_furniture_installation_flow.py` + `custom_furniture_installation_whatsapp_flow.py`
- `hybrid_installation_flow.py` + `hybrid_installation_whatsapp_flow.py`
- `starlink_installation_flow.py` + `starlink_installation_whatsapp_flow.py`
- `site_inspection_flow.py` + `site_inspection_whatsapp_flow.py`
- `loan_application_flow.py` + `loan_application_whatsapp_flow.py`
- `warranty_claim_flow.py` + `warranty_claim_whatsapp_flow.py`
- `lead_gen_flow.py`, `simple_add_order_flow.py`, `payment_whatsapp_flow.py`
- `whatsapp_flow_converter.py` — Converts between conversational and WhatsApp Flow formats
- `load_notification_templates.py` — Notification template seeder

**Sungrip** has **5 flow definition files**:
- `solar_flows.py` — All conversational flows (main menu, quote, installation, packages, support) in a single file
- `solar_quote_whatsapp_flow.py` — WhatsApp Flow JSON for solar quotes
- `solar_packages_whatsapp_flow.py` — WhatsApp Flow JSON for solar packages
- `installation_scheduling_whatsapp_flow.py` — WhatsApp Flow JSON for installation scheduling
- `contact_support_whatsapp_flow.py` — WhatsApp Flow JSON for contact support

**Gaps:**
- No admin flows (admin menu, admin order management, admin assessment/warranty update)
- No `whatsapp_flow_converter.py` utility
- No notification template seeder
- No loan application, warranty claim, or site inspection flows
- All conversational flows in a single 1139-line file vs hanna's modular per-flow files

### 2.3 Interactive Message Handling in Webhook

**Hanna** (`meta_integration/views.py`, lines 374–460):
- Detects `nfm_reply` (WhatsApp Flow responses) → routes to `_handle_flow_response()`
- Detects `button_reply` → checks for payment-related buttons (`pay_*`, `paynow_*`) → routes to `_handle_payment_method_selection()`
- Detects `order` messages → routes to `_handle_order_message()`
- Creates `Message` object with `update_or_create` (idempotent for webhook retries)
- Queues `process_flow_for_message_task` via `transaction.on_commit()` (async, after DB commit)

**Sungrip** (`meta_integration/tasks.py`, lines 81–165, 245–347):
- Detects `nfm_reply` in `_process_flow_response()` but routes differently
- No payment button handling
- No order message handling
- Uses `Message.objects.create()` (not idempotent — fails on webhook retries with duplicate messages)
- Processes flow synchronously within the task, not via `transaction.on_commit()`

**What sungrip needs:**
1. Change `Message.objects.create()` to `Message.objects.update_or_create(whatsapp_message_id=message_id, defaults={...})` for idempotent message handling
2. Add `transaction.on_commit()` pattern for reliable async task dispatch

### 2.4 `process_message_for_flow` vs `FlowProcessor` Architecture

**Hanna** uses a single procedural function `process_message_for_flow()` (line 1285, ~700 lines) that:
- Handles location pin messages for pending requests
- Handles AI conversation mode exit keywords (`exit`, `menu`, `stop`, `quit`)
- Delegates to AI tasks (`handle_ai_conversation_task`, `handle_ai_shopping_task`)
- Handles `ORDER_RECEIVER_PHONE_ID` special case
- Runs a **while-True processing loop** with fall-through step execution
- Evaluates transitions with `_evaluate_transition_condition()` supporting:
  - `always_true`, `expression`, `keyword_match`, `regex_match`
  - `interactive_reply_id_equals` — for button/list interactive replies
  - `nfm_reply` detection and context merging
  - `variable_exists`, `variable_equals`, `variable_comparison`
  - `whatsapp_flow_response_received` — checks for flow data in context

**Sungrip** uses a class-based `FlowProcessor` (line 42, ~790 lines) that:
- Has `start_flow()`, `process_user_reply()`, `execute_current_step()`
- Evaluates transitions with `_evaluate_transition()` supporting:
  - `auto`, `always_true`, `condition_true`/`condition_false`
  - `user_reply_matches` (regex/keywords)
  - `context_variable_equals`, `variable_exists`
  - `whatsapp_flow_response_received`
  - `interactive_reply_id_equals`
  - `expression` — safe AST-based evaluation

**Gaps:**
- No location pin handling (hanna saves GPS coordinates to `SiteAssessmentRequest`/`InstallationRequest`)
- No AI conversation mode switching
- No `ORDER_RECEIVER_PHONE_ID` special routing
- No fall-through step processing loop (hanna processes action→action→question chains in one cycle)
- No `_trigger_new_flow()` function for keyword-based flow triggering from within message processing

### 2.5 WhatsApp Flow Response Processing

**Hanna** (`flows/whatsapp_flow_response_processor.py`):
- Has **15 specific flow response handlers** (e.g., `_handle_solar_installation_whatsapp`, `_handle_warranty_claim_whatsapp`, etc.)
- Each handler validates required fields, creates business entities (e.g., `InstallationRequest`), sends confirmation messages
- Handlers resume conversational flow for additional data collection (e.g., location pin) via `process_message_for_flow()`
- Queues admin notifications via `queue_notifications_to_users()`

**Sungrip** (`flows/whatsapp_flow_response_processor.py`):
- Has **1 generic `process_response()` method** that merges response data into flow session context
- No specific business entity creation
- No per-flow-type validation
- No admin notification queueing
- Triggers flow progression via `FlowProcessor.process_user_reply("__whatsapp_flow_response__")`

This is an appropriate design difference — Sungrip's generic approach is simpler and more extensible for new flow types. Hanna's approach is more coupled to specific business flows.

---

## 3. ROBUST INFORMATION HANDLING

### 3.1 Webhook Signature Verification

**Hanna** (`meta_integration/views.py`, lines 147–166):
```python
def _verify_signature(self, request_body_bytes, x_hub_signature_256, app_secret_key):
    if not x_hub_signature_256:
        return False
    if not app_secret_key:
        logger.error("App Secret not configured. Verification skipped (INSECURE).")
        return True  # Allows processing but logs security warning
    if not x_hub_signature_256.startswith('sha256='):
        return False
    expected = x_hub_signature_256.split('sha256=', 1)[1]
    calculated = hmac.new(app_secret_key.encode(), request_body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated, expected)
```

**Sungrip** (`meta_integration/services.py`, lines 241–263):
```python
@staticmethod
def verify_signature(payload, signature, app_secret):
    if not signature or not signature.startswith("sha256="):
        return False
    expected = signature.split("sha256=")[1]
    computed = hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected)
```

**Difference:** Both implement HMAC-SHA256 correctly. Sungrip's is slightly cleaner but hanna logs more detailed security warnings. Both use `hmac.compare_digest()` (timing-safe). ✅ No significant gap.

### 3.2 Webhook Event Logging

**Hanna** uses `WebhookEventLog.objects.update_or_create()` with `event_identifier` as the key:
```python
log_entry, created_log = WebhookEventLog.objects.update_or_create(
    event_identifier=wamid,
    app_config=target_config,
    defaults={...}
)
if created_log or log_entry.processing_status in ['pending', 'pending_reprocessing', 'error']:
    # Process the message
```
This is **idempotent** — Meta webhook retries don't create duplicate events.

**Sungrip** uses `WebhookEventLog.objects.create()`:
```python
webhook_log = WebhookEventLog.objects.create(
    event_identifier=event_identifier,
    ...
    processing_status="pending"
)
```
This is **NOT idempotent** — webhook retries create duplicate log entries and may process the same message multiple times.

**What sungrip needs:** Change to `update_or_create` with deduplication check.

### 3.3 Async Flow Processing via `transaction.on_commit()`

**Hanna** (`meta_integration/views.py`, line 449):
```python
transaction.on_commit(
    lambda: process_flow_for_message_task.delay(incoming_msg_obj.id)
)
```
This ensures the Celery task is dispatched **only after the database transaction commits**, preventing race conditions where the task runs before the message is saved.

**Sungrip** (`meta_integration/tasks.py`, line 125):
```python
process_webhook_event_task.delay(webhook_log.id)
```
Dispatches the task immediately, potentially before the transaction commits. This could cause `DoesNotExist` errors in the worker.

**What sungrip needs:** Wrap task dispatch in `transaction.on_commit()`.

### 3.4 Message Sending Task — Retry Logic and Sequential Delivery

**Hanna** (`meta_integration/tasks.py`, lines 19–155):
```python
@shared_task(bind=True, max_retries=10, default_retry_delay=3)
def send_whatsapp_message_task(self, outgoing_message_id, active_config_id):
    # Checks for preceding pending messages to ensure sequential delivery
    halting_message = Message.objects.filter(
        Q(contact=outgoing_msg.contact),
        Q(direction='out'),
        Q(id__lt=outgoing_msg.id),
        (Q(status='pending_dispatch', timestamp__gte=stale_pending_threshold) |
         Q(status='sent', status_timestamp__gte=stale_threshold))
    ).order_by('-id').first()
    if halting_message:
        raise self.retry()  # Wait for preceding message
```

**Sungrip** (`meta_integration/tasks.py`, lines 350–375):
```python
@shared_task
def send_message_task(phone_number, message_config, config_id=None):
    service = WhatsAppAPIService(config=config)
    result = service.send_message(phone_number, message_config)
```

**Gaps in sungrip:**
- No `bind=True`, no `max_retries`, no `default_retry_delay` — task fails permanently on first error
- No sequential delivery enforcement — messages may arrive out of order
- No idempotency check (`wamid` deduplication)
- No stale message timeout handling
- No `message_send_failed` signal for monitoring

### 3.5 Fallback Handling on Invalid User Input

**Hanna** (`flows/services.py`, lines 810–855):
```python
max_retries = fallback_config.max_retries
if fallback_config.action == 're_prompt' and current_fallback_count < max_retries:
    logger.info(f"Fallback: Re-prompting question step for contact")
    # Re-sends the question step message
elif fallback_config.action == 'go_to_step':
    # Navigates to a specific fallback step
```
Uses `FallbackConfig` Pydantic model with configurable `action`, `max_retries`, `fallback_message`.

**Sungrip** (`flows/services.py`, lines 404–411):
```python
except ValueError as e:
    logger.warning(f"Invalid reply: {str(e)}")
    send_text_message(
        self.contact.phone_number,
        f"Invalid input: {str(e)}. Please try again."
    )
```
Simple error message, no re-prompt counter, no configurable fallback, no `go_to_step` option.

### 3.6 Flow Action Registry

**Hanna** (`flows/actions.py`, 1700+ lines):
- 20+ registered actions including: payment initiation, order creation, inventory management, customer profile updates, AI conversation triggers, site assessment creation, warranty claim submission, notification dispatch
- Actions like `create_installation_request`, `submit_warranty_claim`, `initiate_paynow_payment`, `update_order_status`

**Sungrip** (`flows/actions.py`, 255 lines):
- 5 registered actions: `calculate_solar_quote`, `log_context_data`, `save_quote_request`, `update_context_variable`, `check_whatsapp_flow`

This is expected — Sungrip is a simpler solar-focused chatbot vs Hanna's full CRM platform.

### 3.7 `process_flow_for_message_task` — Message Dispatch Pattern

**Hanna** (`flows/tasks.py`, lines 34–88):
```python
@shared_task(queue='celery')
def process_flow_for_message_task(message_id):
    tasks_to_dispatch = []
    with transaction.atomic():
        actions = process_message_for_flow(contact, message_data, incoming_message)
        for action in actions:
            if action.get('type') == 'send_whatsapp_message':
                outgoing_msg = Message.objects.create(...)
                tasks_to_dispatch.append((outgoing_msg.id, config_id, dispatch_countdown))
                dispatch_countdown += 2  # 2-second stagger between messages
    # After transaction commits:
    for msg_id, config_id, countdown in tasks_to_dispatch:
        send_whatsapp_message_task.apply_async(args=[msg_id, config_id], countdown=countdown)
```

**Sungrip** has no equivalent — flow processing is done synchronously in `process_webhook_event_task` which directly calls `_trigger_flow_processing()`. Messages are sent synchronously during step execution.

**Gaps in sungrip:**
- No 2-second message staggering (prevents WhatsApp rate limiting)
- No separation between flow processing and message dispatch
- No `transaction.atomic()` wrapping flow processing
- No `apply_async` with countdown for message ordering

### 3.8 Error Handling in `_handle_error`

**Hanna:** Has extensive error handling throughout `process_message_for_flow()` with 5+ `_clear_contact_flow_state(contact, error=True)` calls at different error points, plus detailed logging with contact IDs and step names.

**Sungrip** (`flows/services.py`, lines 812–833):
```python
def _handle_error(self, error_message):
    self.session.status = 'error'
    self.session.context_data['error'] = error_message
    self.session.save()
    send_text_message(self.contact.phone_number,
        "Sorry, an error occurred. Please try again or contact support.")
```
Basic error handling — sets session to error state, sends generic message. No stack trace logging, no contact ID in logs.

---

## Summary of Critical Gaps

| # | Feature | Hanna | Sungrip | Priority |
|---|---------|-------|---------|----------|
| 1 | Session idle cleanup task | ✅ `cleanup_idle_conversations_task` every 5min | ❌ Missing entirely | **HIGH** |
| 2 | `CELERY_BEAT_SCHEDULE` | ✅ 8 scheduled tasks | ❌ None defined | **HIGH** |
| 3 | `update_flow_json` retry with backoff | ✅ 3 retries, exponential backoff | ❌ Single attempt | **MEDIUM** |
| 4 | `list_flows` / `find_flow_by_name` / `sync_flow` | ✅ Full Meta sync lifecycle | ❌ Missing | **MEDIUM** |
| 5 | Idempotent webhook processing (`update_or_create`) | ✅ Deduplicates events | ❌ Creates duplicates | **HIGH** |
| 6 | `transaction.on_commit()` for task dispatch | ✅ Prevents race conditions | ❌ Immediate dispatch | **MEDIUM** |
| 7 | Sequential message delivery enforcement | ✅ Checks preceding messages | ❌ No ordering | **MEDIUM** |
| 8 | Message staggering (countdown) | ✅ 2-second stagger | ❌ No stagger | **LOW** |
| 9 | `send_whatsapp_message_task` retry (10 retries) | ✅ Full retry with backoff | ❌ No retry | **HIGH** |
| 10 | Fallback/re-prompt on invalid input | ✅ Configurable retries + fallback step | ❌ Simple error message | **MEDIUM** |
| 11 | `upload_flows_public_key` | ✅ WABA + phone fallback | ❌ Missing | **LOW** |
| 12 | Per-flow-type response handlers | ✅ 15 specific handlers | ❌ 1 generic handler | **LOW** (design choice) |
| 13 | AI conversation mode support | ✅ Troubleshooting + Shopping | ❌ Not implemented | **LOW** (feature scope) |
| 14 | Location pin handling | ✅ GPS → SiteAssessment/Installation | ❌ Not implemented | **LOW** (feature scope) |
| 15 | Admin flows | ✅ 5 admin flow definitions | ❌ None | **LOW** (feature scope) |
