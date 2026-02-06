"""
Webhook views for meta_integration app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
Handles incoming webhook requests from Meta WhatsApp Business API.
"""
import json
import logging
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings

from .models import MetaAppConfig, WebhookEventLog
from .services import WebhookProcessor
from .tasks import process_webhook_event_task

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class MetaWebhookAPIView(View):
    """
    Handles Meta WhatsApp Business API webhook verification and events.

    Endpoints:
    - GET: Webhook verification (Meta sends this during setup)
    - POST: Incoming webhook events (messages, status updates, etc.)
    """

    def get(self, request):
        """
        Handle webhook verification from Meta.

        Meta sends a GET request with:
        - hub.mode: 'subscribe'
        - hub.verify_token: Your verify token
        - hub.challenge: Random string to echo back

        Returns the challenge if verify_token matches.
        """
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        logger.info(f"Webhook verification request: mode={mode}")

        if mode == 'subscribe':
            # Try to find a config with matching verify token
            try:
                config = MetaAppConfig.objects.filter(verify_token=token).first()
                if config:
                    logger.info(f"Webhook verified for config: {config.name}")
                    return HttpResponse(challenge, content_type='text/plain')
                else:
                    logger.warning(f"Webhook verification failed: Invalid verify token")
                    return HttpResponse('Invalid verify token', status=403)
            except Exception as e:
                logger.error(f"Error during webhook verification: {str(e)}")
                return HttpResponse('Verification error', status=500)
        else:
            logger.warning(f"Invalid webhook verification mode: {mode}")
            return HttpResponse('Invalid mode', status=400)

    def post(self, request):
        """
        Handle incoming webhook events from Meta.

        Processes:
        - Incoming messages
        - Message status updates (sent, delivered, read, failed)
        - Template status updates
        - Other webhook events

        Returns 200 OK immediately to acknowledge receipt,
        then processes the event asynchronously.
        """
        try:
            # Parse payload
            try:
                payload = json.loads(request.body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON payload received")
                return JsonResponse({'error': 'Invalid JSON'}, status=400)

            logger.info(f"Webhook event received: {payload.get('object')}")

            # Extract phone_number_id to find the right config
            phone_number_id = WebhookProcessor.extract_phone_number_id(payload)
            if not phone_number_id:
                logger.warning("Could not extract phone_number_id from webhook payload")
                # Still return 200 to avoid Meta retrying
                return JsonResponse({'status': 'ignored', 'reason': 'No phone_number_id'})

            # Find matching configuration
            try:
                config = MetaAppConfig.objects.get(
                    phone_number_id=phone_number_id,
                    is_active=True
                )
            except MetaAppConfig.DoesNotExist:
                logger.error(f"No active config found for phone_number_id: {phone_number_id}")
                # Still return 200 to avoid Meta retrying
                return JsonResponse({'status': 'ignored', 'reason': 'No active config'})

            # Verify signature if app_secret is configured
            if config.app_secret:
                signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
                is_valid = WebhookProcessor.verify_signature(
                    request.body,
                    signature,
                    config.app_secret
                )
                if not is_valid:
                    logger.error("Webhook signature verification failed")
                    return JsonResponse({'error': 'Invalid signature'}, status=403)
                logger.info("Webhook signature verified successfully")

            # Create webhook log
            webhook_log = WebhookProcessor.process_webhook_event(payload, config)

            # Process asynchronously using Celery
            if getattr(settings, 'CELERY_ENABLED', True):
                process_webhook_event_task.delay(webhook_log.id)
                logger.info(f"Webhook event queued for processing: {webhook_log.id}")
            else:
                # Process synchronously if Celery is disabled (development)
                process_webhook_event_task(webhook_log.id)
                logger.info(f"Webhook event processed synchronously: {webhook_log.id}")

            # Return 200 OK immediately
            return JsonResponse({'status': 'received'}, status=200)

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            # Still return 200 to avoid Meta retrying on our internal errors
            return JsonResponse({'status': 'error', 'message': str(e)}, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookStatusView(View):
    """
    View for checking webhook configuration status.
    """

    def get(self, request):
        """
        Return webhook configuration status.
        """
        try:
            active_config = MetaAppConfig.objects.get_active_config()
            return JsonResponse({
                'status': 'active',
                'config_name': active_config.name,
                'phone_number_id': active_config.phone_number_id,
                'api_version': active_config.api_version
            })
        except MetaAppConfig.DoesNotExist:
            return JsonResponse({
                'status': 'no_active_config',
                'message': 'No active MetaAppConfig found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
