from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0004_employee_salary_due_day"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="borrowed_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
