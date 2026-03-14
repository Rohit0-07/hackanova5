"""
Email Notification Service — supports Mailtrap API token & generic SMTP.

Priority:
  1. MAILTRAP_API_TOKEN is set → use Mailtrap's sending API (recommended)
  2. EMAIL_SMTP_HOST + EMAIL_SENDER + EMAIL_PASSWORD are all set → use SMTP
  3. None set → log a notice and skip silently

All configuration is read from environment variables (loaded from backend/.env
by python-dotenv at startup via main.py).

Environment variables:
  MAILTRAP_API_TOKEN      Your Mailtrap API token
  MAILTRAP_FROM_EMAIL     "From" address (default: noreply@agsearch.app)
  EMAIL_SMTP_HOST         SMTP hostname (e.g. smtp.gmail.com)
  EMAIL_SMTP_PORT         SMTP port (default: 587)
  EMAIL_SENDER            SMTP sender email address
  EMAIL_PASSWORD          SMTP password / app password
  APP_BASE_URL            Frontend URL embedded in emails (default: http://localhost:3000)
"""

import os
import ssl
import smtplib
import json
import httpx
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Dict
from loguru import logger


# ─── Read configuration from env ──────────────────────────────────────────────
MAILTRAP_API_TOKEN  = os.getenv("MAILTRAP_API_TOKEN", "").strip()
MAILTRAP_FROM_EMAIL = os.getenv("MAILTRAP_FROM_EMAIL", "noreply@agsearch.app").strip()

SMTP_HOST     = os.getenv("EMAIL_SMTP_HOST", "").strip()
SMTP_PORT     = int(os.getenv("EMAIL_SMTP_PORT", "587"))
SENDER_EMAIL  = os.getenv("EMAIL_SENDER", "").strip()
SENDER_PASS   = os.getenv("EMAIL_PASSWORD", "").strip()

APP_BASE_URL  = os.getenv("APP_BASE_URL", "http://localhost:3000").strip()

# Storage for pending email subscriptions: session_id → email
_SUBSCRIPTIONS_FILE = Path("./data/pipeline_storage/email_subscriptions.json")


# ─── Subscription persistence ──────────────────────────────────────────────────
def _load_subscriptions() -> Dict[str, str]:
    try:
        if _SUBSCRIPTIONS_FILE.exists():
            return json.loads(_SUBSCRIPTIONS_FILE.read_text())
    except Exception as e:
        logger.warning(f"EmailService: could not load subscriptions: {e}")
    return {}


def _save_subscriptions(data: Dict[str, str]) -> None:
    try:
        _SUBSCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SUBSCRIPTIONS_FILE.write_text(json.dumps(data, indent=2))
    except Exception as e:
        logger.warning(f"EmailService: could not save subscriptions: {e}")


def register_email(session_id: str, email: str) -> None:
    subs = _load_subscriptions()
    subs[session_id] = email
    _save_subscriptions(subs)
    logger.info(f"EmailService: registered {email} → session {session_id}")


def get_email_for_session(session_id: str) -> Optional[str]:
    return _load_subscriptions().get(session_id)


def unregister_email(session_id: str) -> None:
    subs = _load_subscriptions()
    subs.pop(session_id, None)
    _save_subscriptions(subs)


