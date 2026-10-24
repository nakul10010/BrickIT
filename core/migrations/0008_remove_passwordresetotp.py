from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_alter_userprofile_mobile_number"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PasswordResetOTP",
        ),
    ]
