"""
Email service using Microsoft Graph API
This is an alternative to SMTP that works better with Office 365 and MFA
"""
import os
import httpx  # type: ignore
from typing import Optional

# Microsoft Graph API endpoint
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"

async def get_access_token() -> Optional[str]:
    """
    Get OAuth2 access token for Microsoft Graph API
    
    You can get a token using:
    1. Client credentials flow (for app-only access)
    2. Delegated permissions (for user access)
    
    For simplicity, we'll use a token from environment variable.
    For production, implement proper OAuth2 flow with msal library.
    """
    # Option 1: Use token from environment (for testing)
    token = os.getenv("GRAPH_API_TOKEN", "")
    if token:
        return token
    
    # Option 2: Use client credentials (requires Azure App Registration)
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    
    if client_id and client_secret and tenant_id:
        # Get token using client credentials flow
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                print(f"Failed to get access token: {response.status_code} - {response.text}")
                return None
    
    return None

async def send_email_graph(
    to_email: str, 
    subject: str, 
    body: str, 
    from_email: Optional[str] = None,
    subtype: str = "plain"
) -> bool:
    """
    Send an email using Microsoft Graph API
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (HTML or plain text)
        from_email: Sender email (defaults to MAIL_FROM env var)
        subtype: "html" or "plain"
    
    Returns:
        bool: True if email was sent successfully
    """
    try:
        # Get access token
        access_token = await get_access_token()
        if not access_token:
            print("Failed to get Microsoft Graph API access token")
            print("Please set GRAPH_API_TOKEN or configure Azure App credentials")
            return False
        
        # Get sender email
        sender_email = from_email or os.getenv("MAIL_FROM", "")
        if not sender_email:
            print("MAIL_FROM environment variable is not set")
            return False
        
        # Prepare email message
        content_type = "html" if subtype == "html" else "text"
        
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": content_type,
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            }
        }
        
        # Send email via Graph API
        send_url = f"{GRAPH_API_ENDPOINT}/users/{sender_email}/sendMail"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                send_url,
                json=message,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            if response.status_code == 202:
                print(f"Email sent successfully to {to_email} via Microsoft Graph API")
                return True
            else:
                error_msg = response.text
                print(f"Failed to send email via Graph API: {response.status_code} - {error_msg}")
                
                # Provide helpful error messages
                if response.status_code == 401:
                    print("Authentication failed. Check your access token or Azure App credentials")
                elif response.status_code == 403:
                    print("Permission denied. Ensure the app has 'Mail.Send' permission")
                elif response.status_code == 404:
                    print(f"User '{sender_email}' not found or doesn't have a mailbox")
                
                return False
                
    except Exception as e:
        print(f"Error sending email via Graph API: {e}")
        import traceback
        traceback.print_exc()
        return False
