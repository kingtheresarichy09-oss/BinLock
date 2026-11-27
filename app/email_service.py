
import os

from datetime import datetime, timezone
from email.message import EmailMessage

from dotenv import load_dotenv


load_dotenv()


def get_sender_email() -> str:
    sender_email = os.getenv("SMTP_USERNAME")

    if not sender_email:
        raise RuntimeError("SMTP sender email is not configured.")

    return sender_email


def create_verification_email(
    recipient_email: str,
    verification_link: str,
) -> EmailMessage:

    message = EmailMessage()

    message["Subject"] = "Verify your BinLock account"
    message["From"] = f"BinLock <{get_sender_email()}>"
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

Thank you for registering with BinLock.

Please click the link below to verify your email address:

{verification_link}

This verification link expires in 24 hours.

If you did not create this account, you can ignore this email.

BinLock Team
"""
    )

    return message


def create_expiry_reminder_email(
    recipient_email: str,
    full_name: str,
    plan: str,
    expiry_date: datetime,
) -> EmailMessage:

    if expiry_date.tzinfo is None:
        expiry_date = expiry_date.replace(tzinfo=timezone.utc)

    expiry_text = expiry_date.astimezone(timezone.utc).strftime(
        "%d %B %Y at %H:%M UTC"
    )

    message = EmailMessage()

    message["Subject"] = "Your BinLock subscription expires soon"
    message["From"] = f"BinLock <{get_sender_email()}>"
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello {full_name},

This is a reminder that your BinLock {plan} subscription
is scheduled to expire on {expiry_text}.

Please renew your subscription before it expires to
avoid interruption to your waste collection service.

Thank you for choosing BinLock.

BinLock Team
"""
    )

    return message


def create_subscription_expired_email(
    recipient_email: str,
    full_name: str,
    plan: str,
) -> EmailMessage:

    message = EmailMessage()

    message["Subject"] = "Your BinLock subscription has expired"
    message["From"] = f"BinLock <{get_sender_email()}>"
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello {full_name},

Your BinLock {plan} subscription has expired.

To continue using BinLock waste collection services,
please renew your subscription.

Thank you for choosing BinLock.

BinLock Team
"""
    )

    return message
