from django.contrib import admin

from .models import Sales, Customer,Payment

class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone_number",
        "total_due",
    )
    search_fields = ("name", "phone_number")

class SalesAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "brick_type",
        "quantity",
        "price_per_brick",
        "total_amount",
        "amount_paid",
        "amount_due",
        "date",
        "is_delivered",
    )
    search_fields = (
    "customer__name",
    "customer__phone_number",
    )
    list_filter = ("is_delivered",
                    "date", "brick_type")
    def delete_queryset(self, request, queryset):
        for sale in queryset:
            sale.delete()

class PaymentAdmin(admin.ModelAdmin):
    def delete_queryset(self, request, queryset):
        for payment in queryset:
            payment.delete()


admin.site.register(Sales, SalesAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Payment, PaymentAdmin)
