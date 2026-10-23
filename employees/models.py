# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.core.validators import FileExtensionValidator


def next_salary_payment_date():
    today = timezone.localdate()
    days_until_wednesday = (2 - today.weekday()) % 7
    return today + timedelta(days=days_until_wednesday)

class Employee(models.Model):
    DESIGNATION_CHOICES = [
        ("Driver", "Driver"),
        ("Labour", "Labour"),
        ("Manager", "Manager"),
    ]

    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    designation = models.CharField(max_length=80, choices=DESIGNATION_CHOICES, default="Labour")
    photo = models.FileField(
        upload_to="labour_photos/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    borrowed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    salary_due_date = models.DateField()
    salary_due_day = models.PositiveSmallIntegerField(
    "Salary due day",
    null=True,
    validators=[MinValueValidator(1), MaxValueValidator(31)],
)
    def __str__(self):
        return self.name

    def weekly_pay_for_present_days(self, present_days):
        if self.designation.strip().casefold() == "manager":
            return Decimal("0.00")
        return Decimal(self.salary) * present_days

    def monthly_pay_amount(self):
        if self.designation.strip().casefold() == "manager":
            return Decimal(self.salary)
        return Decimal("0.00")
class Attendance(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("holiday", "Holiday"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="present",
    )


class SalaryPayment(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="salary_payments",
    )
    due_date = models.DateField()
    paid_date = models.DateField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "due_date"],
                name="unique_salary_payment_per_due_date",
            )
        ]
        ordering = ["-due_date"]

    def __str__(self):
        return f"{self.employee} salary due {self.due_date}: paid {self.paid_date}"
