"""
Management command to validate the full notification pipeline is correctly configured.

Checks: Groups exist, templates loaded, staff users linked to contacts,
Meta API configured, recent notification health.

Usage:
    python manage.py validate_notification_setup
    python manage.py validate_notification_setup --verbose
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
from notifications.models import Notification, NotificationTemplate
from meta_integration.models import MetaAppConfig


class Command(BaseCommand):
    help = 'Validates that the notification system is fully configured and ready.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Show detailed information for each check.',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        issues = []

        self.stdout.write(self.style.SUCCESS(
            '\n=== Sungrip Notification Setup Validation ===\n'
        ))

        # -------------------------------------------------------
        # Check 1: Required Groups
        # -------------------------------------------------------
        self.stdout.write('1. Checking Notification Groups...')
        required_groups = ['Sales Team', 'Support Team', 'Technical Admin']
        for group_name in required_groups:
            exists = Group.objects.filter(name=group_name).exists()
            if exists:
                member_count = User.objects.filter(groups__name=group_name).count()
                self.stdout.write(self.style.SUCCESS(
                    f'   ✓ {group_name} ({member_count} member(s))'
                ))
                if member_count == 0:
                    issues.append(
                        f"Group '{group_name}' exists but has no members"
                    )
            else:
                issues.append(f"Group '{group_name}' does not exist")
                self.stdout.write(self.style.ERROR(
                    f'   ✗ {group_name} — MISSING'
                ))

        # -------------------------------------------------------
        # Check 2: Staff Users
        # -------------------------------------------------------
        self.stdout.write('\n2. Checking Staff Users...')
        staff_users = User.objects.filter(is_staff=True)
        if not staff_users.exists():
            issues.append('No staff users found')
            self.stdout.write(self.style.ERROR('   ✗ No staff users found'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'   ✓ {staff_users.count()} staff user(s) found'
            ))

        # -------------------------------------------------------
        # Check 3: Staff Users linked to Contacts
        # -------------------------------------------------------
        self.stdout.write('\n3. Checking Staff → Contact linkage...')
        try:
            from customers.models import Customer
            from conversations.models import Contact

            unlinked = []
            for user in staff_users:
                customer = Customer.objects.filter(user=user).first()
                if not customer:
                    unlinked.append(user.username)
                    continue
                contact = Contact.objects.filter(customer=customer).first()
                if not contact:
                    unlinked.append(user.username)

            if unlinked:
                issues.append(
                    f"{len(unlinked)} staff user(s) not linked to a Contact: "
                    f"{', '.join(unlinked[:5])}"
                )
                self.stdout.write(self.style.WARNING(
                    f'   ⚠ {len(unlinked)} staff user(s) lack Customer → Contact chain'
                ))
                if verbose:
                    for u in unlinked:
                        self.stdout.write(f'      - {u}')
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'   ✓ All {staff_users.count()} staff user(s) linked to contacts'
                ))
        except Exception as e:
            issues.append(f'Could not check Contact linkage: {e}')
            self.stdout.write(self.style.WARNING(
                f'   ⚠ Could not verify Contact linkage: {e}'
            ))

        # -------------------------------------------------------
        # Check 4: Notification Templates
        # -------------------------------------------------------
        self.stdout.write('\n4. Checking Notification Templates...')
        template_count = NotificationTemplate.objects.count()
        if template_count == 0:
            issues.append('No notification templates found')
            self.stdout.write(self.style.ERROR('   ✗ No templates loaded'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'   ✓ {template_count} template(s) loaded'
            ))
            if verbose:
                for t in NotificationTemplate.objects.all():
                    status_icon = {
                        'synced': '✓',
                        'pending': '●',
                        'failed': '✗',
                        'disabled': '○',
                    }.get(t.sync_status, '?')
                    self.stdout.write(
                        f'      [{status_icon}] {t.name} ({t.sync_status})'
                    )

        # Pending sync check
        pending = NotificationTemplate.objects.filter(sync_status='pending').count()
        failed = NotificationTemplate.objects.filter(sync_status='failed').count()
        if pending:
            issues.append(f'{pending} template(s) pending Meta sync')
            self.stdout.write(self.style.WARNING(
                f'   ⚠ {pending} template(s) pending sync — '
                f'run: python manage.py sync_meta_templates'
            ))
        if failed:
            issues.append(f'{failed} template(s) failed Meta sync')
            self.stdout.write(self.style.ERROR(
                f'   ✗ {failed} template(s) failed sync — '
                f'run: python manage.py sync_meta_templates --force'
            ))

        # -------------------------------------------------------
        # Check 5: Meta API Configuration
        # -------------------------------------------------------
        self.stdout.write('\n5. Checking Meta API Configuration...')
        try:
            active_config = MetaAppConfig.objects.get_active_config()
            self.stdout.write(self.style.SUCCESS(
                f'   ✓ Active config: {active_config.name}'
            ))
            self.stdout.write(f'      Phone Number ID: {active_config.phone_number_id}')
            self.stdout.write(f'      WABA ID:         {active_config.waba_id}')
        except MetaAppConfig.DoesNotExist:
            issues.append('No active Meta API configuration found')
            self.stdout.write(self.style.ERROR('   ✗ No active Meta API config'))
        except MetaAppConfig.MultipleObjectsReturned:
            issues.append('Multiple active Meta API configurations found')
            self.stdout.write(self.style.ERROR(
                '   ✗ Multiple active configs — only one should be active'
            ))

        # -------------------------------------------------------
        # Check 6: Recent Notification Health
        # -------------------------------------------------------
        self.stdout.write('\n6. Checking Recent Notification Delivery...')
        recent = Notification.objects.all()[:100]
        if not recent.exists():
            self.stdout.write(self.style.NOTICE(
                '   ● No notifications dispatched yet'
            ))
        else:
            total = recent.count()
            sent = sum(1 for n in recent if n.status == 'sent')
            failed_n = sum(1 for n in recent if n.status == 'failed')
            pending_n = sum(1 for n in recent if n.status == 'pending')
            self.stdout.write(
                f'   Last {total}: sent={sent}, failed={failed_n}, pending={pending_n}'
            )
            if failed_n > total * 0.3:
                issues.append(
                    f'High failure rate: {failed_n}/{total} recent notifications failed'
                )
                self.stdout.write(self.style.ERROR(
                    f'   ✗ High failure rate ({failed_n}/{total})'
                ))

        # -------------------------------------------------------
        # Summary
        # -------------------------------------------------------
        self.stdout.write('\n' + '=' * 50)
        if issues:
            self.stdout.write(self.style.ERROR(
                f'\n⚠  {len(issues)} issue(s) found:\n'
            ))
            for i, issue in enumerate(issues, 1):
                self.stdout.write(f'   {i}. {issue}')
            self.stdout.write('')
        else:
            self.stdout.write(self.style.SUCCESS(
                '\n✓ All checks passed! Notification system is ready.\n'
            ))
