"""
Meta Catalog Service for syncing products with Meta (Facebook) Product Catalog.

Adapted from morebnyemba/hanna's catalog_service.py for Sungrip Solar.

IMPORTANT: Image URL Accessibility
===================================
For products to be successfully created in Meta's catalog, the image_url must be:
1. Publicly accessible (no authentication required)
2. Reachable from Meta's servers (not behind a firewall/VPN)
3. Return a valid image with proper Content-Type header
4. Use HTTPS protocol (data URIs are NOT supported by Meta API)

Django Settings Required:
- BACKEND_DOMAIN: Domain name for constructing absolute URLs
"""

import json
import logging

import requests
from django.conf import settings

from .models import MetaAppConfig

DEFAULT_PRODUCT_LINK = "https://sungripsolar.co.zw"

logger = logging.getLogger(__name__)

# Static placeholder image path for products without images
PLACEHOLDER_IMAGE_PATH = "/static/admin/img/placeholder.png"


class MetaCatalogService:
    """Service for syncing products with Meta's WhatsApp Product Catalog."""

    def __init__(self):
        try:
            active_config = MetaAppConfig.objects.get_active_config()
            self.api_version = active_config.api_version
            self.access_token = active_config.access_token
            self.catalog_id = active_config.catalog_id
        except MetaAppConfig.DoesNotExist:
            self.api_version = "v19.0"
            self.access_token = None
            self.catalog_id = None

        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def _get_headers(self):
        if not self.access_token:
            raise ValueError("Meta access token is not configured.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _get_backend_domain(self):
        return getattr(settings, 'BACKEND_DOMAIN', 'localhost')

    def _get_product_data(self, product):
        """
        Build a product data payload for Meta's Catalog API.

        Required fields per Meta API:
        - retailer_id (mapped from SKU)
        - name
        - availability: in stock | out of stock
        - price: integer in cents/minor currency units
        - currency: ISO 4217 code
        - image_url: publicly accessible URL
        """
        if not product.sku:
            raise ValueError(
                f"Product '{product.name}' (ID: {product.id}) is missing an SKU."
            )

        price_value = 0
        if product.selling_price is not None:
            price_value = int(round(float(product.selling_price) * 100))

        data = {
            "retailer_id": product.sku,
            "name": product.name,
            "price": price_value,
            "currency": product.currency,
            "condition": "new",
            "availability": "in stock" if product.stock_quantity > 0 else "out of stock",
            "link": getattr(product, 'website_url', None) or DEFAULT_PRODUCT_LINK,
        }

        if product.short_description:
            data["description"] = product.short_description
        elif product.full_description:
            data["description"] = product.full_description[:5000]

        if product.brand:
            data["brand"] = product.brand

        if product.category and product.category.google_product_category:
            data["google_product_category"] = product.category.google_product_category

        # Resolve image URL
        backend_domain = self._get_backend_domain()
        placeholder_url = f"https://{backend_domain}{PLACEHOLDER_IMAGE_PATH}"

        # Try ProductImage gallery first, then single image field, then image_url
        from products.models import ProductImage
        first_image = ProductImage.objects.filter(product_id=product.pk).first()

        if first_image and hasattr(first_image.image, 'url') and first_image.image.url:
            image_url = str(first_image.image.url).strip()
            if image_url and image_url.startswith('/'):
                image_url = f"https://{backend_domain}{image_url}"
            data["image_url"] = image_url or placeholder_url
        elif product.image and hasattr(product.image, 'url') and product.image.url:
            image_url = str(product.image.url).strip()
            if image_url and image_url.startswith('/'):
                image_url = f"https://{backend_domain}{image_url}"
            data["image_url"] = image_url or placeholder_url
        elif product.image_url:
            data["image_url"] = product.image_url
        else:
            data["image_url"] = placeholder_url

        return data

    def create_product_in_catalog(self, product):
        """Create a new product in Meta Catalog."""
        if not self.catalog_id:
            raise ValueError("WhatsApp Catalog ID is not configured.")
        url = f"{self.base_url}/{self.catalog_id}/products"
        data = self._get_product_data(product)

        logger.info(f"Creating product in Meta Catalog: {product.name} (SKU: {product.sku})")
        logger.debug(f"Payload: {json.dumps(data, indent=2)}")
        response = requests.post(
            url, headers=self._get_headers(), json=data, timeout=30
        )
        return self._handle_response(response, product, "create")

    def update_product_in_catalog(self, product):
        """Update an existing product in Meta Catalog."""
        if not product.whatsapp_catalog_id:
            raise ValueError("Product does not have a WhatsApp Catalog ID.")
        url = f"{self.base_url}/{product.whatsapp_catalog_id}"
        data = self._get_product_data(product)

        logger.info(
            f"Updating product in Meta Catalog: {product.name} "
            f"(Catalog ID: {product.whatsapp_catalog_id})"
        )
        response = requests.post(
            url, headers=self._get_headers(), json=data, timeout=30
        )
        return self._handle_response(response, product, "update")

    def sync_product_update(self, product):
        """Create or update a product depending on whether it already has a catalog ID."""
        if product.whatsapp_catalog_id:
            return self.update_product_in_catalog(product)
        return self.create_product_in_catalog(product)

    def delete_product_from_catalog(self, product):
        """Delete a product from Meta Catalog."""
        if not product.whatsapp_catalog_id:
            raise ValueError("Product does not have a WhatsApp Catalog ID.")
        url = f"{self.base_url}/{product.whatsapp_catalog_id}"

        logger.info(
            f"Deleting product from Meta Catalog: {product.name} "
            f"(Catalog ID: {product.whatsapp_catalog_id})"
        )
        response = requests.delete(url, headers=self._get_headers(), timeout=30)
        return self._handle_response(response, product, "delete")

    def get_product_from_catalog(self, product):
        """Fetch current product data from Meta Catalog."""
        if not product.whatsapp_catalog_id:
            raise ValueError("Product does not have a WhatsApp Catalog ID.")
        url = f"{self.base_url}/{product.whatsapp_catalog_id}"

        response = requests.get(url, headers=self._get_headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def set_product_visibility(self, product, visibility='published'):
        """Set product visibility in Meta Catalog (published/hidden)."""
        if not product.whatsapp_catalog_id:
            raise ValueError("Product does not have a WhatsApp Catalog ID.")
        if visibility not in ('published', 'hidden'):
            raise ValueError(f"Invalid visibility: {visibility}")
        if not self.catalog_id:
            raise ValueError("WhatsApp Catalog ID is not configured.")

        url = f"{self.base_url}/{self.catalog_id}/items_batch"
        data = {
            "requests": [{
                "method": "UPDATE",
                "retailer_id": product.sku,
                "data": {"visibility": visibility},
            }]
        }

        logger.info(
            f"Setting visibility to '{visibility}' for {product.name} (SKU: {product.sku})"
        )
        response = requests.post(
            url, headers=self._get_headers(), json=data, timeout=30
        )
        response.raise_for_status()
        return response.json()

    def fetch_all_catalog_products(self):
        """
        Fetch ALL products from the Meta Catalog.

        Uses the Graph API endpoint: GET /{catalog_id}/products
        Handles pagination via cursors automatically.

        Returns a list of product dicts from Meta.
        """
        if not self.catalog_id:
            raise ValueError("WhatsApp Catalog ID is not configured.")

        url = f"{self.base_url}/{self.catalog_id}/products"
        params = {
            "fields": (
                "id,retailer_id,name,description,price,currency,"
                "availability,image_url,brand,url,category"
            ),
            "limit": 250,
        }

        all_products = []
        while url:
            response = requests.get(
                url, headers=self._get_headers(), params=params, timeout=60
            )
            response.raise_for_status()
            data = response.json()
            all_products.extend(data.get("data", []))

            # Follow pagination cursor
            paging = data.get("paging", {})
            url = paging.get("next")
            params = None  # next URL already includes query params

        logger.info(
            f"Fetched {len(all_products)} product(s) from Meta Catalog {self.catalog_id}"
        )
        return all_products

    def import_products_from_catalog(self):
        """
        Import/sync products FROM Meta Catalog INTO the local database.

        For each product in the catalog:
        - If a local Product with matching SKU exists → update it
        - If no local Product with that SKU → create a new one

        Returns a dict with counts: {created, updated, skipped, errors}.
        """
        from products.models import Product

        meta_products = self.fetch_all_catalog_products()
        stats = {"created": 0, "updated": 0, "skipped": 0, "errors": []}

        for mp in meta_products:
            retailer_id = mp.get("retailer_id", "").strip()
            meta_id = mp.get("id", "")
            name = mp.get("name", "").strip()

            if not retailer_id:
                stats["skipped"] += 1
                logger.warning(
                    f"Skipping Meta product '{name}' (id={meta_id}): no retailer_id/SKU"
                )
                continue

            try:
                # Parse price: Meta may return "$80.00", "8000", "80.00 USD", etc.
                raw_price = str(mp.get("price", "0")).strip()
                # Strip currency symbols and codes
                import re
                raw_price = re.sub(r'[^\d.]', '', raw_price.split()[0])
                raw_price = raw_price or "0"
                price_value = float(raw_price)
                # If value looks like cents (>100 and no decimal), convert
                selling_price = price_value / 100 if price_value > 0 and price_value == int(price_value) and price_value > 1000 else price_value

                currency = mp.get("currency", "USD")
                availability = mp.get("availability", "in stock")
                description = mp.get("description", "")
                image_url = mp.get("image_url", "")
                brand = mp.get("brand", "")

                defaults = {
                    "name": name or retailer_id,
                    "short_description": description[:500] if description else "",
                    "selling_price": selling_price,
                    "cost_price": selling_price,  # default cost = selling; admin can adjust
                    "currency": currency,
                    "stock_quantity": 1 if availability == "in stock" else 0,
                    "image_url": image_url,
                    "brand": brand,
                    "whatsapp_catalog_id": meta_id,
                    "is_active": availability == "in stock",
                }

                product, created = Product.objects.update_or_create(
                    sku=retailer_id,
                    defaults=defaults,
                )

                if created:
                    stats["created"] += 1
                    logger.info(f"Created product from Meta: {name} (SKU: {retailer_id})")
                else:
                    stats["updated"] += 1
                    logger.info(f"Updated product from Meta: {name} (SKU: {retailer_id})")

            except Exception as exc:
                stats["errors"].append(f"{name or retailer_id}: {exc}")
                logger.error(
                    f"Error importing Meta product '{name}' (SKU: {retailer_id}): {exc}"
                )

        logger.info(
            f"Meta import complete — created: {stats['created']}, "
            f"updated: {stats['updated']}, skipped: {stats['skipped']}, "
            f"errors: {len(stats['errors'])}"
        )
        return stats

    def _handle_response(self, response, product, operation):
        """Handle Meta API response with detailed error logging."""
        try:
            response.raise_for_status()
            result = response.json()
            logger.info(
                f"Successfully {operation}d product '{product.name}' in Meta Catalog."
            )
            return result
        except requests.exceptions.HTTPError:
            try:
                error_details = response.json()
                error_obj = error_details.get('error', {})
                error_msg = error_obj.get('message', str(error_details))
                error_code = error_obj.get('code', response.status_code)
                error_type = error_obj.get('type', 'Unknown')
                error_subcode = error_obj.get('error_subcode', '')
                error_user_title = error_obj.get('error_user_title', '')
                error_user_msg = error_obj.get('error_user_msg', '')
            except (ValueError, KeyError):
                error_msg = response.text
                error_code = response.status_code
                error_type = 'Unknown'
                error_subcode = ''
                error_user_title = ''
                error_user_msg = ''

            logger.error(
                f"Meta API error ({operation}) for '{product.name}' "
                f"(SKU: {product.sku}): [{error_code}] {error_msg}"
            )
            if error_subcode or error_user_msg:
                logger.error(
                    f"  -> subcode={error_subcode} type={error_type} "
                    f"title='{error_user_title}' detail='{error_user_msg}'"
                )
            raise ValueError(
                f"Meta API Error ({error_code}): {error_msg}"
            )
        except requests.exceptions.Timeout:
            msg = f"Meta API timeout during {operation} for '{product.name}'"
            logger.error(msg)
            raise ValueError(msg)
        except requests.exceptions.RequestException as exc:
            msg = f"Network error during {operation} for '{product.name}': {exc}"
            logger.error(msg)
            raise ValueError(msg) from exc
