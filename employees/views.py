import calendar
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Employee, Attendance, SalaryPayment
from .forms import EmployeeForm, AttendanceForm, BulkAttendanceForm
from django.utils import timezone


def salary_due_date_for(employee, today):
    if employee.designation.strip().casefold() == "manager":
        due_day = employee.salary_due_day or employee.salary_due_date.day
        due_day = min(due_day, calendar.monthrange(today.year, today.month)[1])
        return date(today.year, today.month, due_day)
    days_until_wednesday = (2 - today.weekday()) % 7
    return today + timedelta(days=days_until_wednesday)


def salary_amount_due_for(employee, due_date):
    if employee.designation.strip().casefold() == "manager":
        return employee.monthly_pay_amount()
    # Thursday through Tuesday is the six-day wage period; Wednesday is payday/holiday.
    week_start = due_date - timedelta(days=6)
    week_end = due_date - timedelta(days=1)
    present_days = employee.attendance_set.filter(
        date__range=(week_start, week_end),
        status="present",
    ).count()
    return employee.weekly_pay_for_present_days(present_days)


@login_required
def employee_list(request):
    employees = Employee.objects.filter(is_active=True)
    selected_month = request.GET.get("month")

    if selected_month:
        try:
            selected_date = date.fromisoformat(f"{selected_month}-01")
        except ValueError:
            selected_date = timezone.localdate().replace(day=1)
            selected_month = selected_date.strftime("%Y-%m")
    else:
        today = timezone.localdate()
        selected_date = today.replace(day=1)
        selected_month = today.strftime("%Y-%m")

    year = selected_date.year
    month = selected_date.month
    month_pay_periods = []
    days_in_month = calendar.monthrange(year, month)[1]
    for payday_day in range(1, days_in_month + 1):
        payday = date(year, month, payday_day)
        if payday.weekday() == 2:  # Thursday–Tuesday work cycle, paid Wednesday
            month_pay_periods.append((payday - timedelta(days=6), payday - timedelta(days=1)))
    month_label = selected_date.strftime("%B %Y")
    today = timezone.localdate()

    for employee in employees:
        employee.current_salary_due_date = salary_due_date_for(employee, today)
        employee.current_salary_amount_due = salary_amount_due_for(
            employee, employee.current_salary_due_date
        )

        employee.current_salary_payment = employee.salary_payments.filter(
            due_date=employee.current_salary_due_date
        ).first()
        if employee.current_salary_amount_due <= 0:
            employee.salary_paid_on_time = False
            employee.salary_status = "no-pay-due"
            employee.salary_status_label = "No pay due"
        elif employee.current_salary_payment and employee.current_salary_payment.amount_paid >= employee.current_salary_amount_due:
            employee.salary_paid_on_time = (
                employee.current_salary_payment.paid_date <= employee.current_salary_due_date
            )
            employee.salary_status = "paid-on-time" if employee.salary_paid_on_time else "paid-late"
            employee.salary_status_label = "Paid on time" if employee.salary_paid_on_time else "Paid late"
        else:
            employee.salary_paid_on_time = False
            employee.salary_status = "unpaid"
            employee.salary_status_label = "Unpaid"
        if employee.designation.strip().casefold() == "manager":
            employee.weekly_payments = []
            employee.month_pay_total = employee.monthly_pay_amount()
        else:
            employee.weekly_payments = []
            for week_number, (period_start, period_end) in enumerate(month_pay_periods, start=1):
                present_days = employee.attendance_set.filter(
                    date__range=(period_start, period_end),
                    status="present",
                ).count()
                employee.weekly_payments.append({
                    "week_number": week_number,
                    "start_date": period_start,
                    "end_date": period_end,
                    "present_days": present_days,
                    "pay": employee.weekly_pay_for_present_days(present_days),
                })
            employee.month_pay_total = sum(
                (week["pay"] for week in employee.weekly_payments), start=0
            )

    return render(
        request,
        "employees/employee_list.html",
        {
            "employees": employees,
            "selected_month": selected_month,
            "month_label": month_label,
        },
    )


