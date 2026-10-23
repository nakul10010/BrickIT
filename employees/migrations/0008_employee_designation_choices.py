from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0007_labour_default_designation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="employee",
            name="designation",
            field=models.CharField(
                choices=[("Driver", "Driver"), ("Labour", "Labour"), ("Manager", "Manager")],
                default="Labour",
                max_length=80,
            ),
        ),
    ]
