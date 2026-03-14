# Email Notifications Configuration Guide

## ✅ Current Status

Your email notification system is **fully configured and ready to use**!

- ✅ **Mailtrap API Token**: Active in `.env` file
- ✅ **Backend Email Service**: Implemented and working
- ✅ **Frontend UI**: Ready with email subscription toast
- ✅ **Database**: Emails stored persistently in `data/pipeline_storage/email_subscriptions.json`

---

## 🎯 How It Works

### Workflow

1. **User starts research analysis** → Toast appears: "Get notified when done?"
2. **User provides email** → System registers email for that session
3. **Pipeline completes** → Automatic email sent with link back to results
4. **Email received** → User clicks link to return to their session

### Architecture

```
Frontend (EmailNotifyToast)
    ↓ (POST /notify/register)
API Gateway (/api/v1/notify/register)
    ↓
Email Service
    ↓ (Checks Mailtrap API token)
Mailtrap API (Cloud email sending)
    ↓
User's Inbox ✉️
```

---

## 🚀 Testing Email Notifications

### Option 1: Test Locally (UI + Manual Pipeline Execution)

```bash
# 1. Start the backend server
cd research-paper-graph/backend
python main.py

# 2. In another terminal, start the frontend
cd research-paper-graph/frontend
npm start

# 3. Open http://localhost:3000
# 4. Start a research analysis
# 5. Toast appears: "Get notified when done?"
# 6. Enter your test email (or rohit@example.com)
# 7. Click "Yes, notify me"
```

### Option 2: Test API Directly

```bash
# Get a session ID from the pipeline runs
# Then test email registration directly:

curl -X POST http://localhost:8000/api/v1/notify/register \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "email": "yourtest@gmail.com"
  }'

# Response:
# {
#   "success": true,
#   "message": "You'll receive an email at yourtest@gmail.com when the analysis completes.",
#   "session_id": "test-session-123",
#   "email": "yourtest@gmail.com"
# }
```

### Option 3: Check Subscription Status

```bash
curl http://localhost:8000/api/v1/notify/status/test-session-123

# Response:
# {
#   "session_id": "test-session-123",
#   "subscribed": true,
#   "email": "yourtest@gmail.com"
# }
```

---

## 📧 Configuration Details

### Backend Environment (.env)

Your `.env` file has:

```env
# Mailtrap API (Primary method — currently active)
MAILTRAP_API_TOKEN=4284b44416b605d24c06f062b58602bb
MAILTRAP_FROM_EMAIL=noreply@agsearch.app

# Generic SMTP fallback (leave blank to use Mailtrap)
EMAIL_SMTP_HOST=
EMAIL_SMTP_PORT=587
EMAIL_SENDER=
EMAIL_PASSWORD=

# Frontend URL for email backlinks
APP_BASE_URL=http://localhost:3000
```

### Mailtrap API Details

