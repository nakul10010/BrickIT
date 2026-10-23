from django.db import migrations, models


def rename_worker_designations(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    Employee.objects.filter(designation="Worker").update(designation="Labour")


def restore_worker_designations(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    Employee.objects.filter(designation="Labour").update(designation="Worker")


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0006_employee_designation"),
    ]

    operations = [
        migrations.RunPython(rename_worker_designations, restore_worker_designations),
        migrations.AlterField(
            model_name="employee",
            name="designation",
            field=models.CharField(default="Labour", max_length=80),
        ),
    ]
