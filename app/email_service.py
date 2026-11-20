
import os

from dotenv import load_dotenv
from email.message import EmailMessage


load_dotenv()


def create_verification_email(
    recipient_email: str,
    verification_link: str
) -> EmailMessage:

    sender_email = os.getenv("SMTP_USERNAME")

    if not sender_email:
        raise RuntimeError("SMTP sender email is not configured.")

    message = EmailMessage()

    message["Subject"] = "Verify your BinLock account"
    message["From"] = f"BinLock <{sender_email}>"
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
