"""One handle machine makes both 7oz and 9oz handle cups (item list answer Q3, 22.11.26)."""

from django.db import migrations

OLD, NEW = "Paper Cup 7oz with handle", "Paper Cup with handle (7oz and 9oz)"


def rename(apps, schema_editor):
    apps.get_model("inventory", "Machine").objects.filter(name=OLD).update(name=NEW)


def unrename(apps, schema_editor):
    apps.get_model("inventory", "Machine").objects.filter(name=NEW).update(name=OLD)


class Migration(migrations.Migration):
    dependencies = [("inventory", "0002_seed_and_permissions")]

    operations = [migrations.RunPython(rename, unrename)]
