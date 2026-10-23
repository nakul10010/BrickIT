from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch
from datetime import date
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from .forms import EmployeeForm
from .models import Attendance, Employee, SalaryPayment

# Create your tests here.


class AuthenticatedTestMixin:
    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(username="test-user", password="test-password")
        self.client.force_login(user)


class EmployeeBorrowedAmountTest(TestCase):
    def test_employee_form_saves_borrowed_amount(self):
        form = EmployeeForm(data={
            "name": "Test Employee",
            "designation": "Labour",
            "salary": "7500.00",
            "borrowed_amount": "1250.00",
        })

        self.assertTrue(form.is_valid(), form.errors)
        employee = form.save()

        self.assertEqual(employee.borrowed_amount, 1250)
        self.assertEqual(Employee.objects.get(pk=employee.pk).borrowed_amount, 1250)

    def test_worker_weekly_pay_uses_present_days_and_daily_rate(self):
        employee = Employee(
            name="Worker",
            designation="Worker",
            salary="850.00",
            borrowed_amount="0.00",
        )
        self.assertEqual(employee.weekly_pay_for_present_days(4), Decimal("3400.00"))


    def test_manager_pay_is_fixed_monthly_salary(self):
        employee = Employee(
            name="Manager",
            designation="Manager",
            salary="7500.00",
            borrowed_amount="0.00",
        )
        self.assertEqual(employee.weekly_pay_for_present_days(4), Decimal("0.00"))
        self.assertEqual(employee.monthly_pay_amount(), Decimal("7500.00"))

    def test_employee_form_accepts_labour_photo(self):
        photo = SimpleUploadedFile(
            "labour-photo.jpg",
            b"sample image data",
            content_type="image/jpeg",
        )
        form = EmployeeForm(
            data={
                "name": "Photo Labour",
                "designation": "Labour",
                "salary": "500.00",
                "borrowed_amount": "0.00",
            },
            files={"photo": photo},
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["photo"].name, "labour-photo.jpg")


class RemoveEmployeeTest(AuthenticatedTestMixin, TestCase):
    def test_removing_worker_hides_them_but_preserves_attendance_history(self):
        employee = Employee.objects.create(
            name="Departed Worker",
            designation="Labour",
            salary=Decimal("500.00"),
            borrowed_amount=Decimal("0.00"),
            salary_due_date=date(2026, 10, 28),
        )
        Attendance.objects.create(
            employee=employee,
            date=date(2026, 10, 22),
            status="present",
        )

        response = self.client.post(reverse("remove_employee", args=[employee.pk]))

        self.assertRedirects(response, reverse("employee_list"))
        employee.refresh_from_db()
        self.assertFalse(employee.is_active)
        self.assertEqual(Attendance.objects.filter(employee=employee).count(), 1)
        self.assertNotContains(self.client.get(reverse("employee_list")), "Departed Worker")

    def test_get_request_does_not_remove_worker(self):
        employee = Employee.objects.create(
            name="Still Active Worker",
            designation="Labour",
            salary=Decimal("500.00"),
            borrowed_amount=Decimal("0.00"),
            salary_due_date=date(2026, 10, 28),
        )

        self.client.get(reverse("remove_employee", args=[employee.pk]))

        employee.refresh_from_db()
        self.assertTrue(employee.is_active)


class AttendanceEditingTest(AuthenticatedTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.employee = Employee.objects.create(
            name="Test Labour",
            designation="Labour",
            salary=Decimal("500.00"),
            borrowed_amount=Decimal("0.00"),
            salary_due_date=date(2026, 10, 28),
        )
        self.attendance = Attendance.objects.create(
            employee=self.employee,
            date=date(2026, 10, 20),
            status="present",
        )

    def test_recorded_calendar_day_links_to_attendance_edit(self):
        response = self.client.get(reverse("attendance_list"), {"month": "2026-10"})

        self.assertContains(
            response,
            reverse("edit_attendance", args=[self.attendance.pk]),
        )

    def test_labour_details_page_uses_updated_title(self):
        response = self.client.get(reverse("employee_list"))

        self.assertContains(response, "Labour Details")
        self.assertContains(response, reverse("attendance_list"))
        self.assertNotContains(response, "attendance-calendar")
        self.assertContains(response, '<details class="labour-accordion">', html=False)
        self.assertContains(response, "Test Labour")
        self.assertContains(response, "Weekly pay")

    def test_attendance_section_lists_records_without_pay_details(self):
        response = self.client.get(reverse("attendance_list"), {"month": "2026-10"})

        self.assertContains(response, "Attendance records")
        self.assertContains(response, "attendance-calendar")
        self.assertContains(response, self.employee.name)
        self.assertContains(response, "Present")
        self.assertNotContains(response, "Borrowed amount")
        self.assertNotContains(response, "Salary reminder")

    def test_attendance_can_be_changed(self):
        response = self.client.post(
            reverse("edit_attendance", args=[self.attendance.pk]),
            {
                "employee": self.employee.pk,
                "date": "2026-10-20",
                "status": "absent",
            },
        )

        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, "absent")
        self.assertRedirects(response, reverse("attendance_list"))


