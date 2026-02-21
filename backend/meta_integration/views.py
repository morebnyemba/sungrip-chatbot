"""
Webhook views for meta_integration app.

Aligned with morebnyemba/hanna's meta_integration/views.py.
Processes incoming webhook events synchronously within the view (contact
creation, message creation, logging) and queues only flow processing
asynchronously via transaction.on_commit().
"""
import json
import logging
import hashlib
import hmac

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime
from django.db import transaction

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import MetaAppConfig, WebhookEventLog
from .serializers import (
    MetaAppConfigSerializer,
    WebhookEventLogSerializer,
    WebhookEventLogListSerializer,
)
from conversations.models import Message
from .tasks import send_read_receipt_task

logger = logging.getLogger('meta_integration')


# ---------------------------------------------------------------------------
# Helper: get active config (matches hanna)
# ---------------------------------------------------------------------------
def get_active_meta_config():
    try:
        return MetaAppConfig.objects.get_active_config()
    except MetaAppConfig.DoesNotExist:
        logger.critical("CRITICAL: No active Meta App Configuration found. Webhook and message sending will fail.")
        return None
    except MetaAppConfig.MultipleObjectsReturned:
        logger.critical("CRITICAL: Multiple active Meta App Configurations found. Please fix in Django Admin.")
        return None
    except Exception as e:
        logger.critical(f"CRITICAL: Error retrieving active MetaAppConfig: {e}", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Permission class (matches hanna)
# ---------------------------------------------------------------------------
class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


# ===========================================================================
# DRF ViewSets (matches hanna — provides admin management API)
# ===========================================================================
class MetaAppConfigViewSet(viewsets.ModelViewSet):
    """
    CRUD for MetaAppConfig.
    """
    queryset = MetaAppConfig.objects.all().order_by('-is_active', 'name')
    serializer_class = MetaAppConfigSerializer
    permission_classes = [IsAdminOrReadOnly]


class WebhookEventLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to webhook event logs for admin.
    """
    queryset = (
        WebhookEventLog.objects.all()
        .select_related('app_config', 'message__contact')
        .order_by('-received_at')
    )
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = [
        'event_type', 'processing_status', 'event_identifier',
        'phone_number_id_received', 'waba_id_received', 'app_config__name',
    ]
    search_fields = [
        'payload', 'processing_notes', 'event_identifier',
    ]
    ordering_fields = ['received_at', 'processed_at', 'event_type']

    def get_serializer_class(self):
        return WebhookEventLogListSerializer if self.action == 'list' else WebhookEventLogSerializer

    @action(detail=False, methods=['get'])
    def latest(self, request):
        count_str = request.query_params.get('count', '25')
        try:
            count = int(count_str)
            if not (0 < count <= 200):
                raise ValueError("Count must be between 1 and 200.")
        except ValueError as e:
            return Response({"error": f"Invalid 'count' parameter: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        latest_logs = self.filter_queryset(self.get_queryset())[:count]
        serializer = self.get_serializer(latest_logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reprocess(self, request, pk=None):
        log_entry = self.get_object()
        if log_entry.processing_status not in ['error', 'failed'] and not log_entry.event_type.startswith('message'):
            return Response(
                {"error": "Only 'message' events or events in 'error'/'failed' state can be reprocessed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        log_entry.processing_status = 'pending_reprocessing'
        log_entry.processing_notes = (log_entry.processing_notes or "") + \
            f"\nManually marked for reprocessing by {request.user} on {timezone.now().isoformat()}."
        log_entry.processed_at = None
        log_entry.save(update_fields=['processing_status', 'processing_notes', 'processed_at'])
        logger.info(f"WebhookEventLog {log_entry.id} marked for reprocessing by {request.user}.")
        return Response(
            {"message": f"Event {log_entry.id} marked for reprocessing."},
            status=status.HTTP_202_ACCEPTED,
        )


# ===========================================================================
# MetaWebhookAPIView (matches hanna — synchronous processing)
# ===========================================================================
@method_decorator(csrf_exempt, name='dispatch')
class MetaWebhookAPIView(View):
    """
    Handles incoming webhook events from Meta (Facebook/WhatsApp).

    GET — webhook verification challenge from Meta.
    POST — incoming events (messages, statuses, errors, etc.).

    All processing happens synchronously within @transaction.atomic;
    only flow-engine work is queued via transaction.on_commit().
    """

    # -----------------------------------------------------------------------
    # Signature verification (matches hanna)
    # -----------------------------------------------------------------------
    def _verify_signature(self, request_body_bytes, x_hub_signature_256, app_secret_key):
        if not x_hub_signature_256:
            logger.warning("Webhook signature (X-Hub-Signature-256) missing.")
            return False
        if not app_secret_key:
            logger.error("App Secret not configured for signature verification. Verification skipped (INSECURE).")
            return True  # Bypass but log warning

        if not x_hub_signature_256.startswith('sha256='):
            logger.warning("Webhook signature format is invalid (must start with 'sha256=').")
            return False
        expected_signature_hex = x_hub_signature_256.split('sha256=', 1)[1]
        byte_key = app_secret_key.encode('utf-8')
        hashed = hmac.new(byte_key, request_body_bytes, hashlib.sha256)
        calculated_signature_hex = hashed.hexdigest()

        if not hmac.compare_digest(calculated_signature_hex, expected_signature_hex):
            logger.warning(
                f"Webhook signature mismatch. "
                f"Expected: {expected_signature_hex}, Calculated: {calculated_signature_hex}"
            )
            return False
        logger.debug("Webhook signature verified successfully.")
        return True

    # -----------------------------------------------------------------------
    # Log helper (matches hanna)
    # -----------------------------------------------------------------------
    def _save_log(self, log_entry: WebhookEventLog, status_val: str, notes: str = None):
        old_status = log_entry.processing_status
        log_entry.processing_status = status_val
        if notes:
            log_entry.processing_notes = (
                f"{log_entry.processing_notes}\n{notes}"
                if log_entry.processing_notes
                else notes
            )
        log_entry.processed_at = timezone.now()
        try:
            log_entry.save(update_fields=['processing_status', 'processing_notes', 'processed_at'])
            logger.debug(f"WebhookEventLog ID {log_entry.id} status from '{old_status}' to '{status_val}'.")
        except Exception as e:
            logger.error(f"Failed to save WebhookEventLog (ID: {log_entry.pk or 'New'}): {e}", exc_info=True)

    # -----------------------------------------------------------------------
    # POST — main webhook receiver (matches hanna)
    # -----------------------------------------------------------------------
    @transaction.atomic
    def post(self, request: HttpRequest, *args, **kwargs):
        from conversations.models import Contact, Conversation

        logger.info("Webhook POST request received.")

        # 1. Decode payload
        raw_payload_str = request.body.decode('utf-8', errors='ignore')
        try:
            payload = json.loads(raw_payload_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {e}. Body: {raw_payload_str[:500]}...")
            WebhookEventLog.objects.create(
                app_config=None, event_type='error',
                payload={'error': 'Invalid JSON', 'body_snippet': raw_payload_str[:500], 'exception': str(e)},
                processing_status='error', processing_notes='Failed to parse JSON.',
            )
            return HttpResponse("Invalid JSON payload", status=400)

        # 2. Determine config from phone_number_id in payload
        target_config = None
        phone_id_from_payload = None
        try:
            phone_id_from_payload = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
                .get("metadata", {})
                .get("phone_number_id")
            )
            if phone_id_from_payload:
                target_config = MetaAppConfig.objects.get(phone_number_id=phone_id_from_payload)
            else:
                logger.warning("Could not find phone_number_id in webhook payload. Falling back to active config.")
                target_config = get_active_meta_config()
        except MetaAppConfig.DoesNotExist:
            logger.error(f"No MetaAppConfig found for phone_number_id '{phone_id_from_payload}'.")
            WebhookEventLog.objects.create(
                app_config=None, event_type='security',
                phone_number_id_received=phone_id_from_payload,
                payload=payload, processing_status='rejected',
                processing_notes=f"No config found for phone_number_id {phone_id_from_payload}.",
            )
            return HttpResponse("EVENT_RECEIVED_BUT_UNCONFIGURED", status=200)
        except (IndexError, KeyError, AttributeError):
            logger.warning("Could not extract phone_number_id from payload structure. Falling back to active config.")
            target_config = get_active_meta_config()

        if not target_config:
            logger.error("No matching or active MetaAppConfig. Event ignored.")
            return HttpResponse("EVENT_RECEIVED_BUT_UNCONFIGURED", status=200)

        logger.info(f"Processing webhook for config: '{target_config.name}' (Phone ID: {target_config.phone_number_id})")

        # 3. Verify signature
        app_secret = target_config.app_secret
        if not app_secret:
            logger.warning(f"App Secret not configured for '{target_config.name}'. Signature verification SKIPPED.")
        elif not self._verify_signature(request.body, request.headers.get('X-Hub-Signature-256'), app_secret):
            logger.error("Webhook signature verification FAILED. Discarding request.")
            WebhookEventLog.objects.create(
                app_config=target_config, event_type='security',
                payload={'error': 'Signature verification failed', 'headers': dict(request.headers)},
                processing_status='rejected', processing_notes='Invalid X-Hub-Signature-256',
            )
            return HttpResponse("Invalid signature", status=403)

        log_entry = None
        base_log_defaults = {
            'app_config': target_config,
            'payload_object_type': payload.get("object"),
        }

        try:
            if payload.get("object") == "whatsapp_business_account":
                for entry_idx, entry in enumerate(payload.get("entry", [])):
                    waba_id = entry.get("id")
                    for change_idx, change in enumerate(entry.get("changes", [])):
                        value = change.get("value", {})
                        field = change.get("field")
                        metadata = value.get("metadata", {})
                        phone_id = metadata.get("phone_number_id")

                        logger.info(
                            f"Processing entry[{entry_idx}].change[{change_idx}]: "
                            f"field='{field}', phone_id='{phone_id}'"
                        )

                        log_defaults_for_change = {
                            **base_log_defaults,
                            'waba_id_received': waba_id,
                            'phone_number_id_received': phone_id,
                        }

                        if field == "messages":
                            # --- Messages ---
                            if "messages" in value:
                                for msg_data in value["messages"]:
                                    wamid = msg_data.get("id")
                                    log_entry, created_log = WebhookEventLog.objects.update_or_create(
                                        event_identifier=wamid,
                                        app_config=target_config,
                                        defaults={
                                            'payload_object_type': payload.get("object"),
                                            'waba_id_received': waba_id,
                                            'phone_number_id_received': phone_id,
                                            'event_type': f"message_{msg_data.get('type', 'unknown')}",
                                            'payload': msg_data,
                                            'processing_status': 'pending',
                                        },
                                    )
                                    if created_log or log_entry.processing_status in ['pending', 'pending_reprocessing', 'error']:
                                        contact_wa_id = msg_data.get("from")
                                        profile_name = (
                                            value.get("contacts", [{}])[0]
                                            .get("profile", {})
                                            .get("name", "Unknown")
                                        )
                                        contact, _ = Contact.objects.get_or_create(
                                            whatsapp_id=contact_wa_id,
                                            defaults={
                                                'phone_number': contact_wa_id,
                                                'profile_name': profile_name,
                                            },
                                        )
                                        self._handle_message(msg_data, metadata, value, target_config, log_entry, contact)
                                    else:
                                        logger.info(f"Skipping already processed WebhookEventLog for WAMID: {wamid}")

                            # --- Statuses ---
                            elif "statuses" in value:
                                for status_data in value["statuses"]:
                                    wamid = status_data.get("id")
                                    status_val = status_data.get("status")
                                    status_identifier = f"{wamid}_{status_val}"
                                    log_entry, _ = WebhookEventLog.objects.update_or_create(
                                        event_identifier=status_identifier,
                                        app_config=target_config,
                                        defaults={
                                            'event_type': 'message_status',
                                            **log_defaults_for_change,
                                            'payload': status_data,
                                            'processing_status': 'pending',
                                        },
                                    )
                                    self.handle_status_update(status_data, metadata, target_config, log_entry)

                            # --- Errors ---
                            elif "errors" in value:
                                for error_data in value["errors"]:
                                    error_code = error_data.get('code')
                                    log_id = f"error_{error_code}_{timezone.now().timestamp()}"
                                    log_entry, _ = WebhookEventLog.objects.update_or_create(
                                        event_identifier=log_id,
                                        app_config=target_config,
                                        event_type='error',
                                        defaults={**log_defaults_for_change, 'payload': error_data, 'processing_status': 'pending'},
                                    )
                                    self.handle_error_notification(error_data, metadata, target_config, log_entry)
                            else:
                                logger.warning(f"Change field is 'messages' but no 'messages' or 'statuses' key. Keys: {value.keys()}")

                        elif field == "account_update":
                            log_entry, _ = WebhookEventLog.objects.update_or_create(
                                event_identifier=f"{field}_{value.get('event', 'unknown')}_{entry.get('id', 'unknown')}_{timezone.now().timestamp()}",
                                app_config=target_config,
                                event_type='account_update',
                                defaults={**log_defaults_for_change, 'payload': value, 'processing_status': 'pending'},
                            )
                            self.handle_account_update(value, metadata, target_config, log_entry)

                        elif field == "message_template_status_update":
                            log_entry, _ = WebhookEventLog.objects.update_or_create(
                                event_identifier=f"{field}_{value.get('message_template_id')}_{value.get('event')}",
                                app_config=target_config,
                                event_type='template_status',
                                defaults={**log_defaults_for_change, 'payload': value, 'processing_status': 'pending'},
                            )
                            self.handle_template_status_update(value, metadata, target_config, log_entry)

                        else:
                            generic_event_id = f"{field}_{entry.get('id', 'unknown')}_{change_idx}_{timezone.now().timestamp()}"
                            log_entry, _ = WebhookEventLog.objects.update_or_create(
                                event_identifier=generic_event_id,
                                app_config=target_config,
                                event_type=field or 'unknown',
                                defaults={**log_defaults_for_change, 'payload': value, 'processing_status': 'pending'},
                            )
                            logger.warning(f"Unhandled change field '{field}'. Logged with ID {log_entry.id}")
                            self._save_log(log_entry, 'ignored', f"Unhandled field: {field}")

            else:
                # Non-whatsapp_business_account object types
                generic_event_id = f"{payload.get('object', 'unknown_object')}_{timezone.now().timestamp()}"
                log_entry, _ = WebhookEventLog.objects.update_or_create(
                    event_identifier=generic_event_id,
                    app_config=target_config,
                    defaults={**base_log_defaults, 'payload': payload, 'processing_status': 'pending'},
                )
                logger.warning(f"Received webhook for unhandled object type: {payload.get('object')}")
                self._save_log(log_entry, 'ignored', f"Unhandled object: {payload.get('object')}")

            return HttpResponse("EVENT_RECEIVED", status=200)

        except Exception as e:
            logger.error(f"General error processing webhook: {e}", exc_info=True)
            current_payload_for_log = payload if 'payload' in locals() else {
                'raw_error_body': raw_payload_str,
                'exception_point': 'general_processing',
            }
            if log_entry and log_entry.pk:
                self._save_log(log_entry, 'failed', f"General processing error: {str(e)[:250]}")
            else:
                WebhookEventLog.objects.create(
                    **base_log_defaults,
                    event_identifier=f"error_{timezone.now().timestamp()}",
                    processing_status='failed',
                    payload=current_payload_for_log,
                    event_type='error',
                    processing_notes=f"General processing error: {str(e)[:250]}",
                )
            return HttpResponse("Internal Server Error processing event.", status=500)

    # -----------------------------------------------------------------------
    # _handle_message — processes an individual incoming message (matches hanna)
    # -----------------------------------------------------------------------
    @transaction.atomic
    def _handle_message(self, msg_data: dict, metadata: dict, value_entry: dict,
                        active_config: MetaAppConfig, log_entry: WebhookEventLog, contact):
        from conversations.models import Contact, Conversation
        from flows.tasks import process_flow_for_message_task

        whatsapp_message_id = msg_data.get("id")
        message_type = msg_data.get("type", "unknown")

        logger.info(
            f"Handling message WAMID: {whatsapp_message_id} for Contact "
            f"{contact.whatsapp_id}, Type: {message_type}."
        )

        # Check if this is a flow response (nfm_reply)
        if message_type == "interactive" and msg_data.get("interactive", {}).get("type") == "nfm_reply":
            self._handle_flow_response(msg_data, contact, active_config, log_entry)
            return

        # Check if this is an ORDER message from WhatsApp Commerce Catalog
        # (matches hanna pattern — orders are handled outside the flow engine)
        if message_type == "order":
            self._handle_order_message(msg_data, contact, active_config, log_entry)
            return

        # Parse message timestamp
        message_timestamp_str = msg_data.get("timestamp")
        message_timestamp = None
        if message_timestamp_str:
            try:
                message_timestamp = timezone.make_aware(datetime.fromtimestamp(int(message_timestamp_str)))
            except ValueError:
                logger.warning(f"Could not parse message timestamp: {message_timestamp_str}")
        if not message_timestamp:
            message_timestamp = timezone.now()

        # Get or create conversation
        conversation = Conversation.objects.filter(contact=contact, status='active').first()
        if not conversation:
            conversation = Conversation.objects.create(
                contact=contact,
                title=f"Chat with {contact.profile_name or contact.phone_number}",
                status='active',
            )

        # Create/update message record (matches hanna's update_or_create on wamid)
        incoming_msg_obj, msg_created = Message.objects.update_or_create(
            message_id=whatsapp_message_id,
            defaults={
                'contact': contact,
                'conversation': conversation,
                'app_config': active_config,
                'direction': 'inbound',
                'message_type': message_type,
                'content_payload': msg_data,
                'content': self._extract_content_text(msg_data, message_type),
                'interactive_data': msg_data.get('interactive') if message_type == 'interactive' else None,
                'media_id': msg_data.get(message_type, {}).get('id', '') if message_type in ('image', 'video', 'audio', 'document') else '',
                'location_latitude': msg_data.get('location', {}).get('latitude') if message_type == 'location' else None,
                'location_longitude': msg_data.get('location', {}).get('longitude') if message_type == 'location' else None,
                'location_name': msg_data.get('location', {}).get('name', '') if message_type == 'location' else '',
                'location_address': msg_data.get('location', {}).get('address', '') if message_type == 'location' else '',
                'timestamp': message_timestamp,
                'status': 'received',
                'status_timestamp': message_timestamp,
            },
        )

        if not msg_created:
            logger.info(f"Message WAMID {whatsapp_message_id} already exists. Updated payload.")
        else:
            logger.info(f"Saved incoming message (WAMID: {whatsapp_message_id}) as DB ID {incoming_msg_obj.id}")

        # Link log to message
        if log_entry and log_entry.pk:
            log_entry.message = incoming_msg_obj
            log_entry.processing_status = 'processing_queued'
            log_entry.save(update_fields=['message', 'processing_status'])

        try:
            # Queue flow processing via transaction.on_commit (matches hanna)
            transaction.on_commit(
                lambda: process_flow_for_message_task.delay(incoming_msg_obj.id)
            )
            logger.info(f"Queued process_flow_for_message_task for message {incoming_msg_obj.id}.")
        except Exception as e:
            logger.error(
                f"Unhandled exception in _handle_message for WAMID {whatsapp_message_id}: {e}",
                exc_info=True,
            )
            if log_entry and log_entry.pk:
                self._save_log(log_entry, 'failed', f"Critical error before queueing flow: {str(e)[:200]}")

        # Send read receipt
        self._send_read_receipt(whatsapp_message_id, active_config)

    # -----------------------------------------------------------------------
    # _handle_order_message — WhatsApp Commerce Catalog orders (matches hanna)
    # -----------------------------------------------------------------------
    def _handle_order_message(self, msg_data: dict, contact, active_config: MetaAppConfig, log_entry: WebhookEventLog):
        """
        Handle incoming ``order`` messages from the WhatsApp Commerce Catalog.

        When a customer browses the native WhatsApp catalog, adds items to
        their cart, and taps "Send", WhatsApp delivers a message with
        type="order".  This method:
        1. Calls ``process_order_from_catalog`` to create Order + OrderItems.
        2. Starts the ``order_delivery_info`` flow to collect recipient /
           address / location details.
        """
        from flows.services import process_order_from_catalog
        from flows.models import Flow, FlowStep, FlowSession
        from flows.tasks import process_flow_continuation_task
        from conversations.models import Conversation

        whatsapp_message_id = msg_data.get("id")

        logger.info(
            f"Processing catalog order from {contact.phone_number} "
            f"(WAMID: {whatsapp_message_id})"
        )

        # Parse timestamp
        message_timestamp_str = msg_data.get("timestamp")
        message_timestamp = None
        if message_timestamp_str:
            try:
                message_timestamp = timezone.make_aware(
                    datetime.fromtimestamp(int(message_timestamp_str))
                )
            except ValueError:
                pass
        if not message_timestamp:
            message_timestamp = timezone.now()

        # Store the order message in the conversation log
        conversation = Conversation.objects.filter(
            contact=contact, status='active'
        ).first()
        if not conversation:
            conversation = Conversation.objects.create(
                contact=contact,
                title=f"Chat with {contact.profile_name or contact.phone_number}",
                status='active',
            )

        # Summarize order items for the message content
        items = msg_data.get('order', {}).get('product_items', [])
        content_text = f"[Catalog Order: {len(items)} item(s)]"

        Message.objects.update_or_create(
            message_id=whatsapp_message_id,
            defaults={
                'contact': contact,
                'conversation': conversation,
                'app_config': active_config,
                'direction': 'inbound',
                'message_type': 'order',
                'content_payload': msg_data,
                'content': content_text,
                'timestamp': message_timestamp,
                'status': 'received',
                'status_timestamp': message_timestamp,
            },
        )

        # Process the order (creates DB records)
        success, notes, order_context = process_order_from_catalog(msg_data, contact)

        if log_entry and log_entry.pk:
            self._save_log(
                log_entry,
                'processed' if success else 'failed',
                notes,
            )

        # If order was created successfully, start the delivery-info flow
        # so the user is prompted for recipient / address / location.
        if success and order_context:
            try:
                delivery_flow = Flow.objects.filter(
                    name='order_delivery_info', is_active=True
                ).first()
                if delivery_flow:
                    entry_step = FlowStep.objects.filter(
                        flow=delivery_flow, is_entry_point=True
                    ).first()
                    if entry_step:
                        # End any active sessions first
                        FlowSession.objects.filter(
                            contact=contact, status='active'
                        ).update(
                            status='completed',
                            completed_at=timezone.now(),
                        )
                        FlowSession.objects.create(
                            contact=contact,
                            flow=delivery_flow,
                            current_step=entry_step,
                            status='active',
                            context_data=order_context,
                        )
                        # Trigger the flow engine to execute the entry step
                        # and send the first question to the user.
                        transaction.on_commit(
                            lambda: process_flow_continuation_task.delay(
                                contact.id,
                                {'type': 'internal_flow_start'},
                            )
                        )
                        logger.info(
                            f"Started order_delivery_info flow for "
                            f"order {order_context.get('order_number')}"
                        )
                    else:
                        logger.error("order_delivery_info flow has no entry point")
                else:
                    logger.warning(
                        "order_delivery_info flow not found or inactive. "
                        "Skipping delivery info collection."
                    )
            except Exception as exc:
                logger.error(
                    f"Failed to start delivery info flow: {exc}",
                    exc_info=True,
                )

        # Send read receipt
        self._send_read_receipt(whatsapp_message_id, active_config)

    # -----------------------------------------------------------------------
    # _handle_flow_response — handles nfm_reply messages (matches hanna)
    # -----------------------------------------------------------------------
    def _handle_flow_response(self, msg_data: dict, contact, active_config: MetaAppConfig, log_entry: WebhookEventLog):
        from flows.services import process_whatsapp_flow_response
        from conversations.models import Conversation
        from flows.tasks import process_flow_for_message_task

        whatsapp_message_id = msg_data.get("id")
        message_timestamp_str = msg_data.get("timestamp")
        message_timestamp = None
        if message_timestamp_str:
            try:
                message_timestamp = timezone.make_aware(datetime.fromtimestamp(int(message_timestamp_str)))
            except ValueError:
                logger.warning(f"Could not parse message timestamp: {message_timestamp_str}")
        if not message_timestamp:
            message_timestamp = timezone.now()

        # Get or create conversation
        conversation = Conversation.objects.filter(contact=contact, status='active').first()
        if not conversation:
            conversation = Conversation.objects.create(
                contact=contact,
                title=f"Chat with {contact.profile_name or contact.phone_number}",
                status='active',
            )

        incoming_msg_obj, _ = Message.objects.update_or_create(
            message_id=whatsapp_message_id,
            defaults={
                'contact': contact,
                'conversation': conversation,
                'app_config': active_config,
                'direction': 'inbound',
                'message_type': 'interactive',
                'content_payload': msg_data,
                'content': '[WhatsApp Flow Response]',
                'interactive_data': msg_data.get('interactive'),
                'timestamp': message_timestamp,
                'status': 'received',
                'status_timestamp': message_timestamp,
            },
        )

        if log_entry and log_entry.pk:
            log_entry.message = incoming_msg_obj
            log_entry.save(update_fields=['message'])

        # Process flow response context
        success, notes = process_whatsapp_flow_response(msg_data, contact, active_config)

        if success:
            msg_id = incoming_msg_obj.id
            transaction.on_commit(
                lambda: process_flow_for_message_task.delay(msg_id)
            )
            logger.info(f"Queued flow continuation for flow response message {msg_id}.")
            self._save_log(log_entry, 'processed', f"{notes} Flow continuation queued.")
        else:
            self._save_log(log_entry, 'error', notes)

    # -----------------------------------------------------------------------
    # _send_read_receipt — dispatches Celery task (matches hanna)
    # -----------------------------------------------------------------------
    def _send_read_receipt(self, wamid: str, app_config: MetaAppConfig, show_typing_indicator: bool = True):
        if not wamid:
            logger.warning("Cannot send read receipt: Missing WAMID.")
            return
        send_read_receipt_task.delay(
            wamid=wamid,
            config_id=app_config.id,
            show_typing_indicator=show_typing_indicator,
        )
        logger.info(f"Dispatched read receipt task for WAMID {wamid} (Typing: {show_typing_indicator}).")

    # -----------------------------------------------------------------------
    # Status / error / template / account update handlers (matches hanna)
    # -----------------------------------------------------------------------
    def handle_status_update(self, status_data, metadata, app_config, log_entry: WebhookEventLog):
        wamid = status_data.get("id")
        status_value = status_data.get("status")
        ts_str = status_data.get("timestamp")
        status_ts = (
            timezone.make_aware(datetime.fromtimestamp(int(ts_str)))
            if ts_str and ts_str.isdigit()
            else timezone.now()
        )
        logger.info(f"Status Update: WAMID={wamid}, Status='{status_value}'")
        notes = [f"Status for WAMID {wamid} is {status_value}."]
        try:
            msg_to_update = Message.objects.filter(message_id=wamid, direction='outbound').first()
            if msg_to_update:
                msg_to_update.status = status_value
                msg_to_update.status_timestamp = status_ts
                msg_to_update.save(update_fields=['status', 'status_timestamp'])
                notes.append("DB record updated.")
                self._save_log(log_entry, 'processed', " ".join(notes))
            else:
                self._save_log(log_entry, 'ignored', f"No matching outgoing msg for WAMID {wamid}.")
        except Exception as e:
            logger.error(f"Error updating status for WAMID {wamid}: {e}", exc_info=True)
            self._save_log(log_entry, 'error', str(e))

    def handle_error_notification(self, error_data, metadata, app_config, log_entry: WebhookEventLog):
        logger.error(f"Received error notification from Meta: {error_data}")
        self._save_log(log_entry, 'processed', f"Meta error logged: {error_data.get('title')}")

    def handle_template_status_update(self, status_data, metadata, app_config, log_entry: WebhookEventLog):
        logger.info(f"Template Status Update: {status_data}")
        self._save_log(
            log_entry, 'processed',
            f"Template status '{status_data.get('event')}' for '{status_data.get('message_template_name')}' logged.",
        )

    def handle_account_update(self, update_data, metadata, app_config, log_entry: WebhookEventLog):
        event = update_data.get('event')
        logger.info(f"Account Update Received: Event='{event}', Data: {update_data}")
        notes = f"Account update event '{event}' received."

        if event == 'DISABLED_UPDATE':
            is_disabled = update_data.get('is_disabled', False)
            if is_disabled:
                logger.critical(
                    f"CRITICAL: WhatsApp Business Account {app_config.waba_id} has been disabled! "
                    f"Reason: {update_data.get('disable_reason')}"
                )
                notes += f" Account DISABLED. Reason: {update_data.get('disable_reason')}. Immediate action required."
            else:
                logger.info(f"Account {app_config.waba_id} is no longer disabled.")
                notes += " Account is no longer disabled."
        elif event == 'ACCOUNT_REVIEW_UPDATE':
            decision = update_data.get('decision')
            logger.warning(
                f"Account review update for {app_config.waba_id}: {decision}. "
                f"Rejection reason: {update_data.get('rejection_reason')}"
            )
            notes += f" Review decision: {decision}."

        self._save_log(log_entry, 'processed', notes)

    # -----------------------------------------------------------------------
    # Content extraction helper
    # -----------------------------------------------------------------------
    @staticmethod
    def _extract_content_text(message_data: dict, message_type: str) -> str:
        if message_type == "text":
            return message_data.get("text", {}).get("body", "")
        elif message_type == "image":
            return f"[Image: {message_data.get('image', {}).get('id', '')}]"
        elif message_type == "document":
            return f"[Document: {message_data.get('document', {}).get('filename', '')}]"
        elif message_type == "audio":
            return "[Audio message]"
        elif message_type == "video":
            return "[Video message]"
        elif message_type == "interactive":
            return "[Interactive message]"
        elif message_type == "location":
            return f"[Location: {message_data.get('location', {}).get('name', 'Unknown')}]"
        else:
            return f"[{message_type} message]"

    # -----------------------------------------------------------------------
    # GET — webhook verification challenge (matches hanna)
    # -----------------------------------------------------------------------
    def get(self, request: HttpRequest, *args, **kwargs):
        active_config = get_active_meta_config()
        if not active_config:
            return HttpResponse("Error: App configuration not found or inactive.", status=404)

        verify_token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        mode = request.GET.get('hub.mode')

        logger.info(
            f"Webhook GET verification for config '{active_config.name}': "
            f"mode='{mode}', received_token='{verify_token}', challenge='{challenge}'"
        )

        if mode == 'subscribe' and verify_token == active_config.verify_token and challenge:
            logger.info(f"Webhook successfully verified for app: {active_config.name}.")
            return HttpResponse(challenge, status=200)
        else:
            failure_reasons = []
            if mode != 'subscribe':
                failure_reasons.append(f"mode was '{mode}' not 'subscribe'")
            if verify_token != active_config.verify_token:
                failure_reasons.append("verify_token did not match")
            if not challenge:
                failure_reasons.append("challenge was missing")

            logger.warning(
                f"Webhook verification failed for app: {active_config.name}. "
                f"Reason(s): {', '.join(failure_reasons) or 'Unknown'}. "
                f"Received Token: '{verify_token}'"
            )
            return HttpResponse("Error: Verification token mismatch or challenge missing.", status=403)


# ===========================================================================
# WebhookStatusView (sungrip-chatbot utility, kept for convenience)
# ===========================================================================
@method_decorator(csrf_exempt, name='dispatch')
class WebhookStatusView(View):
    """Check webhook configuration status."""

    def get(self, request):
        try:
            active_config = MetaAppConfig.objects.get_active_config()
            return JsonResponse({
                'status': 'active',
                'config_name': active_config.name,
                'phone_number_id': active_config.phone_number_id,
                'api_version': active_config.api_version,
            })
        except MetaAppConfig.DoesNotExist:
            return JsonResponse({
                'status': 'no_active_config',
                'message': 'No active MetaAppConfig found',
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e),
            }, status=500)
