import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import PasswordResetOTP, UserProfile
from .sms import SMSConfigurationError, send_sms

logger = logging.getLogger(__name__)
RESET_SESSION_KEY = "password_reset_user_id"


def _e164(number):
    number = "".join(char for char in number.strip() if char.isdigit() or char == "+")
    if number.startswith("+"):
        return number
    if len(number) == 10:
        return f"+91{number}"
    return f"+{number}"


@require_http_methods(["GET", "POST"])
def forgot_password(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        user = get_user_model().objects.filter(username__iexact=username, is_active=True).first()
        if user:
            try:
                profile = user.userprofile
                phone = profile.mobile_number.strip()
            except (UserProfile.DoesNotExist, AttributeError):
                phone = ""
            if phone:
                now = timezone.now()
                reset, _ = PasswordResetOTP.objects.get_or_create(
                    user=user,
                    defaults={"otp_hash": "", "expires_at": now},
                )
                # Keep requests bounded: one OTP request per minute and no more than 5 per hour.
                if reset.window_started_at <= now - timedelta(hours=1):
                    reset.window_started_at = now
                    reset.sent_in_window = 0
                if reset.sent_in_window < 5 and (not reset.otp_hash or reset.created_at <= now - timedelta(minutes=1)):
                    otp = f"{secrets.randbelow(1_000_000):06d}"
                    try:
                        send_sms(_e164(phone), f"Your Gomti Bricks password reset code is {otp}. It expires in 10 minutes.")
                    except SMSConfigurationError:
                        logger.warning("Password reset SMS could not be delivered")
                    else:
                        reset.otp_hash = PasswordResetOTP.hash_otp(otp)
                        reset.created_at = now
                        reset.expires_at = now + timedelta(minutes=10)
                        reset.attempts = 0
                        reset.consumed = False
                        reset.sent_in_window += 1
                        reset.save()
                        request.session[RESET_SESSION_KEY] = user.pk
        # Same confirmation whether the account exists or not.
        request.session["password_reset_requested"] = True
        return redirect("password_reset")
    return render(request, "registration/forgot_password.html")


@require_http_methods(["GET", "POST"])
def password_reset(request):
    requested = request.session.pop("password_reset_requested", False)
    if request.method == "POST":
        user_id = request.session.get(RESET_SESSION_KEY)
        reset = PasswordResetOTP.objects.filter(user_id=user_id, consumed=False).first() if user_id else None
        otp = request.POST.get("otp", "").strip()
        password = request.POST.get("new_password", "")
        confirmation = request.POST.get("confirm_password", "")
        valid = bool(
            reset
            and reset.attempts < 5
            and reset.expires_at > timezone.now()
            and check_password(otp, reset.otp_hash)
        )
        if not valid:
            if reset and reset.attempts < 5:
                reset.attempts += 1
                reset.save(update_fields=["attempts"])
            return render(request, "registration/password_reset.html", {
                "error": "The code is invalid or expired. Request a new code and try again.",
            })
        user = reset.user
        if password != confirmation:
            return render(request, "registration/password_reset.html", {"error": "The passwords do not match."})
        try:
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            return render(request, "registration/password_reset.html", {"error": " ".join(exc.messages)})
        user.set_password(password)
        user.save(update_fields=["password"])
        reset.consumed = True
        reset.save(update_fields=["consumed"])
        request.session.pop(RESET_SESSION_KEY, None)
        messages.success(request, "Password changed. Sign in with your new password.")
        return redirect("login")
    return render(request, "registration/password_reset.html", {"requested": requested})