# ─── Email HTML template ───────────────────────────────────────────────────────
def _build_html(session_id: str, query: str, papers_count: int, status: str) -> tuple[str, str]:
    """Return (html_body, plain_body)."""
    session_url = f"{APP_BASE_URL}?session={session_id}"
    status_label = "✅ Completed" if status == "completed" else "⚠️ Finished with issues"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/><style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:0}}
  .c{{max-width:560px;margin:40px auto;background:#1e293b;border-radius:16px;overflow:hidden;border:1px solid #334155}}
  .h{{background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:32px 32px 24px}}
  .h h1{{margin:0 0 6px;font-size:22px;font-weight:800;color:#fff}}
  .h p{{margin:0;font-size:13px;color:#c7d2fe}}
  .b{{padding:28px 32px}}
  .pill{{display:inline-block;background:#064e3b;color:#34d399;border:1px solid #059669;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;border-radius:999px;padding:4px 12px;margin-bottom:20px}}
  .box{{background:#0f172a;border:1px solid #334155;border-radius:10px;padding:14px 18px;margin-bottom:20px}}
  .box .lbl{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#64748b;margin-bottom:6px}}
  .box .val{{font-size:14px;color:#f1f5f9;font-weight:600;line-height:1.5}}
  .cta{{display:block;background:#4f46e5;color:#fff!important;text-decoration:none;text-align:center;padding:14px 20px;border-radius:12px;font-weight:700;font-size:14px;margin-bottom:20px}}
  .foot{{padding:16px 32px 24px;text-align:center;font-size:11px;color:#475569;border-top:1px solid #1e293b}}
  a{{color:#818cf8}}
</style></head>
<body>
  <div class="c">
    <div class="h"><h1>AgSearch — Research Complete</h1><p>Your autonomous research analysis has finished.</p></div>
    <div class="b">
      <div class="pill">{status_label}</div>
      <div class="box">
        <div class="lbl">Research Query</div>
        <div class="val">{query}</div>
      </div>
      <a class="cta" href="{session_url}">View Your Research Session →</a>
      <p style="font-size:12px;color:#64748b;text-align:center;margin:0">
        Direct link: <a href="{session_url}" style="font-size:11px;word-break:break-all">{session_url}</a>
      </p>
    </div>
    <div class="foot">Sent by AgSearch · <a href="{APP_BASE_URL}">Open App</a></div>
  </div>
</body></html>"""

    plain = (
        f"AgSearch — Research Complete\n\n"
        f"Status: {status_label}\n"
        f"Query: {query}\n"
        f"Papers mined: {papers_count}\n\n"
        f"View your session:\n{session_url}\n"
    )
    return html, plain


# ─── Mailtrap Sending API ──────────────────────────────────────────────────────
def _send_via_mailtrap_api(recipient: str, subject: str, html: str, plain: str) -> bool:
    """Send email using Mailtrap's sending API (requires API token)."""
    url = "https://send.api.mailtrap.io/api/send"
    headers = {
        "Authorization": f"Bearer {MAILTRAP_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": {"email": MAILTRAP_FROM_EMAIL, "name": "AgSearch"},
        "to": [{"email": recipient}],
        "subject": subject,
        "html": html,
        "text": plain,
    }
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            logger.info(f"EmailService [Mailtrap API]: sent to {recipient}")
            return True
        else:
            logger.error(f"EmailService [Mailtrap API]: HTTP {resp.status_code} — {resp.text}")
            return False
    except Exception as e:
        logger.error(f"EmailService [Mailtrap API]: request failed — {e}")
        return False


# ─── Generic SMTP fallback ─────────────────────────────────────────────────────
def _send_via_smtp(recipient: str, subject: str, html: str, plain: str) -> bool:
    """Send email via generic SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = recipient
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())

        logger.info(f"EmailService [SMTP]: sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"EmailService [SMTP]: failed — {e}")
        return False


# ─── Public API ───────────────────────────────────────────────────────────────
def send_completion_email(
    session_id: str,
    query: str,
    papers_count: int,
    status: str = "completed",
) -> bool:
    """
    Send a completion notification to the registered email for this session.
    Uses Mailtrap API token if set, otherwise falls back to SMTP.
    Returns True if sent, False if skipped or failed.
    """
    recipient = get_email_for_session(session_id)
    if not recipient:
        logger.debug(f"EmailService: no subscription for session {session_id}")
        return False

    subject = f"⚡ AgSearch: Your research on '{query[:60]}' is ready"
    html, plain = _build_html(session_id, query, papers_count, status)

    sent = False

    # Priority 1: Mailtrap API token
    if MAILTRAP_API_TOKEN:
        sent = _send_via_mailtrap_api(recipient, subject, html, plain)

    # Priority 2: Generic SMTP
    elif SMTP_HOST and SENDER_EMAIL and SENDER_PASS:
        sent = _send_via_smtp(recipient, subject, html, plain)

    else:
        logger.info(
            "EmailService: no provider configured. "
            "Set MAILTRAP_API_TOKEN in your .env file to enable email notifications."
        )
        return False

    if sent:
        unregister_email(session_id)

    return sent
