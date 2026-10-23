from django import forms
from django.utils import timezone
from .models import Employee, Attendance, next_salary_payment_date


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["name", "designation", "photo", "salary", "borrowed_amount"]
        labels = {
            "photo": "Labour photo",
            "salary": "Pay amount (₹)",
            "borrowed_amount": "Borrowed amount (₹)",
        }
        help_texts = {
            "salary": "For Driver and Labour, this is the per-day rate. For a Manager, this is the fixed monthly salary.",
        }
        widgets = {
            "photo": forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def save(self, commit=True):
        employee = super().save(commit=False)
        employee.designation = employee.designation.strip() or "Labour"
        if not employee.salary_due_date:
            employee.salary_due_date = next_salary_payment_date()
        if commit:
            employee.save()
            self.save_m2m()
        return employee


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ["employee", "date", "status"]
        labels = {"employee": "Labour"}
        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }


class BulkAttendanceForm(forms.Form):
    employees = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.filter(is_active=True).order_by("name"),
        label="Select labour",
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Select at least one labourer."},
    )
    date = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Attendance date",
    )
    status = forms.ChoiceField(
        choices=Attendance.STATUS_CHOICES,
        initial="present",
        label="Attendance status",
    )

    def save(self):
        records = []
        for employee in self.cleaned_data["employees"]:
            record, _ = Attendance.objects.update_or_create(
                employee=employee,
                date=self.cleaned_data["date"],
                defaults={"status": self.cleaned_data["status"]},
            )
            records.append(record)
        return records
