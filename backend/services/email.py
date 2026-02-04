import logging
import os
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel, SecretStr
from backend.services.email_graph import send_email_graph
# Check which email method to use
logger = logging.getLogger(__name__)
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
            if result:
                logger.info("Email sent to %s from %s", to_email, from_email or "default")
            return result
        except ImportError:
            logger.warning("Graph not available, falling back to SMTP")
        except Exception as e:
            logger.warning("Graph API failed: %s", e)
            if from_email:
                logger.warning("Not falling back to SMTP (would use MAIL_FROM). Fix Graph config.")
                raise
            logger.info("Falling back to SMTP")

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
        logger.info("Email sent to %s from %s", to_email, sender)
    except Exception as e:
        error_msg = str(e)
        logger.exception("Failed to send email to %s: %s", to_email, e)
        if "535" in error_msg or "Authentication unsuccessful" in error_msg:
            logger.warning(
                "Office 365 SMTP auth failed. Verify MAIL_USERNAME/MAIL_PASSWORD, use App Password if MFA, enable SMTP AUTH. Consider EMAIL_METHOD=graph."
            )