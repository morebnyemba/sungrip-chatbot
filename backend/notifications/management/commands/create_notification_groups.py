"""
Management command to create the Django auth Groups required by the notification system.

Groups are used to target notifications to specific teams of staff users.
Each staff user should belong to at least one group to receive notifications.

Usage:
    python manage.py create_notification_groups
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


# Groups needed by Sungrip's notification system
REQUIRED_GROUPS = [
    {
        'name': 'Sales Team',
        'description': (
            'Receives notifications for new quotes, orders, installation requests, '
            'and general sales-related events.'
        ),
    },
    {
        'name': 'Support Team',
        'description': (
            'Receives notifications for customer support requests and escalations.'
        ),
    },
    {
        'name': 'Technical Admin',
        'description': (
            'Receives notifications for system errors, failed message deliveries, '
            'and technical issues.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Creates the Django auth Groups required by the notification system.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            '--- Creating Notification Groups ---'
        ))

        created_count = 0
        existing_count = 0

        for group_info in REQUIRED_GROUPS:
            group, created = Group.objects.get_or_create(name=group_info['name'])
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  Created group: '{group_info['name']}'"
                ))
            else:
                existing_count += 1
                self.stdout.write(self.style.NOTICE(
                    f"  Already exists: '{group_info['name']}'"
                ))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Created {created_count}, already existed {existing_count}.'
        ))

        # Remind about adding users
        self.stdout.write('')
        self.stdout.write(
            'Next steps: assign staff users to these groups in Django Admin → Users → Groups.'
        )
        self.stdout.write(
            'Staff users in a group will receive WhatsApp notifications targeted to that group.'
        )
