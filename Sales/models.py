from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from core.models import BrickType, Inventory
# Create your models here.
class Customer(models.Model):
    name=models.CharField(max_length=100)
    phone_number=models.CharField(max_length=15,blank=True)
    address=models.TextField(blank=True)

    def total_due(self):
        total = 0

        customer_sales = Sales.objects.filter(
            customer=self
        )

        for sale in customer_sales:
            total = total + sale.amount_due()

        return total

    def __str__(self):
        return self.name
class Sales(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("cash", "Cash"),
        ("card", "Card"),
        ("cheque", "Cheque"),
        ("upi", "UPI"),
    ]

    customer = models.ForeignKey(
    Customer,
    on_delete=models.PROTECT,
    null=True,
    blank=True
    )

    brick_type = models.ForeignKey(
        BrickType,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()
    price_per_brick = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        default="",
    )

    date = models.DateField(default=timezone.localdate)
    is_delivered = models.BooleanField(default=False)
    delivery_date = models.DateField(null=True, blank=True)
    delivery_time = models.TimeField(null=True, blank=True)
    delivery_address = models.TextField(blank=True)

    def clean(self):
        inventory = Inventory.objects.get(
            brick_type=self.brick_type
        )

        available_quantity = inventory.quantity

        if self.pk is not None:
            old_sale = Sales.objects.get(pk=self.pk)

            if old_sale.brick_type == self.brick_type:
                available_quantity = (
                    available_quantity + old_sale.quantity
                )

        if self.quantity > available_quantity:
            raise ValidationError({
                "quantity": "Not enough bricks in inventory."
            })
        if self.amount_paid < 0:
            raise ValidationError({
                "amount_paid": "Amount paid cannot be negative."
            })

        if self.amount_paid > self.total_amount():
            raise ValidationError({
                "amount_paid": "Amount paid cannot exceed the total amount."
            })
    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk is None:
                old_quantity = 0
                old_brick_type = self.brick_type
            else:
                old_sale = Sales.objects.get(pk=self.pk)
                old_quantity = old_sale.quantity
                old_brick_type = old_sale.brick_type

            if old_brick_type == self.brick_type:
                difference = self.quantity - old_quantity

                inventory = Inventory.objects.get(
                    brick_type=self.brick_type
                )

                if difference > inventory.quantity:
                    raise ValidationError(
                        "Not enough bricks in inventory."
                    )

                super().save(*args, **kwargs)

                inventory.quantity = (
                    inventory.quantity - difference
                )
                inventory.save()

            else:
                old_inventory = Inventory.objects.get(
                    brick_type=old_brick_type
                )

                new_inventory = Inventory.objects.get(
                    brick_type=self.brick_type
                )

                if self.quantity > new_inventory.quantity:
                    raise ValidationError(
                        "Not enough bricks in the new inventory."
                    )

                super().save(*args, **kwargs)

                old_inventory.quantity = (
                    old_inventory.quantity + old_quantity
                )
                old_inventory.save()

                new_inventory.quantity = (
                    new_inventory.quantity - self.quantity
                )
                new_inventory.save()
    def delete(self, *args, **kwargs):
        with transaction.atomic():
            inventory = Inventory.objects.get(
                brick_type=self.brick_type
            )

            inventory.quantity = (
                inventory.quantity + self.quantity
            )
            inventory.save()

            return super().delete(*args, **kwargs)
        
    def total_amount(self):
        return self.quantity * self.price_per_brick
    def amount_due(self):
        return self.total_amount() - self.amount_paid
    def __str__(self):
        if self.customer:
            return (
                f"{self.customer.name} - "
                f"{self.brick_type} - "
                f"{self.quantity} - "
                f"{self.date}"
            )

        return (
            f"No customer - "
            f"{self.brick_type} - "
            f"{self.quantity} - "
            f"{self.date}"
        )
class Payment(models.Model):
    sale = models.ForeignKey(
        Sales,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    date = models.DateField(
        default=timezone.localdate
    )

    payment_method = models.CharField(
        max_length=20,
        blank=True
    )

    note = models.CharField(
        max_length=200,
        blank=True
    )
    def clean(self):
        if self.amount <= 0:
            raise ValidationError({
                "amount": "Payment must be greater than zero."
            })

        available_due = self.sale.amount_due()

        if self.pk is not None:
            old_payment = Payment.objects.get(
                pk=self.pk
            )

            if old_payment.sale == self.sale:
                available_due = (
                    available_due + old_payment.amount
                )

        if self.amount > available_due:
            raise ValidationError({
                "amount": "Payment cannot exceed the amount due."
            })
    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk is None:
                old_amount = 0

            else:
                old_payment = Payment.objects.get(
                    pk=self.pk
                )

                if old_payment.sale != self.sale:
                    raise ValidationError(
                        "The Sale on a Payment cannot be changed."
                    )

                old_amount = old_payment.amount

            sale = Sales.objects.get(
                pk=self.sale.pk
            )

            difference = self.amount - old_amount

            if self.amount <= 0:
                raise ValidationError(
                    "Payment must be greater than zero."
                )

            if difference > sale.amount_due():
                raise ValidationError(
                    "Payment cannot exceed the amount due."
                )

            super().save(*args, **kwargs)

            sale.amount_paid = (
                sale.amount_paid + difference
            )
            sale.save()

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            sale = Sales.objects.get(
                pk=self.sale.pk
            )

            sale.amount_paid = (
                sale.amount_paid - self.amount
            )
            sale.save()

        return super().delete(*args, **kwargs)
    def __str__(self):
        return f"{self.sale} - ₹{self.amount} - {self.date}"
