"""
Meta Template Sync Service – imports WhatsApp message templates from Meta.

Uses the Graph API endpoint:
    GET /{waba_id}/message_templates

Populates both:
    - conversations.MessageTemplate  (detailed template records)
    - notifications.NotificationTemplate  (lightweight mapping for notifications)

Following the same service pattern used by MetaCatalogService.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from .models import MetaAppConfig

logger = logging.getLogger(__name__)

# Meta template status → local status mapping
STATUS_MAP = {
    "APPROVED": "approved",
    "PENDING": "pending",
    "REJECTED": "rejected",
    "PAUSED": "rejected",        # treat paused as rejected locally
    "DISABLED": "rejected",
    "IN_APPEAL": "pending",
    "PENDING_DELETION": "rejected",
    "DELETED": "rejected",
    "LIMIT_EXCEEDED": "rejected",
}

CATEGORY_MAP = {
    "MARKETING": "marketing",
    "UTILITY": "utility",
    "AUTHENTICATION": "authentication",
}


class MetaTemplateService:
    """Service for syncing WhatsApp message templates from Meta."""

    def __init__(self):
        try:
            config = MetaAppConfig.objects.get_active_config()
            self.api_version = config.api_version
            self.access_token = config.access_token
            self.waba_id = config.waba_id
        except MetaAppConfig.DoesNotExist:
            self.api_version = "v19.0"
            self.access_token = None
            self.waba_id = None

        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError("Meta access token is not configured.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    # ── Fetch all templates from Meta ───────────────────────────────

    def fetch_all_templates(
        self, status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all message templates from the WABA using cursor-based pagination.

        Args:
            status_filter: Optional Meta status to filter by (e.g. 'APPROVED').

        Returns:
            List of raw template dicts from Meta's API.
        """
        if not self.waba_id:
            raise ValueError("WABA ID is not configured.")

        url = f"{self.base_url}/{self.waba_id}/message_templates"
        params: Dict[str, Any] = {
            "limit": 100,
            "fields": "id,name,language,status,category,components,quality_score",
        }
        if status_filter:
            params["status"] = status_filter

        headers = self._get_headers()
        all_templates: List[Dict[str, Any]] = []

        while url:
            try:
                response = requests.get(
                    url, headers=headers, params=params, timeout=30
                )
                response.raise_for_status()
                data = response.json()

                templates = data.get("data", [])
                all_templates.extend(templates)
                logger.info(
                    f"Fetched {len(templates)} templates (total so far: {len(all_templates)})"
                )

                # Cursor pagination
                paging = data.get("paging", {})
                url = paging.get("next")
                params = {}  # params are embedded in the 'next' URL

            except requests.exceptions.RequestException as exc:
                logger.error(f"Error fetching templates from Meta: {exc}")
                raise

        logger.info(f"Total templates fetched from Meta: {len(all_templates)}")
        return all_templates

    # ── Parse components ────────────────────────────────────────────

    @staticmethod
    def _parse_components(
        components: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Parse Meta template components into flat fields.

        Returns dict with keys:
            header_type, header_content, body, footer, buttons
        """
        result: Dict[str, Any] = {
            "header_type": "",
            "header_content": "",
            "body": "",
            "footer": "",
            "buttons": [],
        }

        for comp in components or []:
            comp_type = comp.get("type", "").upper()

            if comp_type == "HEADER":
                fmt = comp.get("format", "TEXT").lower()
                result["header_type"] = fmt
                if fmt == "text":
                    result["header_content"] = comp.get("text", "")
                else:
                    # image / video / document – store the example URL if any
                    example = comp.get("example", {})
                    header_handles = example.get("header_handle", [])
                    result["header_content"] = (
                        header_handles[0] if header_handles else ""
                    )

            elif comp_type == "BODY":
                result["body"] = comp.get("text", "")

            elif comp_type == "FOOTER":
                result["footer"] = comp.get("text", "")

            elif comp_type == "BUTTONS":
                buttons_raw = comp.get("buttons", [])
                parsed_buttons = []
                for btn in buttons_raw:
                    parsed_buttons.append(
                        {
                            "type": btn.get("type", "").lower(),
                            "text": btn.get("text", ""),
                            "url": btn.get("url", ""),
                            "phone_number": btn.get("phone_number", ""),
                        }
                    )
                result["buttons"] = parsed_buttons

        return result

    # ── Import into MessageTemplate ─────────────────────────────────

    def import_templates(
        self, status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch all templates from Meta and sync them into the local
        conversations.MessageTemplate model.

        Returns:
            Stats dict with keys: created, updated, skipped, errors
        """
        from conversations.models import MessageTemplate

        raw_templates = self.fetch_all_templates(status_filter=status_filter)

        stats: Dict[str, Any] = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

        for tmpl in raw_templates:
            meta_id = tmpl.get("id", "")
            name = tmpl.get("name", "")
            language = tmpl.get("language", "en")
            meta_status = tmpl.get("status", "PENDING").upper()
            meta_category = tmpl.get("category", "UTILITY").upper()
            components = tmpl.get("components", [])

            if not name:
                stats["skipped"] += 1
                continue

            try:
                parsed = self._parse_components(components)
                local_status = STATUS_MAP.get(meta_status, "pending")
                local_category = CATEGORY_MAP.get(meta_category, "utility")

                # Use (name, language) as the unique key
                obj, created = MessageTemplate.objects.update_or_create(
                    name=name,
                    language=language,
                    defaults={
                        "category": local_category,
                        "header_type": parsed["header_type"],
                        "header_content": parsed["header_content"],
                        "body": parsed["body"],
                        "footer": parsed["footer"],
                        "buttons": parsed["buttons"],
                        "template_id": meta_id,
                        "status": local_status,
                        "is_active": local_status == "approved",
                    },
                )

                if created:
                    stats["created"] += 1
                    logger.info(
                        f"Created template: {name} ({language}) [{local_status}]"
                    )
                else:
                    stats["updated"] += 1
                    logger.info(
                        f"Updated template: {name} ({language}) [{local_status}]"
                    )

            except Exception as exc:
                stats["errors"].append(f"{name} ({language}): {exc}")
                logger.error(f"Error importing template '{name}': {exc}")

        logger.info(
            f"Template import complete — created: {stats['created']}, "
            f"updated: {stats['updated']}, skipped: {stats['skipped']}, "
            f"errors: {len(stats['errors'])}"
        )
        return stats

    # ── Sync into NotificationTemplate ──────────────────────────────

    def sync_notification_templates(
        self, status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch all templates from Meta and sync into the
        notifications.NotificationTemplate model (lightweight records
        used by the notification system).

        Returns:
            Stats dict with keys: created, updated, skipped, errors
        """
        from notifications.models import NotificationTemplate

        raw_templates = self.fetch_all_templates(status_filter=status_filter)

        stats: Dict[str, Any] = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

        for tmpl in raw_templates:
            meta_id = tmpl.get("id", "")
            name = tmpl.get("name", "")
            meta_status = tmpl.get("status", "PENDING").upper()
            components = tmpl.get("components", [])

            if not name:
                stats["skipped"] += 1
                continue

            try:
                parsed = self._parse_components(components)
                local_status = STATUS_MAP.get(meta_status, "pending")

                # Map Meta status to NotificationTemplate.sync_status
                if local_status == "approved":
                    sync_status = "synced"
                elif local_status == "rejected":
                    sync_status = "disabled"
                else:
                    sync_status = "pending"

                # Build body parameter mapping from Meta's example variables
                body_params = self._extract_body_params(parsed["body"])

                # Build button quick-replies
                quick_replies = [
                    btn["text"]
                    for btn in parsed["buttons"]
                    if btn.get("type") == "quick_reply"
                ][:3]

                obj, created = NotificationTemplate.objects.update_or_create(
                    name=name,
                    defaults={
                        "description": f"Auto-synced from Meta ({meta_status})",
                        "message_body": parsed["body"],
                        "buttons": quick_replies,
                        "body_parameters": body_params,
                        "meta_template_id": meta_id,
                        "sync_status": sync_status,
                    },
                )

                if created:
                    stats["created"] += 1
                    logger.info(f"Created notification template: {name}")
                else:
                    stats["updated"] += 1
                    logger.info(f"Updated notification template: {name}")

            except Exception as exc:
                stats["errors"].append(f"{name}: {exc}")
                logger.error(
                    f"Error syncing notification template '{name}': {exc}"
                )

        logger.info(
            f"Notification template sync complete — created: {stats['created']}, "
            f"updated: {stats['updated']}, skipped: {stats['skipped']}, "
            f"errors: {len(stats['errors'])}"
        )
        return stats

    @staticmethod
    def _extract_body_params(body_text: str) -> Dict[str, str]:
        """
        Extract {{1}}, {{2}} etc. from body text and build a parameter mapping.

        Returns:
            e.g. {"1": "param_1", "2": "param_2"}
        """
        import re

        params: Dict[str, str] = {}
        matches = re.findall(r"\{\{(\d+)\}\}", body_text)
        for idx in sorted(set(matches)):
            params[idx] = f"param_{idx}"
        return params
