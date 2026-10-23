from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import BrickType, Expense, Inventory, PasswordResetOTP, Production, UserProfile


class ProductionAdmin(admin.ModelAdmin):  #This lets us customize how Production behaves inside Django Admin
    def delete_queryset(self, request, queryset):
        for production in queryset:
            production.delete()


admin.site.register(BrickType)
admin.site.register(Inventory)
admin.site.register(Production, ProductionAdmin)
admin.site.register(Expense)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    max_num = 1


admin.site.unregister(get_user_model())


@admin.register(get_user_model())
class BusinessUserAdmin(UserAdmin):
    inlines = [UserProfileInline]


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "attempts", "consumed")
    readonly_fields = ("user", "otp_hash", "created_at", "expires_at", "attempts", "consumed")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