@login_required
def attendance_list(request):
    today = timezone.localdate()
    selected_month = request.GET.get("month") or today.strftime("%Y-%m")
    try:
        selected_date = date.fromisoformat(f"{selected_month}-01")
    except ValueError:
        selected_date = today.replace(day=1)
        selected_month = selected_date.strftime("%Y-%m")

    all_employees = Employee.objects.filter(is_active=True).order_by("name")
    employees = all_employees
    month_weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(
        selected_date.year, selected_date.month
    )
    selected_employee = request.GET.get("employee", "")
    if selected_employee.isdigit():
        employees = all_employees.filter(pk=int(selected_employee))

    for employee in employees:
        month_attendance = employee.attendance_set.filter(
            date__year=selected_date.year,
            date__month=selected_date.month,
        )
        attendance_by_day = {record.date.day: record for record in month_attendance}
        employee.present_days = month_attendance.filter(status="present").count()
        employee.absent_days = month_attendance.filter(status="absent").count()
        employee.holiday_days = month_attendance.filter(status="holiday").count()
        employee.attendance_weeks = [
            [
                {
                    "number": day,
                    "status": attendance_by_day[day].status if day in attendance_by_day else "",
                    "attendance_id": attendance_by_day[day].id if day in attendance_by_day else None,
                }
                if day else {"number": "", "status": "outside"}
                for day in week
            ]
            for week in month_weeks
        ]

    records = Attendance.objects.select_related("employee").filter(
        date__year=selected_date.year,
        date__month=selected_date.month,
    )
    if selected_employee.isdigit():
        records = records.filter(employee_id=int(selected_employee))
    records = records.order_by("-date", "employee__name")
    working_days_count = records.filter(status__in=("present", "absent")).dates("date", "day").count()

    return render(
        request,
        "employees/attendance_list.html",
        {
            "attendance_records": records,
            "employees": employees,
            "all_employees": all_employees,
            "selected_employee": selected_employee,
            "selected_month": selected_month,
            "month_label": selected_date.strftime("%B %Y"),
            "working_days_count": working_days_count,
            "present_count": records.filter(status="present").count(),
            "absent_count": records.filter(status="absent").count(),
            "holiday_count": records.filter(status="holiday").count(),
        },
    )

@login_required
def add_employee(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect("employee_list")
    else:
        form = EmployeeForm()

    return render(
        request,
        "employees/employee_form.html",
        {"form": form},
    )


@login_required
def edit_employee(request, employee_id):
    employee = Employee.objects.get(pk=employee_id)
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            return redirect("employee_list")
    else:
        form = EmployeeForm(instance=employee)

    return render(
        request,
        "employees/employee_form.html",
        {"form": form, "is_edit": True, "employee": employee},
    )


@login_required
def remove_employee(request, employee_id):
    if request.method == "POST":
        employee = get_object_or_404(Employee, pk=employee_id, is_active=True)
        employee.is_active = False
        employee.save(update_fields=["is_active"])
    return redirect("employee_list")


@login_required
def employee_detail(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    today = timezone.localdate()
    due_date = salary_due_date_for(employee, today)
    amount_due = salary_amount_due_for(employee, due_date)
    payment = employee.salary_payments.filter(due_date=due_date).first()
    if amount_due <= 0:
        salary_status = "No pay due"
    elif payment and payment.amount_paid >= amount_due:
        salary_status = "Paid on time" if payment.paid_date <= due_date else "Paid late"
    else:
        salary_status = "Unpaid"

    attendance = employee.attendance_set.order_by("-date")
    return render(
        request,
        "employees/employee_detail.html",
        {
            "employee": employee,
            "attendance_records": attendance[:30],
            "salary_payments": employee.salary_payments.all()[:12],
            "present_total": attendance.filter(status="present").count(),
            "absent_total": attendance.filter(status="absent").count(),
            "holiday_total": attendance.filter(status="holiday").count(),
            "current_salary_due_date": due_date,
            "current_salary_amount_due": amount_due,
            "salary_status_label": salary_status,
        },
    )


@login_required
def add_attendance(request):
    if request.method == "POST":
        form = BulkAttendanceForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("attendance_list")
    else:
        form = BulkAttendanceForm()

    return render(
        request,
        "employees/bulk_attendance_form.html",
        {"form": form},
    )


@login_required
def edit_attendance(request, attendance_id):
    attendance = get_object_or_404(Attendance, pk=attendance_id)
    if request.method == "POST":
        form = AttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            form.save()
            return redirect("attendance_list")
    else:
        form = AttendanceForm(instance=attendance)

    return render(
        request,
        "employees/attendance_form.html",
        {"form": form, "is_edit": True, "attendance": attendance},
    )


@login_required
def mark_salary_paid(request, employee_id):
    if request.method != "POST":
        return redirect("employee_list")

    employee = get_object_or_404(Employee, pk=employee_id)
    today = timezone.localdate()
    due_date = salary_due_date_for(employee, today)
    amount_due = salary_amount_due_for(employee, due_date)
    if amount_due <= 0:
        return redirect("employee_list")

    SalaryPayment.objects.update_or_create(
        employee=employee,
        due_date=due_date,
        defaults={"paid_date": today, "amount_paid": amount_due},
    )
    return redirect("employee_list")
