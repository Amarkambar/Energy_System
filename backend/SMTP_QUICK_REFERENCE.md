# SMTP Quick Reference Card

## ⚡ Quick Setup (5 minutes)

### Gmail (Testing)

```bash
# 1. Get app password: https://myaccount.google.com/apppasswords
# 2. Update .env:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # Remove spaces from app password

# 3. Test
python test_email.py
```

### SendGrid (Production)

```bash
# 1. Sign up: https://signup.sendgrid.com/
# 2. Create API key with Mail Send permission
# 3. Update .env:
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your_api_key_here

# 4. Test
python test_email.py
```

---

## 🔧 What Works Now

✅ **Password Reset Emails** (`/api/auth/forgot-password`)

- User receives clickable reset link
- Link expires in 15 minutes
- HTML formatted email

✅ **Alert Notifications** (via `EmailNotifier` class)

- Critical/Warning/Info severity levels
- Grouped by severity in email body
- Sent to `ALERT_EMAIL_RECIPIENTS` list

---

## 📝 Files Modified

| File            | Purpose                              |
| --------------- | ------------------------------------ |
| `SMTP_SETUP.md` | Complete setup guide (all providers) |
| `test_email.py` | Test script for email configuration  |
| `.env.example`  | Updated with SMTP options            |
| `README.md`     | Added email setup instructions       |

---

## ⚙️ Configuration

### Single Recipient

```python
# config.py
ALERT_EMAIL_RECIPIENTS = ["admin@company.com"]
```

### Multiple Recipients

```python
# config.py
ALERT_EMAIL_RECIPIENTS = [
    "admin@company.com",
    "ops@company.com",
    "alerts@company.com"
]
```

---

## 🧪 Test Commands

```bash
# Test full email setup
python test_email.py

# Test via API
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com"}'
```

---

## 🐛 Troubleshooting

| Issue                                | Solution                                                  |
| ------------------------------------ | --------------------------------------------------------- |
| "SMTP AUTH extension not supported"  | Use port 587 (not 465)                                    |
| "Username and Password not accepted" | Gmail: Use app password. SendGrid: Use `SMTP_USER=apikey` |
| Emails go to spam                    | Use SendGrid/AWS SES with verified domain                 |
| No error but email not received      | Check spam folder, verify recipient email                 |

Full troubleshooting guide: `SMTP_SETUP.md`

---

## ⏱️ Setup Time Estimates

- **Gmail (testing)**: 5 minutes
- **SendGrid (production)**: 30 minutes
- **AWS SES (scale)**: 1-2 hours (includes domain verification)

---

## 📚 See Also

- Full setup guide: `SMTP_SETUP.md`
- Email API code: `api.py` lines 169-215
- Alert emails: `alerts/alerts_engine.py` lines 168-227
- Configuration: `config.py` lines 27-31
