from django.urls import path
from . import views

urlpatterns = [
    path("", views.employee_list, name="employee_list"),
    path("attendance/", views.attendance_list, name="attendance_list"),
    path("add/", views.add_employee, name="add_employee"),
    path("<int:employee_id>/details/", views.employee_detail, name="employee_detail"),
    path("<int:employee_id>/edit/", views.edit_employee, name="edit_employee"),
    path("<int:employee_id>/remove/", views.remove_employee, name="remove_employee"),
    path("attendance/add/", views.add_attendance, name="add_attendance"),
    path("attendance/<int:attendance_id>/edit/", views.edit_attendance, name="edit_attendance"),
    path("<int:employee_id>/salary/mark-paid/", views.mark_salary_paid, name="mark_salary_paid"),

]
