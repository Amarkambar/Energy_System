#!/usr/bin/env python3
"""
Email Configuration Test Script

Usage:
    python test_email.py

This script tests both password reset and alert notification emails.
"""

import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

def test_smtp_connection():
    """Test basic SMTP connection"""
    import smtplib
    
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    
    print("🔍 Testing SMTP Configuration...")
    print(f"   Host: {smtp_host}")
    print(f"   Port: {smtp_port}")
    print(f"   User: {smtp_user}")
    print(f"   Password: {'*' * len(smtp_pass) if smtp_pass else 'NOT SET'}")
    print()
    
    if not smtp_user or smtp_user == "your@gmail.com":
        print("❌ SMTP_USER not configured in .env file")
        print("   Please update backend/.env with your email credentials")
        print("   See SMTP_SETUP.md for detailed instructions")
        return False
    
    if not smtp_pass or smtp_pass == "your_password":
        print("❌ SMTP_PASSWORD not configured in .env file")
        return False
    
    try:
        print("📡 Connecting to SMTP server...")
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            print("✅ TLS connection established")
            
            server.login(smtp_user, smtp_pass)
            print("✅ Authentication successful")
            
        print()
        print("✅ SMTP configuration is valid!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("   Check your SMTP_USER and SMTP_PASSWORD in .env")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_password_reset_email(recipient: str = None):
    """Test password reset email"""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib
    
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    
    recipient = recipient or smtp_user
    
    print(f"📧 Sending test password reset email to {recipient}...")
    
    reset_link = "http://localhost:5173/reset-password?token=TEST_TOKEN_123&email=" + recipient
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "[Energy Diagnostics] Password Reset Request (TEST)"
    msg["From"] = smtp_user
    msg["To"] = recipient
    
    body = f"""
    <html><body style="font-family:Arial,sans-serif;">
    <h2>🔐 Password Reset Test</h2>
    <p>This is a <b>TEST EMAIL</b> from your Energy Diagnostics system.</p>
    <p>Click the link below to reset your password. This link expires in <b>15 minutes</b>.</p>
    <p><a href="{reset_link}" style="background:#00e5ff;color:#000;padding:10px 20px;border-radius:5px;text-decoration:none;">Reset Password</a></p>
    <p>If you did not request this, ignore this email.</p>
    <hr/>
    <p style="color:#666;font-size:12px;">This is an automated test. SMTP is configured correctly! ✅</p>
    </body></html>
    """
    msg.attach(MIMEText(body, "html"))
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [recipient], msg.as_string())
        
        print(f"✅ Password reset email sent successfully to {recipient}")
        print(f"   Check your inbox (and spam folder)")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def test_alert_email(recipient: str = None):
    """Test alert notification email"""
    from alerts.alerts_engine import EmailNotifier
    
    recipient = recipient or os.getenv("SMTP_USER")
    
    print(f"📧 Sending test alert email to {recipient}...")
    
    test_alerts = [
        {
            "rule": "High Consumption",
            "severity": "critical",
            "message": "Consumption exceeded 600 kWh at 14:30 (threshold: 500 kWh)",
            "timestamp": "2026-04-02 14:30:00"
        },
        {
            "rule": "Voltage Deviation",
            "severity": "warning",
            "message": "Voltage: 245V detected (threshold: 240V)",
            "timestamp": "2026-04-02 14:35:00"
        },
        {
            "rule": "Anomaly Detected",
            "severity": "critical",
            "message": "ML model detected unusual consumption pattern (score: 0.92)",
            "timestamp": "2026-04-02 14:40:00"
        },
        {
            "rule": "Equipment Health",
            "severity": "info",
            "message": "Preventive maintenance recommended for Unit-A3",
            "timestamp": "2026-04-02 14:45:00"
        }
    ]
    
    try:
        notifier = EmailNotifier()
        notifier.send_alert_email(test_alerts, recipients=[recipient])
        print(f"✅ Alert email sent successfully to {recipient}")
        print(f"   Check your inbox for an email with 2 critical, 1 warning, 1 info alerts")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send alert email: {e}")
        return False


def main():
    print("=" * 60)
    print("  Energy Diagnostics - Email Configuration Test")
    print("=" * 60)
    print()
    
    # Test 1: SMTP Connection
    if not test_smtp_connection():
        print()
        print("⚠️  Please fix SMTP configuration before continuing")
        print("   See backend/SMTP_SETUP.md for setup instructions")
        sys.exit(1)
    
    print()
    
    # Get recipient email
    default_recipient = os.getenv("SMTP_USER")
    print(f"📬 Recipient email (default: {default_recipient})")
    recipient_input = input(f"   Press Enter to use default, or enter different email: ").strip()
    recipient = recipient_input if recipient_input else default_recipient
    
    print()
    
    # Test 2: Password Reset Email
    success_reset = test_password_reset_email(recipient)
    print()
    
    # Test 3: Alert Email
    success_alert = test_alert_email(recipient)
    print()
    
    # Summary
    print("=" * 60)
    print("  Test Summary")
    print("=" * 60)
    print(f"  SMTP Connection:      {'✅ PASS' if True else '❌ FAIL'}")
    print(f"  Password Reset Email: {'✅ PASS' if success_reset else '❌ FAIL'}")
    print(f"  Alert Email:          {'✅ PASS' if success_alert else '❌ FAIL'}")
    print("=" * 60)
    print()
    
    if success_reset and success_alert:
        print("🎉 All tests passed! Email notifications are working correctly.")
        print()
        print("Next steps:")
        print("  1. Check your inbox for both test emails")
        print("  2. Verify emails are NOT in spam folder")
        print("  3. Update ALERT_EMAIL_RECIPIENTS in config.py if needed")
        print("  4. Test forgot-password flow in the frontend")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        print("   See SMTP_SETUP.md for troubleshooting tips")


if __name__ == "__main__":
    main()
