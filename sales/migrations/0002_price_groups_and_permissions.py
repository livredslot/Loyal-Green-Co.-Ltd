"""Price groups from pending action A5, and who may see or change customers and prices."""

from django.contrib.auth.management import create_permissions
from django.db import migrations

from accounts.roles import ACCOUNTANT, DIRECTOR, PRODUCTION_LEAD, SALES_MANAGER, WAREHOUSE_LEAD

PRICE_GROUPS = ["Supermarket", "Wholesale", "Retail shop", "Hotel / restaurant"]

MODELS = ["customer", "price", "pricegroup"]
ROLE_PERMISSIONS = {
    DIRECTOR: [f"{a}_{m}" for m in MODELS for a in ("view", "add", "change")],
    SALES_MANAGER: ["view_customer", "add_customer", "change_customer", "view_price", "view_pricegroup"],
    ACCOUNTANT: ["view_customer", "view_price", "view_pricegroup"],
    PRODUCTION_LEAD: ["view_customer"],
    WAREHOUSE_LEAD: ["view_customer"],
}


def seed(apps, schema_editor):
    app_config = apps.get_app_config("sales")
    app_config.models_module = True
    create_permissions(app_config, verbosity=0, apps=apps)
    app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for role, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        group.permissions.add(*Permission.objects.filter(content_type__app_label="sales", codename__in=codenames))

    PriceGroup = apps.get_model("sales", "PriceGroup")
    for order, name in enumerate(PRICE_GROUPS, start=1):
        PriceGroup.objects.get_or_create(name=name, defaults={"order": order})


def unseed(apps, schema_editor):
    apps.get_model("sales", "PriceGroup").objects.filter(name__in=PRICE_GROUPS, prices__isnull=True, customers__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0001_initial"),
        ("core", "0002_roles"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
