from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from core import auth_views as core_auth_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/password-reset/", core_auth_views.forgot_password, name="forgot_password"),
    path("accounts/password-reset/verify/", core_auth_views.password_reset, name="password_reset"),
    path("", include("core.urls")),
    path("", include("Sales.urls")),
    path("employees/", include("employees.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
