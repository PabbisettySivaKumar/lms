import os
from typing import List
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel

# Check which email method to use
EMAIL_METHOD = os.getenv("EMAIL_METHOD", "smtp").lower()  # "smtp" or "graph"

# Load config from env
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@example.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.office365.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_email(to_email: str, subject: str, body: str, subtype: str = "plain"):
    """
    Send an email using either SMTP or Microsoft Graph API
    
    Set EMAIL_METHOD environment variable to:
    - "smtp" (default) - Uses SMTP
    - "graph" - Uses Microsoft Graph API (recommended for Office 365)
    """
    if EMAIL_METHOD == "graph":
        # Use Microsoft Graph API
        try:
            from backend.services.email_graph import send_email_graph
            return await send_email_graph(to_email, subject, body, subtype=subtype)
        except ImportError:
            print("Microsoft Graph API email service not available, falling back to SMTP")
        except Exception as e:
            print(f"Graph API email failed: {e}, falling back to SMTP")
    
    # Default: Use SMTP
    try:
        message = MessageSchema(
            subject=subject,
            recipients=[to_email],
            body=body,
            subtype=subtype
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
        print(f"Email sent to {to_email}")
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