"""Who may see or change suppliers."""

from django.contrib.auth.management import create_permissions
from django.db import migrations

from accounts.roles import ACCOUNTANT, DIRECTOR, PRODUCTION_LEAD, SALES_MANAGER, WAREHOUSE_LEAD

ROLE_PERMISSIONS = {
    DIRECTOR: ["view_supplier", "add_supplier", "change_supplier"],
    ACCOUNTANT: ["view_supplier", "add_supplier", "change_supplier"],
    SALES_MANAGER: ["view_supplier"],
    PRODUCTION_LEAD: ["view_supplier"],
    WAREHOUSE_LEAD: ["view_supplier"],
}


def seed(apps, schema_editor):
    app_config = apps.get_app_config("purchasing")
    app_config.models_module = True
    create_permissions(app_config, verbosity=0, apps=apps)
    app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for role, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        group.permissions.add(*Permission.objects.filter(content_type__app_label="purchasing", codename__in=codenames))


class Migration(migrations.Migration):
    dependencies = [
        ("purchasing", "0001_initial"),
        ("core", "0002_roles"),
    ]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
