# SMTP Email Configuration Guide

This guide walks you through configuring email notifications for password reset and alert notifications in the Energy Diagnostics system.

---

## 🎯 What Gets Enabled

Once SMTP is configured, the following features will work:

1. **Password Reset Emails** - Users receive a clickable link to reset their password (15-minute expiry)
2. **Alert Notifications** - System sends email digests when critical/warning alerts are triggered
3. **User Registration** - Optional welcome emails (can be added)

**Current Implementation**:

- `backend/api.py` lines 169-215: Forgot password email
- `backend/alerts/alerts_engine.py` lines 168-227: Alert notification emails

---

## 📧 Option 1: Gmail (Easiest for Testing)

### Step 1: Enable App Password in Gmail

1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already)
3. Scroll down to **App passwords**
4. Select app: **Mail**, device: **Other (Custom name)** → Enter "Energy Diagnostics"
5. Click **Generate** → Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### Step 2: Update `.env` File

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # App password from Step 1 (remove spaces)
```

### Step 3: Test

```bash
# Restart backend
cd backend
python api.py

# Test forgot-password endpoint
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "your.email@gmail.com"}'
```

Check your inbox for the reset email!

---

## 📧 Option 2: SendGrid (Recommended for Production)

SendGrid offers 100 emails/day free, better deliverability, and no Gmail rate limits.

### Step 1: Create SendGrid Account

1. Sign up: https://signup.sendgrid.com/
2. Verify your email
3. Complete sender identity verification

### Step 2: Create API Key

1. Go to **Settings** → **API Keys**
2. Click **Create API Key**
3. Name: "Energy Diagnostics Production"
4. Permissions: **Full Access** (or Restricted with Mail Send only)
5. Copy the API key (e.g., `SG.abc123...`)

### Step 3: Update `.env` File

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey  # Literally the word "apikey"
SMTP_PASSWORD=SG.abc123...  # Your API key from Step 2
```

### Step 4: Verify Sender Email

SendGrid requires sender verification:

1. Go to **Settings** → **Sender Authentication**
2. Choose **Single Sender Verification** (easier) or **Domain Authentication** (production)
3. Verify the email you'll use in `SMTP_USER`

### Step 5: Test

Same as Gmail test above. SendGrid logs all emails in the dashboard under **Activity**.

---

## 📧 Option 3: AWS SES (Best for Scale)

AWS Simple Email Service offers 62,000 emails/month free (first 12 months).

### Step 1: Set Up AWS SES

1. Go to AWS Console → **SES (Simple Email Service)**
2. Click **Verify a New Email Address**
3. Enter your sender email (e.g., `alerts@yourdomain.com`)
4. Check inbox and click verification link

### Step 2: Create SMTP Credentials

1. In SES console, go to **SMTP Settings**
2. Click **Create My SMTP Credentials**
3. Save the **SMTP Username** and **SMTP Password**

### Step 3: Request Production Access

By default, SES is in **Sandbox Mode** (can only send to verified emails).

1. Go to **Sending Statistics** → **Request Production Access**
2. Fill out the form (takes 24 hours)

### Step 4: Update `.env` File

```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com  # Change region if needed
SMTP_PORT=587
SMTP_USER=AKIAIOSFODNN7EXAMPLE  # From Step 2
SMTP_PASSWORD=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  # From Step 2
```

---

## 📧 Option 4: Outlook/Office365

### Step 1: Update `.env` File

```bash
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your.email@outlook.com  # or @hotmail.com
SMTP_PASSWORD=your_outlook_password  # Use regular password or app password
```

**Note**: Office365 may require app-specific password if 2FA is enabled.

---

## 🧪 Testing Your Configuration

### Test 1: Password Reset Email

```bash
# Using curl
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Expected response if SMTP works:
# {"message": "Reset link sent to your email", "email": "test@example.com"}
```

### Test 2: Alert Notifications

```python
# backend/test_email.py
from alerts.alerts_engine import EmailNotifier

notifier = EmailNotifier()
test_alerts = [
    {
        "rule": "High Consumption",
        "severity": "critical",
        "message": "Consumption exceeded 600 kWh at 14:30"
    },
    {
        "rule": "Voltage Deviation",
        "severity": "warning",
        "message": "Voltage: 245V (threshold: 240V)"
    }
]

notifier.send_alert_email(test_alerts, recipients=["your@email.com"])
print("Check your inbox!")
```

