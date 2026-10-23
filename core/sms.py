import base64
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class SMSConfigurationError(Exception):
    pass


def send_sms(to_number, message):
    """Send an SMS using Twilio Programmable Messaging, configured only via env settings."""
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    sender = settings.TWILIO_FROM_NUMBER
    if not all((account_sid, auth_token, sender)):
        raise SMSConfigurationError("SMS delivery is not configured")

    endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = urlencode({"To": to_number, "From": sender, "Body": message}).encode()
    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    request = Request(endpoint, data=payload, headers={
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode())
            if response.status >= 300 or result.get("status") == "failed":
                raise SMSConfigurationError("SMS provider rejected the message")
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise SMSConfigurationError("SMS delivery failed") from exc
