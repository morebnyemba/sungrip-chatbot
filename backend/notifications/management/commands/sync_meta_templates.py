"""
Management command to sync local NotificationTemplates with Meta WhatsApp Business API.

Ported from morebnyemba/hanna's sync_meta_templates command, adapted for Sungrip Solar.

Usage:
    python manage.py sync_meta_templates              # Sync all templates
    python manage.py sync_meta_templates --dry-run    # Preview without sending
    python manage.py sync_meta_templates --template sungrip_new_product_order  # Sync one
"""

import re
import json
import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from notifications.models import NotificationTemplate
from meta_integration.models import MetaAppConfig


class Command(BaseCommand):
    help = 'Syncs local NotificationTemplate records with the Meta WhatsApp Business API.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print the API payloads that would be sent without actually calling Meta.',
        )
        parser.add_argument(
            '--template',
            type=str,
            default=None,
            help='Sync only the template with this name (e.g. sungrip_new_product_order).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even for templates that are already marked as synced.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        single_template = options.get('template')
        force = options.get('force', False)

        # Validate Meta configuration
        try:
            self.active_config = MetaAppConfig.objects.get_active_config()
            if not self.active_config.waba_id or not self.active_config.access_token:
                raise CommandError(
                    "Active MetaAppConfig is missing WABA ID or Access Token. "
                    "Please configure in Django Admin."
                )
        except MetaAppConfig.DoesNotExist:
            raise CommandError(
                "No active MetaAppConfig found. "
                "Please create and activate one in Django Admin."
            )

        api_version = self.active_config.api_version or 'v21.0'
        version_suffix = getattr(settings, 'META_SYNC_VERSION_SUFFIX', 'v1_01')

        self.stdout.write(self.style.SUCCESS(
            "--- Starting WhatsApp Template Sync with Meta ---"
        ))
        self.stdout.write(f"  WABA ID:         {self.active_config.waba_id}")
        self.stdout.write(f"  API Version:     {api_version}")
        self.stdout.write(f"  Version Suffix:  {version_suffix}")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "--- DRY RUN MODE: No requests will be sent to Meta. ---"
            ))

        # Build queryset
        templates_qs = NotificationTemplate.objects.all()
        if single_template:
            templates_qs = templates_qs.filter(name=single_template)
            if not templates_qs.exists():
                raise CommandError(f"Template '{single_template}' not found in database.")

        if not templates_qs.exists():
            self.stdout.write(self.style.WARNING(
                "No notification templates found in the database to sync."
            ))
            return

        headers = {
            "Authorization": f"Bearer {self.active_config.access_token}",
            "Content-Type": "application/json",
        }

        sync_stats = {'created': 0, 'updated': 0, 'skipped': 0, 'failed': 0}

        for template in templates_qs:
            template_name = template.name
            template_name_with_version = f"{template_name}_{version_suffix}"
            original_body = template.message_body

            self.stdout.write(
                f"\nProcessing: '{template_name}' → '{template_name_with_version}'"
            )

            # Skip disabled templates
            if template.sync_status == 'disabled':
                self.stdout.write(self.style.NOTICE(
                    f"  Skipping disabled template: '{template_name}'"
                ))
                sync_stats['skipped'] += 1
                continue

            # Skip already-synced templates unless --force
            if template.sync_status == 'synced' and not force:
                self.stdout.write(self.style.NOTICE(
                    f"  Skipping already-synced template: '{template_name}' (use --force to re-sync)"
                ))
                sync_stats['skipped'] += 1
                continue

            # --- Convert Jinja2 variables to Meta positional params ---
            jinja_pattern = r'\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}'
            jinja_matches = re.findall(jinja_pattern, original_body)

            # Preserve first-occurrence order, deduplicate
            jinja_variables = []
            seen = set()
            for var in jinja_matches:
                if var not in seen:
                    jinja_variables.append(var)
                    seen.add(var)

            meta_body = original_body
            body_parameters_map = {}

            if jinja_variables:
                for idx, var_name in enumerate(jinja_variables):
                    var_regex = r'\{\{\s*' + re.escape(var_name) + r'\s*\}\}'
                    meta_body = re.sub(
                        var_regex, f'{{{{{idx + 1}}}}}', meta_body, count=1
                    )
                    body_parameters_map[str(idx + 1)] = var_name

            # Store the computed mapping back on the template
            template.body_parameters = body_parameters_map

            # --- Build components ---
            components = [{"type": "BODY", "text": meta_body}]

            # Add example values for body parameters (required by Meta)
            if body_parameters_map:
                example_values = [
                    f"[{var_name.split('.')[-1]}]"
                    for var_name in body_parameters_map.values()
                ]
                components[0]["example"] = {"body_text": [example_values]}

            # Add footer
            components.append({
                "type": "FOOTER",
                "text": "Sungrip Solar — Confidential notification."
            })

            # --- Determine create vs update ---
            if template.meta_template_id:
                # Update existing template on Meta
                api_url = (
                    f"https://graph.facebook.com/{api_version}"
                    f"/{template.meta_template_id}"
                )
                payload = {"components": components}
                action = "update"
            else:
                # Create new template on Meta
                api_url = (
                    f"https://graph.facebook.com/{api_version}"
                    f"/{self.active_config.waba_id}/message_templates"
                )
                payload = {
                    "name": template_name_with_version,
                    "language": "en_US",
                    "category": "UTILITY",
                    "components": components,
                }
                action = "create"

            # --- Dry-run: print only ---
            if dry_run:
                self.stdout.write(self.style.NOTICE(
                    f"  [Dry Run] Action: {action.upper()}, URL: {api_url}"
                ))
                self.stdout.write(self.style.NOTICE(
                    f"  [Dry Run] Payload:"
                ))
                self.stdout.write(json.dumps(payload, indent=2))
                continue

            # --- Send to Meta ---
            try:
                if action == "create":
                    response = requests.post(
                        api_url, headers=headers, json=payload, timeout=30
                    )
                else:
                    response = requests.post(
                        api_url, headers=headers, json=payload, timeout=30
                    )

                response_data = response.json()

                if response.status_code in [200, 201]:
                    if action == "create":
                        template.meta_template_id = response_data.get('id')
                    template.sync_status = 'synced'
                    template.save()
                    sync_stats['created' if action == 'create' else 'updated'] += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  SUCCESS: '{template_name_with_version}' "
                        f"{action}d. ID: {template.meta_template_id}"
                    ))
                else:
                    error = response_data.get('error', {})
                    error_subcode = error.get('error_subcode')

                    if error_subcode == 2388039:
                        self.stdout.write(self.style.WARNING(
                            f"  SKIPPED: '{template_name}' is in non-editable "
                            f"status (e.g., pending review, rejected)."
                        ))
                        sync_stats['skipped'] += 1
                    else:
                        self.stdout.write(self.style.ERROR(
                            f"  FAILED to {action} '{template_name}'. "
                            f"Status: {response.status_code}"
                        ))
                        self.stdout.write(self.style.ERROR(
                            f"  Error: {json.dumps(response_data, indent=2)}"
                        ))
                        template.sync_status = 'failed'
                        template.save()
                        sync_stats['failed'] += 1

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(
                    f"  NETWORK ERROR for '{template_name}': {e}"
                ))
                template.sync_status = 'failed'
                template.save()
                sync_stats['failed'] += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"  UNEXPECTED ERROR for '{template_name}': {e}"
                ))
                template.sync_status = 'failed'
                template.save()
                sync_stats['failed'] += 1

        # --- Summary ---
        self.stdout.write(self.style.SUCCESS(
            "\n--- Template Sync Finished ---"
        ))
        self.stdout.write(
            f"  Created: {sync_stats['created']}  |  "
            f"Updated: {sync_stats['updated']}  |  "
            f"Skipped: {sync_stats['skipped']}  |  "
            f"Failed:  {sync_stats['failed']}"
        )
