from django.db import models, transaction #ensures Production and Inventory change together—or neither changes
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator


class BrickType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Inventory(models.Model):
    brick_type = models.OneToOneField(
        BrickType,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.brick_type} - {self.quantity}"


class Production(models.Model):
    brick_type=models.ForeignKey(
        BrickType,
        on_delete=models.CASCADE
    )
    quantity=models.PositiveIntegerField(default=0)
    date=models.DateField(default=timezone.localdate)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk is None:
                old_quantity = 0
                old_brick_type = self.brick_type
            else:
                old_production = Production.objects.get(pk=self.pk)
                old_quantity = old_production.quantity
                old_brick_type = old_production.brick_type

            super().save(*args, **kwargs)

            if old_brick_type == self.brick_type:
                difference = self.quantity - old_quantity

                inventory, created = Inventory.objects.get_or_create(
                    brick_type=self.brick_type
                )

                inventory.quantity = inventory.quantity + difference
                inventory.save()

            else:
                old_inventory = Inventory.objects.get(
                    brick_type=old_brick_type
                )

                old_inventory.quantity = (
                    old_inventory.quantity - old_quantity
                )
                old_inventory.save()

                new_inventory, created = Inventory.objects.get_or_create(
                    brick_type=self.brick_type
                )

                new_inventory.quantity = (
                    new_inventory.quantity + self.quantity
                )
                new_inventory.save()
    def delete(self, *args, **kwargs):
        with transaction.atomic():
            inventory = Inventory.objects.get(
                brick_type=self.brick_type
            )

            inventory.quantity = (
                inventory.quantity - self.quantity
            )
            inventory.save()

            return super().delete(*args, **kwargs)
    def __str__(self):
        return f"{self.brick_type} - {self.quantity} - {self.date}"


class Expense(models.Model):
    ELECTRICITY = "electricity"
    FUEL = "fuel"
    MISCELLANEOUS = "miscellaneous"
    CATEGORY_CHOICES = [
        (ELECTRICITY, "Electricity"),
        (FUEL, "Fuel"),
        (MISCELLANEOUS, "Miscellaneous"),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.get_category_display()} - ₹{self.amount} - {self.date}"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mobile_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            regex=r"^\+?[1-9]\d{9,14}$",
            message="Enter a 10–15 digit mobile number, optionally starting with + and country code.",
        )],
    )

    def __str__(self):
        return f"Profile for {self.user.get_username()}"


class PasswordResetOTP(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed = models.BooleanField(default=False)
    window_started_at = models.DateTimeField(default=timezone.now)
    sent_in_window = models.PositiveSmallIntegerField(default=0)

    @classmethod
    def hash_otp(cls, otp):
        return make_password(otp)
