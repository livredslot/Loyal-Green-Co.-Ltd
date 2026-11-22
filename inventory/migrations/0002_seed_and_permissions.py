"""Stock locations and machines from the pending-actions form (A10), and who may change what."""

from django.contrib.auth.management import create_permissions
from django.db import migrations

from accounts.roles import ACCOUNTANT, DIRECTOR, PRODUCTION_LEAD, SALES_MANAGER, WAREHOUSE_LEAD

LOCATIONS = [
    ("RAW", "Raw material store"),
    ("FG", "Finished goods area"),
    ("REPACK", "Repack area"),
]

# name, output per hour (pcs), note
MACHINES = [
    ("Paper Cup 7oz (1)", 2000, ""),
    ("Paper Cup 7oz (2)", 2000, ""),
    ("Paper Cup 7oz with handle", 2000, ""),
    ("Paper Cup 9oz", 2000, ""),
    ("Paper Bowl", 2000, ""),
    ("Paper Plate", 3000, "Two machines, 7\" and 9\""),
    ("Noodle Bowl", 720, ""),
    ("Packing Machine", 1500, "Packs cups, plates and bowls"),
]

MODELS = ["item", "category", "location", "machine", "recipe", "recipeline"]
VIEW_ALL = [f"view_{m}" for m in MODELS]
ROLE_PERMISSIONS = {
    DIRECTOR: VIEW_ALL + [f"{a}_{m}" for m in MODELS for a in ("add", "change")],
    PRODUCTION_LEAD: VIEW_ALL + [f"{a}_{m}" for m in ("recipe", "recipeline", "machine") for a in ("add", "change")],
    SALES_MANAGER: VIEW_ALL,
    ACCOUNTANT: VIEW_ALL,
    WAREHOUSE_LEAD: VIEW_ALL,
}


def seed(apps, schema_editor):
    app_config = apps.get_app_config("inventory")
    app_config.models_module = True
    create_permissions(app_config, verbosity=0, apps=apps)
    app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for role, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        group.permissions.add(*Permission.objects.filter(content_type__app_label="inventory", codename__in=codenames))

    Location = apps.get_model("inventory", "Location")
    for code, name in LOCATIONS:
        Location.objects.get_or_create(code=code, defaults={"name": name})

    Machine = apps.get_model("inventory", "Machine")
    for name, output, note in MACHINES:
        Machine.objects.get_or_create(name=name, defaults={"output_per_hour": output, "notes": note})


def unseed(apps, schema_editor):
    apps.get_model("inventory", "Location").objects.filter(code__in=[c for c, _ in LOCATIONS]).delete()
    apps.get_model("inventory", "Machine").objects.filter(name__in=[n for n, _, _ in MACHINES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0001_initial"),
        ("core", "0002_roles"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
