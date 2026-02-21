"""
Management command to load flow definitions into the database.

This command imports flow definitions from flows/definitions/ and creates
Flow and FlowStep records in the database.

Following conventions from morebnyemba/Kalai-Safaris.
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.db import transaction
from flows.models import Flow, FlowStep, FlowTransition
from flows.definitions.main_menu_flow import MAIN_MENU_FLOW
from flows.definitions.solar_quote_flow import SOLAR_QUOTE_FLOW
from flows.definitions.installation_scheduling_flow import INSTALLATION_SCHEDULING_FLOW
from flows.definitions.solar_packages_flow import SOLAR_PACKAGES_FLOW
from flows.definitions.contact_support_flow import CONTACT_SUPPORT_FLOW
from flows.definitions.order_delivery_info_flow import ORDER_DELIVERY_INFO_FLOW


class Command(BaseCommand):
    help = 'Loads or updates predefined conversational flows from definition files into the database.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Starting to load flow definitions...")
        
        # List of flow definitions to load
        # Main menu should be loaded first as it's the entry point
        flow_definitions = [
            MAIN_MENU_FLOW,
            SOLAR_QUOTE_FLOW,
            INSTALLATION_SCHEDULING_FLOW,
            SOLAR_PACKAGES_FLOW,
            CONTACT_SUPPORT_FLOW,
            ORDER_DELIVERY_INFO_FLOW,
        ]

        for flow_def in flow_definitions:
            self.load_flow(flow_def)

        self.stdout.write(self.style.SUCCESS("Successfully loaded all flow definitions."))

    def load_flow(self, flow_def: dict):
        flow_name = flow_def['name']
        self.stdout.write(f"  Processing flow: '{flow_name}'...")

        # Pop 'is_active' to handle it at the end, preventing validation errors.
        is_active_from_def = flow_def.get('is_active', False)

        # Create or update the Flow object, but keep it inactive for now to avoid validation issues
        flow, created = Flow.objects.update_or_create(
            name=flow_name,
            defaults={
                'friendly_name': flow_def.get('friendly_name', flow_name.replace('_', ' ').title()),
                'description': flow_def.get('description', ''),
                'trigger_keywords': flow_def.get('trigger_keywords', []),
                'trigger_config': flow_def.get('trigger_config', {}),
                # --- IMPORTANT: Create/update as inactive first to avoid validation issues ---
                'is_active': False
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"    Created new flow '{flow_name}'."))
        else:
            self.stdout.write(f"    Updating existing flow '{flow_name}'. Clearing old steps and transitions.")
            # Clear all existing steps, which will cascade to transitions, ensuring a clean sync.
            flow.steps.all().delete()

        # First pass: Create all steps from the definition
        steps_in_db = {}
        for step_def in flow_def['steps']:
            step_name = step_def['name']
            step = FlowStep.objects.create(
                flow=flow,
                name=step_name,
                step_type=step_def['type'],
                config=step_def.get('config', {}),
                is_entry_point=step_def.get('is_entry_point', False)
            )
            steps_in_db[step_name] = step
            self.stdout.write(f"      - Created step '{step_name}'.")

        # Second pass: Create transitions, now that all steps are guaranteed to exist
        for step_def in flow_def['steps']:
            current_step_name = step_def['name']
            current_step_obj = steps_in_db[current_step_name]

            for i, trans_def in enumerate(step_def.get('transitions', [])):
                next_step_name = trans_def['to_step']
                if next_step_name not in steps_in_db:
                    raise CommandError(f"Next step '{next_step_name}' not found for transition from '{current_step_name}'. Aborting.")

                FlowTransition.objects.create(
                    current_step=current_step_obj,
                    next_step=steps_in_db[next_step_name],
                    condition_config=trans_def.get('condition_config', {}),
                    priority=trans_def.get('priority', i)
                )
            if step_def.get('transitions'):
                 self.stdout.write(f"      - Created transitions for step '{current_step_name}'.")

        # --- Final step: Set the intended 'is_active' status and run full validation ---
        if is_active_from_def:
            flow.is_active = is_active_from_def
            try:
                # This will run the model's clean() method, which checks for an entry point
                # now that all steps have been created.
                flow.full_clean()
                flow.save(update_fields=['is_active'])
                self.stdout.write(self.style.SUCCESS(f"    Successfully set 'is_active' to {is_active_from_def} for flow '{flow_name}'."))
            except ValidationError as e:
                self.stdout.write(self.style.ERROR(f"    Validation failed for flow '{flow_name}' when trying to activate it. Please check its definition."))
                # Raise CommandError to ensure the transaction is rolled back.
                raise CommandError(f"Validation error for flow '{flow_name}': {e}")
