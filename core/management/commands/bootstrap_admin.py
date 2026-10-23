import os

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the initial superuser from private environment variables, if configured."

    def handle(self, *args, **options):
        username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "").strip()
        password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
        email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
        if not username or not password:
            self.stdout.write("Initial admin bootstrap skipped; credentials are not configured.")
            return

        User = get_user_model()
        existing = User.objects.filter(username=username).first()
        if existing:
            if existing.is_staff and existing.is_superuser:
                self.stdout.write("Initial admin already exists; no changes made.")
                return
            raise CommandError("The bootstrap username exists but is not an administrator.")

        user = User(username=username, email=email, is_staff=True, is_superuser=True, is_active=True)
        try:
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            raise CommandError("Bootstrap password does not meet the configured password rules.") from exc
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Initial administrator '{username}' created."))
