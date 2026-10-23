from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0005_employee_borrowed_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="designation",
            field=models.CharField(default="Worker", max_length=80),
        ),
    ]