Run: `python backend/test_email.py`

---

## 🔒 Security Best Practices

### 1. Never Commit Credentials to Git

Add to `.gitignore`:

```
.env
*.env
.env.local
.env.production
```

### 2. Use Environment Variables in Production

For Docker deployments:

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
```

Then set in host `.env` or use Docker secrets.

### 3. Rotate API Keys Regularly

- SendGrid: Rotate every 90 days
- AWS SES: Use IAM roles instead of keys when possible

---

## ⚙️ Advanced Configuration

### Custom Email Templates

Edit templates in:

- **Password Reset**: `backend/api.py` line 193
- **Alerts**: `backend/alerts/alerts_engine.py` line 186

### Add Rate Limiting

To prevent email abuse, add rate limiting to forgot-password:

```python
# backend/api.py (after line 177)
_rate_limit = {}  # email -> last_sent_time

@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    email = req.email.lower()
    now = time.time()

    # Rate limit: 1 email per 5 minutes
    if email in _rate_limit and now - _rate_limit[email] < 300:
        raise HTTPException(429, "Please wait 5 minutes before requesting another reset")

    _rate_limit[email] = now
    # ... rest of function
```

### Configure Alert Recipients

Edit `backend/config.py`:

```python
ALERT_EMAIL_RECIPIENTS = [
    "admin@company.com",
    "ops@company.com",
    "alerts@company.com"
]
```

Or make it dynamic via settings API:

```bash
POST /api/settings/thresholds
{
  "alert_email_recipients": ["admin@company.com", "engineer@company.com"]
}
```

---

## 📊 Monitoring Email Delivery

### Gmail

- Check **Sent** folder
- Monitor quota: 500 emails/day for regular accounts, 2000/day for Google Workspace

### SendGrid

- Dashboard → **Activity** → View delivery status
- Set up **Event Webhooks** for bounce/spam tracking

### AWS SES

- CloudWatch metrics: Sends, Bounces, Complaints
- Enable **Configuration Sets** for detailed tracking

---

## 🐛 Troubleshooting

### Error: "SMTP AUTH extension not supported"

**Solution**: Check SMTP_PORT (should be 587 for TLS, not 465)

### Error: "Username and Password not accepted"

**Solution**:

- Gmail: Use App Password, not regular password
- SendGrid: Ensure `SMTP_USER=apikey` (literal word)
- AWS SES: Verify SMTP credentials are correct

### Error: "Connection timeout"

**Solution**:

- Check firewall allows outbound port 587
- Verify SMTP_HOST is correct
- Try port 465 (SSL) or 2525 (alternative)

### Emails Go to Spam

**Solution**:

- Use verified sender domain (not Gmail for production)
- Set up SPF/DKIM records (SendGrid/AWS SES guides)
- Add unsubscribe link in alert emails

### No Error, But Email Not Received

**Solution**:

- Check spam folder
- Verify recipient email is correct
- Check SendGrid/SES logs for delivery status
- Test with a different recipient email

---

## ✅ Post-Configuration Checklist

- [ ] `.env` file updated with SMTP credentials
- [ ] Credentials are NOT committed to Git
- [ ] Backend restarted after `.env` changes
- [ ] Forgot-password email tested and received
- [ ] Alert notification email tested and received
- [ ] Emails NOT going to spam
- [ ] Rate limiting configured (optional)
- [ ] Multiple recipient emails tested (optional)
- [ ] Production SMTP provider chosen (SendGrid/AWS SES)

---

## 🚀 Next Steps

Once SMTP is working:

1. **Add welcome emails** on user registration
2. **Schedule daily alert digests** (instead of real-time)
3. **Add email templates** with company branding
4. **Implement unsubscribe functionality**
5. **Set up bounce/complaint handling**

**Estimated Setup Time**: 15-30 minutes (Gmail), 1-2 hours (SendGrid/AWS SES with domain verification)
