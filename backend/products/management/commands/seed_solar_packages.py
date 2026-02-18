"""
Management command to seed the database with Sungrip solar packages.

Creates all 6 standard packages:
  • 3 × Cash-on-delivery packages  (3.5 kVA, 4.2 kVA, 6.2 kVA)
  • 3 × 6-month payment-plan packages (3.5 kVA, 4.2 kVA, 6.2 kVA)

Usage:
    python manage.py seed_solar_packages          # create missing only
    python manage.py seed_solar_packages --reset   # wipe & recreate all
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import SolarPackage


# ──────────────────────────────────────────────────────────────────────
# Package data extracted from Sungrip promotional material
# ──────────────────────────────────────────────────────────────────────

PACKAGES = [
    # ──── Cash on Delivery Packages ────────────────────────────────────
    {
        "name": "3.5kVA Solar (Cash)",
        "description": (
            "Entry-level home solar system ideal for small households. "
            "Supply and fix — professional installation included. "
            "Outside Harare, transport charges apply. "
            "Warranty and after-service support included."
        ),
        "system_size_kw": 3.5,
        "recommended_for": "small_home",
        "total_price": 1100,
        "payment_type": "cash",
        "installment_months": 0,
        "installation_included": True,
        "is_active": True,
        "is_popular": False,
        "display_order": 1,
        "equipment_summary": [
            "4 × 450-585W Solar Panels",
            "100Ah 24V Lithium Battery",
            "3.2 kVA Hybrid Inverter",
        ],
        "powers": [
            "Fridge",
            "TV",
            "Solar Iron",
            "WiFi Router",
            "Decoder",
            "Lights & Laptop",
            "Borehole Pump (0.5 HP)",
        ],
        "features": [
            "Professional supply & installation",
            "Cash on delivery",
            "Warranty & after-service support",
            "Payment after delivery & installation",
        ],
    },
    {
        "name": "4.2kVA Solar (Cash)",
        "description": (
            "Mid-range home solar system with camera support. "
            "Supply and fix — professional installation included. "
            "Outside Harare, transport charges apply. "
            "Warranty and after-service support included."
        ),
        "system_size_kw": 4.2,
        "recommended_for": "medium_home",
        "total_price": 1200,
        "payment_type": "cash",
        "installment_months": 0,
        "installation_included": True,
        "is_active": True,
        "is_popular": True,
        "display_order": 2,
        "equipment_summary": [
            "4 × 450-585W Solar Panels",
            "100Ah 24V Lithium Battery",
            "4.2 kVA Hybrid Inverter",
        ],
        "powers": [
            "Fridge",
            "TV",
            "Security Cameras",
            "Solar Iron",
            "WiFi Router",
            "Decoder",
            "Lights & Laptop",
            "Borehole Pump (0.75 HP)",
        ],
        "features": [
            "Professional supply & installation",
            "Cash on delivery",
            "Warranty & after-service support",
            "Payment after delivery & installation",
        ],
    },
    {
        "name": "6.2kVA Solar (Cash)",
        "description": (
            "Heavy-duty home solar system for large households. "
            "Powers all lights, plugs, entertainment, and multiple fridges. "
            "Supply and fix — professional installation included. "
            "Outside Harare, transport charges apply. "
            "Warranty and after-service support included."
        ),
        "system_size_kw": 6.2,
        "recommended_for": "large_home",
        "total_price": 1800,
        "payment_type": "cash",
        "installment_months": 0,
        "installation_included": True,
        "is_active": True,
        "is_popular": False,
        "display_order": 3,
        "equipment_summary": [
            "6 × 450-585W Solar Panels",
            "100Ah 51.2V Lithium Battery",
            "6.2 kVA Hybrid Inverter",
        ],
        "powers": [
            "All Lights & Plugs",
            "Entertainment Systems",
            "Up to 3 Fridges",
            "Borehole & Booster Pump (1.5 HP)",
        ],
        "features": [
            "Professional supply & installation",
            "Cash on delivery",
            "Warranty & after-service support",
            "Payment after delivery & installation",
        ],
    },
    # ──── 6-Month Payment Plan Packages ────────────────────────────────
    {
        "name": "3.5kVA Solar (6-Mo)",
        "description": (
            "Entry-level home solar system with flexible 6-month payment plan. "
            "Supply and fix — professional installation included. "
            "Outside Harare, transport charges apply. "
            "Warranty and after-service support included. "
            "Solar system on credit — pay over 6 months."
        ),
        "system_size_kw": 3.5,
        "recommended_for": "small_home",
        "total_price": 1600,
        "payment_type": "installment",
        "installment_months": 6,
        "installation_included": True,
        "is_active": True,
        "is_popular": False,
        "display_order": 4,
        "equipment_summary": [
            "4 × 450-585W Solar Panels",
            "100Ah 24V Lithium Battery",
            "3.5 kVA Hybrid Inverter",
        ],
        "powers": [
            "Fridge",
            "TV",
            "Solar Iron",
            "WiFi Router",
            "Decoder",
            "Lights & Laptop",
            "Borehole Pump (0.5 HP)",
        ],
        "features": [
            "6-month payment plan",
            "Professional supply & installation",
            "Warranty & after-service support",
            "Solar system on credit",
        ],
    },
    {
        "name": "4.2kVA Solar (6-Mo)",
        "description": (
            "Mid-range home solar system with camera support and flexible "
            "6-month payment plan. Supply and fix — professional installation "
            "included. Outside Harare, transport charges apply. "
            "Warranty and after-service support included."
        ),
        "system_size_kw": 4.2,
        "recommended_for": "medium_home",
        "total_price": 1900,
        "payment_type": "installment",
        "installment_months": 6,
        "installation_included": True,
        "is_active": True,
        "is_popular": True,
        "display_order": 5,
        "equipment_summary": [
            "4 × 450-585W Solar Panels",
            "100Ah 24V Lithium Battery",
            "4.2 kVA Hybrid Inverter",
        ],
        "powers": [
            "Fridge",
            "TV",
            "Security Cameras",
            "Solar Iron",
            "WiFi Router",
            "Decoder",
            "Lights & Laptop",
            "Borehole Pump (0.75 HP)",
        ],
        "features": [
            "6-month payment plan",
            "Professional supply & installation",
            "Warranty & after-service support",
            "Solar system on credit",
        ],
    },
    {
        "name": "6.2kVA Solar (6-Mo)",
        "description": (
            "Heavy-duty home solar system for large households with flexible "
            "6-month payment plan. Powers all lights, plugs, entertainment, "
            "and multiple fridges. Supply and fix — professional installation "
            "included. Outside Harare, transport charges apply."
        ),
        "system_size_kw": 6.2,
        "recommended_for": "large_home",
        "total_price": 2450,
        "payment_type": "installment",
        "installment_months": 6,
        "installation_included": True,
        "is_active": True,
        "is_popular": False,
        "display_order": 6,
        "equipment_summary": [
            "6 × 450-585W Solar Panels",
            "100Ah 51.2V Lithium Battery",
            "6.2 kVA Hybrid Inverter",
        ],
        "powers": [
            "All Lights & Plugs",
            "Entertainment Systems",
            "Up to 3 Fridges",
            "Borehole & Booster Pump (1.5 HP)",
        ],
        "features": [
            "6-month payment plan",
            "Professional supply & installation",
            "Warranty & after-service support",
            "Solar system on credit",
        ],
    },
]


class Command(BaseCommand):
    help = "Seeds the database with Sungrip solar packages (cash + installment plans)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing solar packages before seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            count = SolarPackage.objects.count()
            SolarPackage.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing package(s)."))

        created = 0
        updated = 0

        for pkg_data in PACKAGES:
            # Use name as the unique lookup key
            name = pkg_data['name']
            defaults = {k: v for k, v in pkg_data.items() if k != 'name'}

            obj, was_created = SolarPackage.objects.update_or_create(
                name=name,
                defaults=defaults,
            )

            if was_created:
                created += 1
                self.stdout.write(f"  ✅ Created: {obj.name} — ${obj.total_price:,.0f}")
            else:
                updated += 1
                self.stdout.write(f"  🔄 Updated: {obj.name} — ${obj.total_price:,.0f}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! {created} created, {updated} updated. "
                f"Total active packages: {SolarPackage.objects.filter(is_active=True).count()}"
            )
        )
