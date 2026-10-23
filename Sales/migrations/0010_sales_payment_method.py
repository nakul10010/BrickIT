from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Sales", "0009_sales_delivery_details"),
    ]

    operations = [
        migrations.AddField(
            model_name="sales",
            name="payment_method",
            field=models.CharField(
                blank=True,
                choices=[("cash", "Cash"), ("card", "Card"), ("cheque", "Cheque"), ("upi", "UPI")],
                default="",
                max_length=10,
            ),
        ),
    ]
