import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import FlowSession

logger = logging.getLogger(__name__)

SESSION_IDLE_TIMEOUT_MINUTES = 5


@shared_task(name="flows.cleanup_idle_sessions_task")
def cleanup_idle_sessions_task():
    """Clean up flow sessions that have been idle beyond the timeout threshold."""
    idle_threshold = timezone.now() - timedelta(minutes=SESSION_IDLE_TIMEOUT_MINUTES)
    idle_sessions = FlowSession.objects.filter(
        status='active',
        updated_at__lt=idle_threshold,
    )

    from meta_integration.utils import send_text_message

    cleaned_count = 0
    for session in idle_sessions:
        session.status = 'expired'
        session.completed_at = timezone.now()
        session.save()

        try:
            send_text_message(
                session.contact.phone_number,
                "Your session has expired due to inactivity. "
                "Please send 'menu' to start a new conversation.",
            )
        except Exception:
            logger.exception(
                "Failed to send expiry notification for session %s", session.id
            )

        logger.info("Cleaned up idle session %s for contact %s", session.id, session.contact_id)
        cleaned_count += 1

    logger.info("Cleaned up %d idle sessions", cleaned_count)
    return {"cleaned_up": cleaned_count}
