"""
Signal handlers for syncing Product instances with Meta (Facebook) Catalog.

Adapted from morebnyemba/hanna's products_and_services/signals.py.
Automatically triggers catalog CRUD operations when products are
created, updated, or deleted.
"""
import logging
import threading
from datetime import timedelta

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Product, ProductImage

logger = logging.getLogger(__name__)

# Thread-local storage to prevent recursive signal calls
_thread_locals = threading.local()

MAX_SYNC_ATTEMPTS = 5
MIN_RETRY_DELAY_MINUTES = 5


@receiver(post_save, sender=Product)
def sync_product_to_meta_catalog(sender, instance, created, **kwargs):
    """Sync product to Meta Catalog on create/update."""
    processing_key = f"syncing_product_{instance.pk}"
    if getattr(_thread_locals, processing_key, False):
        return

    # Skip if only internal sync-tracking fields were updated
    update_fields = kwargs.get('update_fields')
    if update_fields is not None:
        sync_fields = {
            'whatsapp_catalog_id', 'meta_sync_attempts',
            'meta_sync_last_error', 'meta_sync_last_attempt',
            'meta_sync_last_success',
        }
        if set(update_fields).issubset(sync_fields):
            return

    from meta_integration.catalog_service import MetaCatalogService

    if not instance.sku or not instance.is_active:
        return

    if instance.meta_sync_attempts >= MAX_SYNC_ATTEMPTS:
        logger.warning(
            f"Product '{instance.name}' exceeded max sync attempts ({MAX_SYNC_ATTEMPTS}). "
            f"Last error: {instance.meta_sync_last_error}"
        )
        return

    # Exponential backoff
    if instance.meta_sync_attempts > 0 and instance.meta_sync_last_attempt:
        delay = MIN_RETRY_DELAY_MINUTES * (3 ** (instance.meta_sync_attempts - 1))
        next_retry = instance.meta_sync_last_attempt + timedelta(minutes=delay)
        if timezone.now() < next_retry:
            return

    setattr(_thread_locals, processing_key, True)
    sync_time = timezone.now()

    try:
        service = MetaCatalogService()

        if created or not instance.whatsapp_catalog_id:
            response = service.create_product_in_catalog(instance)
            if response and 'id' in response:
                Product.objects.filter(pk=instance.pk).update(
                    whatsapp_catalog_id=response['id'],
                    meta_sync_attempts=0,
                    meta_sync_last_error=None,
                    meta_sync_last_attempt=sync_time,
                    meta_sync_last_success=sync_time,
                )
                logger.info(f"Created product in Meta Catalog: {response['id']}")
            else:
                _record_sync_error(
                    instance, sync_time,
                    f"Unexpected response: {response}"
                )
        else:
            service.update_product_in_catalog(instance)
            Product.objects.filter(pk=instance.pk).update(
                meta_sync_attempts=0,
                meta_sync_last_error=None,
                meta_sync_last_attempt=sync_time,
                meta_sync_last_success=sync_time,
            )
            logger.info(f"Updated product '{instance.name}' in Meta Catalog")

    except ValueError as exc:
        _record_sync_error(instance, sync_time, f"Config error: {exc}")
    except Exception as exc:
        _record_sync_error(instance, sync_time, f"{type(exc).__name__}: {exc}")
        logger.error(f"Error syncing product '{instance.name}': {exc}", exc_info=True)
    finally:
        setattr(_thread_locals, processing_key, False)


@receiver(post_delete, sender=Product)
def delete_product_from_meta_catalog(sender, instance, **kwargs):
    """Delete product from Meta Catalog when removed locally."""
    if not instance.whatsapp_catalog_id:
        return

    from meta_integration.catalog_service import MetaCatalogService

    try:
        service = MetaCatalogService()
        service.delete_product_from_catalog(instance)
        logger.info(
            f"Deleted product '{instance.name}' from Meta Catalog "
            f"(ID: {instance.whatsapp_catalog_id})"
        )
    except Exception as exc:
        logger.error(f"Error deleting product from Meta Catalog: {exc}", exc_info=True)


@receiver(post_save, sender=ProductImage)
def sync_product_on_image_change(sender, instance, created, **kwargs):
    """Re-sync parent product when an image is added."""
    product = instance.product
    if not product.pk or not product.sku or not product.is_active:
        return

    needs_resync = not product.whatsapp_catalog_id or created
    if not needs_resync:
        return

    if product.meta_sync_attempts > 0:
        Product.objects.filter(pk=product.pk).update(
            meta_sync_attempts=0,
            meta_sync_last_error=None,
        )
        product.refresh_from_db()

    # Trigger post_save signal on product
    product.save(update_fields=['updated_at'])


def _record_sync_error(product, sync_time, error_msg):
    """Helper to record a sync failure on the product."""
    Product.objects.filter(pk=product.pk).update(
        meta_sync_attempts=product.meta_sync_attempts + 1,
        meta_sync_last_error=error_msg[:1000],
        meta_sync_last_attempt=sync_time,
    )
    logger.error(f"Sync error for '{product.name}': {error_msg}")
