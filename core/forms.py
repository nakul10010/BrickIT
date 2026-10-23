from django import forms

from .models import Expense, Production


class ProductionForm(forms.ModelForm):

    class Meta:
        model = Production

        fields = [
            "brick_type",
            "quantity",
            "date",
        ]


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["category", "amount", "date", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "note": forms.TextInput(attrs={"placeholder": "Optional details"}),
        }
