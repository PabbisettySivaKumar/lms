
import smtplib
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

username = os.getenv("MAIL_USERNAME")
password = os.getenv("MAIL_PASSWORD")
server = os.getenv("MAIL_SERVER", "smtp.office365.com")
port = int(os.getenv("MAIL_PORT", 587))

print(f"--- Testing SMTP Connection ---")
print(f"Server: {server}:{port}")
print(f"User: {username}")
# Do not print password

try:
    print("1. Connecting to server...")
    smtp = smtplib.SMTP(server, port)
    smtp.set_debuglevel(1)  # Show communication details
    
    print("2. Starting TLS...")
    smtp.starttls()
    
    print("3. Logging in...")
    smtp.login(username, password)
    
    print("\n✅ SUCCESS! Authentication working.")
    smtp.quit()
except Exception as e:
    print(f"\n❌ FAILED: {e}")
