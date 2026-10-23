from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Sales", "0008_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="sales",
            name="delivery_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sales",
            name="delivery_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sales",
            name="delivery_address",
            field=models.TextField(blank=True),
        ),
    ]
