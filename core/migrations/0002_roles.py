"""Creates the five role groups and the company profile row."""

from django.contrib.auth.management import create_permissions
from django.db import migrations

from accounts.roles import ROLE_PERMISSIONS


def create_roles(apps, schema_editor):
    # Permissions are normally created after all migrations run; make sure
    # core's exist now so they can be given to the groups.
    # (Historical app configs have no models_module, which create_permissions checks.)
    app_config = apps.get_app_config("core")
    app_config.models_module = True
    create_permissions(app_config, verbosity=0, apps=apps)
    app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for role, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        group.permissions.add(*Permission.objects.filter(content_type__app_label="core", codename__in=codenames))

    CompanyProfile = apps.get_model("core", "CompanyProfile")
    CompanyProfile.objects.get_or_create(pk=1)


def remove_roles(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=ROLE_PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(create_roles, remove_roles)]
