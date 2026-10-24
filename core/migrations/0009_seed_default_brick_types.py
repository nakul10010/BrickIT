from django.db import migrations


def seed_default_brick_types(apps, schema_editor):
    BrickType = apps.get_model("core", "BrickType")
    Inventory = apps.get_model("core", "Inventory")
    database = schema_editor.connection.alias

    for name in ("4-inch", "6-inch"):
        brick_type, _ = BrickType.objects.using(database).get_or_create(name=name)
        Inventory.objects.using(database).get_or_create(
            brick_type_id=brick_type.pk,
            defaults={"quantity": 0},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_remove_passwordresetotp"),
    ]

    operations = [
        migrations.RunPython(seed_default_brick_types, migrations.RunPython.noop),
    ]
