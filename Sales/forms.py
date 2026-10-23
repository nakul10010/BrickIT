from django import forms
from django.db import transaction

from .models import Customer, Sales


class SalesForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=[("", "Select payment method")] + Sales.PAYMENT_METHOD_CHOICES,
        label="Payment method",
        required=True,
    )
    new_customer_name = forms.CharField(
        label="New customer name", required=False, max_length=100
    )
    new_customer_phone = forms.CharField(
        label="Phone number", required=False, max_length=15
    )
    new_customer_address = forms.CharField(
        label="Customer address", required=False, widget=forms.Textarea(attrs={"rows": 2})
    )

    class Meta:
        model = Sales

        fields = [
            "customer",
            "brick_type",
            "quantity",
            "price_per_brick",
            "amount_paid",
            "payment_method",
            "date",
            "delivery_date",
            "delivery_time",
            "delivery_address",
            "is_delivered",
        ]
        labels = {
            "price_per_brick": "Price per brick (₹)",
            "amount_paid": "Amount paid (₹)",
            "delivery_date": "Delivery date",
            "delivery_time": "Delivery time",
            "delivery_address": "Delivery address",
        }
        help_texts = {
            "customer": "Select an existing customer, or add a new one below.",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "delivery_date": forms.DateInput(attrs={"type": "date"}),
            "delivery_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get("customer")
        new_customer_name = cleaned_data.get("new_customer_name", "").strip()
        if customer and new_customer_name:
            self.add_error("customer", "Choose an existing customer or enter a new customer, not both.")
            self.add_error("new_customer_name", "Clear this field to use the selected customer.")
        if not cleaned_data.get("delivery_address"):
            if new_customer_name:
                cleaned_data["delivery_address"] = cleaned_data.get("new_customer_address", "")
            elif customer:
                cleaned_data["delivery_address"] = customer.address
        return cleaned_data

    def save(self, commit=True):
        sale = super().save(commit=False)
        new_customer_name = self.cleaned_data.get("new_customer_name", "").strip()
        if new_customer_name:
            sale.customer = Customer(
                name=new_customer_name,
                phone_number=self.cleaned_data.get("new_customer_phone", "").strip(),
                address=self.cleaned_data.get("new_customer_address", "").strip(),
            )

        if commit:
            with transaction.atomic():
                if new_customer_name:
                    sale.customer.save()
                sale.save()
                self.save_m2m()
        return sale
