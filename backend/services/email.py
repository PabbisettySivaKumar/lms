import os
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel, SecretStr
from backend.services.email_graph import send_email_graph
# Check which email method to use
EMAIL_METHOD = os.getenv("EMAIL_METHOD", "smtp").lower()  # "smtp" or "graph"

# Load config from env
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=SecretStr(os.getenv("MAIL_PASSWORD", "")),  # type: ignore
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@example.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.office365.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_email(
    to_email: str,
    subject: str,
    body: str,
    subtype: str = "plain",
    from_email: Optional[str] = None,
):
    """
    Send email via SMTP or Microsoft Graph.
    - EMAIL_METHOD=smtp: sender is MAIL_FROM; from_email ignored.
    - EMAIL_METHOD=graph: when from_email is set (e.g. manager from DB), send from that address; else MAIL_FROM.
    """
    if EMAIL_METHOD == "graph":
        try:
            result = await send_email_graph(to_email, subject, body, from_email=from_email, subtype=subtype)
            if result and from_email:
                print(f"Email sent to {to_email} from {from_email}")
            elif result:
                print(f"Email sent to {to_email}")
            return result
        except ImportError:
            print("Graph not available, falling back to SMTP")
        except Exception as e:
            print(f"Graph API failed: {e}")
            if from_email:
                print("Not falling back to SMTP (would use MAIL_FROM). Fix Graph config.")
                raise
            print("Falling back to SMTP")

    # SMTP (sender = MAIL_FROM)
    try:
        message_subtype = MessageType.plain if subtype == "plain" else MessageType.html
        message = MessageSchema(  # type: ignore
            subject=subject,
            recipients=[to_email],  # type: ignore
            body=body,
            subtype=message_subtype  # type: ignore
        )
        fm = FastMail(conf)
        await fm.send_message(message)
        sender = from_email or os.getenv("MAIL_FROM", "noreply")
        print(f"Email sent to {to_email} from {sender}")
    except Exception as e:
        # Keep original error format but add helpful message for Office 365 auth issues
        error_msg = str(e)
        print(f"Failed to send email: Exception raised {e}, check your credentials or email service configuration")
        
        # Provide helpful error messages for common Office 365 issues
        if "535" in error_msg or "Authentication unsuccessful" in error_msg:
            print("Office 365 SMTP Authentication failed. Common solutions:")
            print("1. Verify MAIL_USERNAME and MAIL_PASSWORD are correct")
            print("2. If MFA is enabled, use an App Password instead of your regular password")
            print("3. Enable 'SMTP AUTH' in Office 365 admin center (Exchange Admin Center > Mail flow > Settings)")
            print("4. Ensure the account has permission to send emails via SMTP")
            print("\n💡 Tip: Consider using Microsoft Graph API instead by setting EMAIL_METHOD=graph")