class BulkAttendanceTest(AuthenticatedTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.labourers = [
            Employee.objects.create(
                name=name,
                designation="Labour",
                salary=Decimal("500.00"),
                borrowed_amount=Decimal("0.00"),
                salary_due_date=date(2026, 10, 28),
            )
            for name in ("Waman", "Raman")
        ]

    def test_attendance_is_saved_for_multiple_selected_labourers(self):
        response = self.client.post(
            reverse("add_attendance"),
            {
                "employees": [person.pk for person in self.labourers],
                "date": "2026-10-23",
                "status": "present",
            },
        )

        self.assertRedirects(response, reverse("attendance_list"))
        self.assertEqual(Attendance.objects.filter(date=date(2026, 10, 23)).count(), 2)
        self.assertEqual(
            set(
                Attendance.objects.filter(date=date(2026, 10, 23)).values_list(
                    "employee__name", flat=True
                )
            ),
            {"Waman", "Raman"},
        )

    def test_bulk_attendance_form_shows_labour_checkboxes(self):
        response = self.client.get(reverse("add_attendance"))

        self.assertContains(response, 'type="checkbox"')
        self.assertContains(response, "Waman")
        self.assertContains(response, "Raman")


class SalaryPaymentStatusTest(AuthenticatedTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.employee = Employee.objects.create(
            name="Pay Status Labour",
            designation="Labour",
            salary=Decimal("500.00"),
            borrowed_amount=Decimal("0.00"),
            salary_due_date=date(2026, 10, 28),
        )

    @patch("employees.views.timezone.localdate", return_value=date(2026, 10, 21))
    def test_labour_card_is_red_while_salary_is_unpaid(self, _today):
        Attendance.objects.create(
            employee=self.employee,
            date=date(2026, 10, 16),
            status="present",
        )
        response = self.client.get(reverse("employee_list"))

        self.assertContains(response, "salary-unpaid")
        self.assertContains(response, "Unpaid")

    @patch("employees.views.timezone.localdate", return_value=date(2026, 10, 21))
    def test_mark_paid_records_payment_and_turns_card_green(self, _today):
        for present_date in (date(2026, 10, 16), date(2026, 10, 19), date(2026, 10, 20), date(2026, 10, 21)):
            Attendance.objects.create(
                employee=self.employee,
                date=present_date,
                status="present",
            )
        response = self.client.post(
            reverse("mark_salary_paid", args=[self.employee.pk])
        )

        self.assertRedirects(response, reverse("employee_list"))
        payment = SalaryPayment.objects.get(employee=self.employee)
        self.assertEqual(payment.due_date, date(2026, 10, 21))
        self.assertEqual(payment.paid_date, date(2026, 10, 21))
        self.assertEqual(payment.amount_paid, Decimal("1500.00"))
        page = self.client.get(reverse("employee_list"))
        self.assertContains(page, "salary-paid-on-time")
        self.assertContains(page, "Paid on time")

    @patch("employees.views.timezone.localdate", return_value=date(2026, 10, 20))
    def test_weekly_salary_is_due_next_wednesday_for_wednesday_cycle(self, _today):
        for present_date in (date(2026, 10, 16), date(2026, 10, 19), date(2026, 10, 20)):
            Attendance.objects.create(
                employee=self.employee,
                date=present_date,
                status="present",
            )

        response = self.client.get(reverse("employee_list"))

        self.assertContains(response, "Due 21/10/2026")
        self.assertContains(response, "₹1,500.00")

    def test_monthly_pay_breakdown_uses_thursday_to_tuesday_cycles(self):
        response = self.client.get(reverse("employee_list"), {"month": "2026-10"})

        self.assertContains(response, "01/10–06/10")
        self.assertContains(response, "08/10–13/10")

    def test_first_pay_period_in_month_includes_days_from_previous_month(self):
        for present_date in (date(2026, 10, 29), date(2026, 11, 1), date(2026, 11, 3)):
            Attendance.objects.create(
                employee=self.employee,
                date=present_date,
                status="present",
            )

        response = self.client.get(reverse("employee_list"), {"month": "2026-11"})

        self.assertContains(response, "29/10–03/11 · 3 present")