- **Provider**: [Mailtrap.io](https://mailtrap.io)
- **Token**: Already configured ✅
- **From Email**: noreply@agsearch.app
- **Email Template**: Professional dark-theme, fully responsive HTML
- **Features**:
  - Research query summary in email
  - Direct link back to session
  - Status indicator (Completed/Finished with issues)
  - Papers count displayed

---

## 🔄 API Endpoints

### 1. Register Email Notification

**POST** `/api/v1/notify/register`

```json
{
  "session_id": "abc-123-xyz",
  "email": "user@example.com"
}
```

Response:
```json
{
  "success": true,
  "message": "You'll receive an email...",
  "session_id": "abc-123-xyz",
  "email": "user@example.com"
}
```

### 2. Get Subscription Status

**GET** `/api/v1/notify/status/{session_id}`

Response:
```json
{
  "session_id": "abc-123-xyz",
  "subscribed": true,
  "email": "user@example.com"
}
```

### 3. Unregister Email

**DELETE** `/api/v1/notify/unregister/{session_id}`

Response:
```json
{
  "success": true,
  "message": "Email notification removed.",
  "session_id": "abc-123-xyz",
  "email": "user@example.com"
}
```

---

## 📂 Subscription Storage

Emails are persisted in JSON format:

```bash
# File: data/pipeline_storage/email_subscriptions.json
{
  "session-id-1": "user1@example.com",
  "session-id-2": "user2@example.com",
  "fca1e3df-5885-4765-86f4-4bfd6f8f0091": "test@gmail.com"
}
```

- **Persistence**: Survives app restarts
- **Cleanup**: Emails auto-removed after successful notification
- **Manual cleanup**: Use unregister endpoint if needed

---

## 🎨 Frontend Components

### EmailNotifyToast Component

Located in: `frontend/src/components/EmailNotifyToast.js`

**Features:**
- ✅ Appears when analysis starts
- ✅ Smooth animations and transitions
- ✅ Email validation (basic @ check)
- ✅ Loading states
- ✅ Success confirmation
- ✅ Persistent "Notify me" bell button if dismissed
- ✅ Error handling with user-friendly messages

**Phases:**
1. `ask` → "Get notified when done?" prompt
2. `form` → Email input form
3. `loading` → Registering notification...
4. `success` → All set! Confirmation
5. `dismissed` → Small bell button in corner

---

## 🔧 Production Deployment

### For Production Use:

1. **Secure your Mailtrap token**:
   - Never commit `.env` file to git
   - Use environment variables in production
   - Rotate token if it gets exposed

2. **Update APP_BASE_URL**:
   ```env
   # Development
   APP_BASE_URL=http://localhost:3000
   
   # Production
   APP_BASE_URL=https://agsearch.yourdomain.com
   ```

3. **Test email sending**:
   ```bash
   curl -X POST http://your-api.com/api/v1/notify/register \
     -H "Content-Type: application/json" \
     -d '{"session_id": "test-prod", "email": "you@gmail.com"}'
   ```

4. **Monitor email deliverability**:
   - Check Mailtrap dashboard for bounce rates
   - Monitor spam complaints
   - Review email rendering on different clients

---

## 🐛 Troubleshooting

### Issue: Toast doesn't appear

**Solution:**
- Ensure backend is running: `python main.py`
- Check browser console for errors
- Verify `sessionId` is being passed to `EmailNotifyToast`

### Issue: Email registration fails

**Solution:**
- Check email format (must contain @)
- Verify backend is running on port 8000
- Check backend logs for errors:
  ```bash
  tail -f research-paper-graph/backend/app.log
  ```

### Issue: Email never arrives

**Solution:**
1. Check Mailtrap dashboard: https://mailtrap.io/inboxes
2. Verify Mailtrap token in `.env` is correct
3. Check if pipeline actually completed (check backend logs)
4. Look for bounces in Mailtrap dashboard

### Issue: "SMTP not configured" warning

**Solution:**
- This is expected when using Mailtrap API
- The warning is just informational
- Emails are still sent via Mailtrap (which is the primary method)
- To silence it, configure SMTP OR ignore (safe to ignore)

---

## 📧 Email Template Features

The notification email includes:

- **Header**: Status indicator (✅ Complete or ⚠️ Finished)
- **Research Query**: Full query text
- **Session Link**: Direct clickable button
- **Branding**: AgSearch logo and styling
- **Responsive**: Works on mobile, tablet, desktop
- **Footer**: Back to app link
- **Dark Theme**: Professional appearance

---

## ✨ Next Steps

1. **Test the workflow:**
   - Run frontend and backend
   - Start analysis
   - Register test email
   - Wait for completion
   - Check inbox for email

2. **Customize email template** (if needed):
   - Edit `backend/app/services/email_service.py`
   - Modify `_build_html()` function
   - Update styling and content

3. **Integrate with UI features:**
   - Show email status in SessionDetail view
   - Allow users to update email for existing sessions
   - Add unsubscribe button in email

4. **Monitor & Analytics:**
   - Log email sends to database
   - Track delivery rates
   - Monitor user preferences

---

## 📞 Support

For issues or questions:
1. Check backend logs: `backend.log`
2. Check Mailtrap status: https://mailtrap.io
3. Verify environment variables loaded: Check `backend/main.py` startup output
4. Test API endpoints with curl (see examples above)
