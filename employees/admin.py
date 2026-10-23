from django.contrib import admin

# Register your models here.
from .models import Employee, Attendance, SalaryPayment

admin.site.register(Employee)
admin.site.register(Attendance)
admin.site.register(SalaryPayment)
