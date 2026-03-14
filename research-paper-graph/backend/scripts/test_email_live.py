import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.email_service import register_email, send_completion_email
from dotenv import load_dotenv

def test_live():
    # Load .env
    load_dotenv()
    
    email = input("Enter recipient email for live test: ").strip()
    if not email:
        print("No email provided. Exiting.")
        return

    session_id = "live-test-session"
    query = "Autonomous Research Agents with Resend Integration"
    
    print(f"\nRegistering {email} for test...")
    register_email(session_id, email)
    
    print("Attempting to send completion email...")
    success = send_completion_email(session_id, query, 42, status="completed")
    
    if success:
        print("\n✅ SUCCESS: Email sent! Check your inbox (including Junk/Spam).")
    else:
        print("\n❌ FAILED: Email not sent. Check backend console logs/errors.")
        print("Make sure RESEND_API_KEY is correctly set in backend/.env")

if __name__ == "__main__":
    test_live()
