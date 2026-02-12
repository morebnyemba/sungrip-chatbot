"""Management command to create solar-specific flows.

This command creates or updates solar flows in the database.
Following conventions from morebnyemba/Kalai-Safaris create_reg_flow.py pattern.

Usage:
    python manage.py create_flow --flow=solar_quote
    python manage.py create_flow --flow=installation_scheduling
    python manage.py create_flow --flow=all

For loading multiple flows from definitions, use: python manage.py load_flow_definitions
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from flows.models import Flow, FlowStep, FlowTransition
from flows.definitions.solar_flows import (
    MAIN_MENU_FLOW,
    SOLAR_QUOTE_FLOW,
    INSTALLATION_SCHEDULING_FLOW,
    SOLAR_PACKAGES_FLOW,
    CONTACT_SUPPORT_FLOW
)
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Creates or updates solar-specific flows in the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flow',
            type=str,
            choices=['main_menu', 'solar_quote', 'installation_scheduling', 'solar_packages', 'contact_support', 'all'],
            default='all',
            help='Which flow to create (default: all)'
        )

    def handle(self, *args, **options):
        flow_choice = options['flow']
        
        self.stdout.write(self.style.SUCCESS("--- Starting Solar Flow Creation Script ---"))

        flows_to_create = []
        if flow_choice in ['main_menu', 'all']:
            flows_to_create.append(MAIN_MENU_FLOW)
        if flow_choice in ['solar_quote', 'all']:
            flows_to_create.append(SOLAR_QUOTE_FLOW)
        if flow_choice in ['installation_scheduling', 'all']:
            flows_to_create.append(INSTALLATION_SCHEDULING_FLOW)
        if flow_choice in ['solar_packages', 'all']:
            flows_to_create.append(SOLAR_PACKAGES_FLOW)
        if flow_choice in ['contact_support', 'all']:
            flows_to_create.append(CONTACT_SUPPORT_FLOW)

        if not flows_to_create:
            raise CommandError(f"No flows selected for creation with choice '{flow_choice}'.")

        for flow_config in flows_to_create:
            self.create_flow(flow_config)

        self.stdout.write(self.style.SUCCESS("\n--- ✅ Solar Flow Creation Script Finished Successfully! ---"))

    def create_flow(self, flow_config: dict):
        """Create or update a single flow from configuration."""
        
        with transaction.atomic():
            # Get or create the Flow
            flow, created = Flow.objects.update_or_create(
                name=flow_config["name"],
                defaults={
                    "friendly_name": flow_config.get("friendly_name", flow_config["name"]),
                    "description": flow_config.get("description", ""),
                    "trigger_keywords": flow_config.get("trigger_keywords", []),
                    "is_active": flow_config.get("is_active", True)
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Flow "{flow.name}" was created.'))
            else:
                self.stdout.write(self.style.WARNING(f'🔄 Flow "{flow.name}" was found, updating it.'))
                # Clear existing steps and transitions to ensure a clean slate
                flow.steps.all().delete()
                self.stdout.write(self.style.WARNING(f'🗑️  Cleared all old steps and transitions for "{flow.name}".'))

            # Create steps
            steps_map = {}
            for step_data in flow_config.get("steps", []):
                self.stdout.write(f'  -> Creating step: {step_data["name"]}')
                step = FlowStep.objects.create(
                    flow=flow,
                    name=step_data["name"],
                    step_type=step_data["type"],
                    is_entry_point=step_data.get("is_entry_point", False),
                    config=step_data.get("config", {})
                )
                steps_map[step.name] = step

            # Create transitions
            for step_data in flow_config.get("steps", []):
                current_step = steps_map.get(step_data["name"])
                if not current_step:
                    logger.error(f"Step '{step_data['name']}' not found in steps_map. Skipping transitions for this step.")
                    continue

                for i, trans_data in enumerate(step_data.get("transitions", [])):
                    next_step = steps_map.get(trans_data.get("to_step"))
                    if next_step:
                        self.stdout.write(f'    -> Creating transition from "{current_step.name}" to "{next_step.name}"')
                        FlowTransition.objects.create(
                            current_step=current_step, next_step=next_step,
                            priority=trans_data.get("priority", i + 1),
                            condition_config=trans_data.get("condition_config", {})
                        )
                    else:
                        logger.warning(f"Next step '{trans_data.get('to_step')}' not found for transition from '{current_step.name}'. Skipping this transition.")

