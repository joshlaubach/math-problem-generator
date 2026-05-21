"""
Email service using Resend.

Two email types:
  - send_session_report: sent at WS close with summary bullets
  - send_session_reminder: sent when a session is scheduled for later

All sends are best-effort — failures are logged and silently swallowed.
Set RESEND_API_KEY in the environment to enable sending.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

_BASE_FROM = "Gradient Tutor <tutor@gradient-math.com>"


def _get_resend():
    """Return the resend module if configured, else None."""
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        return None
    try:
        import resend as _resend
        _resend.api_key = api_key
        return _resend
    except ImportError:
        return None


def _html_template(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
             background: #faf9f6; margin: 0; padding: 0;">
  <div style="max-width: 540px; margin: 40px auto; background: #fff;
              border: 1px solid #e8e0d5; border-radius: 12px; overflow: hidden;">
    <div style="background: #c4976a; padding: 24px 32px;">
      <div style="font-size: 18px; font-weight: 700; color: #fff; letter-spacing: -0.02em;">
        ✦ Gradient
      </div>
    </div>
    <div style="padding: 32px;">
      {body_html}
    </div>
    <div style="padding: 16px 32px; border-top: 1px solid #e8e0d5;
                font-size: 12px; color: #999; text-align: center;">
      Gradient Adaptive Math — <a href="https://gradient-math.com" style="color: #c4976a;">gradient-math.com</a>
    </div>
  </div>
</body>
</html>"""


def send_session_report(
    user_email: str,
    user_name: str,
    topic_name: str,
    tutor_name: str,
    duration_minutes: int,
    summary_bullets: list[str],
    hints_used: int,
    attempts: int,
    score_pct: int,
) -> None:
    """Send a post-session report email. Fire-and-forget."""
    resend = _get_resend()
    if not resend:
        logger.debug("Resend not configured — skipping session report email")
        return

    bullets_html = "".join(
        f'<li style="margin-bottom: 6px; color: #444; line-height: 1.5;">{b}</li>'
        for b in summary_bullets
    ) if summary_bullets else '<li style="color: #999;">Session data unavailable</li>'

    stats_html = "".join([
        f'<div style="text-align: center; flex: 1;">'
        f'<div style="font-size: 24px; font-weight: 700; color: #c4976a;">{v}</div>'
        f'<div style="font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 0.05em;">{l}</div>'
        f'</div>'
        for v, l in [(f"{duration_minutes}m", "Duration"), (str(attempts), "Attempts"),
                     (str(hints_used), "Hints"), (f"{score_pct}%", "Score")]
    ])

    body = f"""
    <h2 style="font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px;">
      Session Complete
    </h2>
    <p style="font-size: 14px; color: #888; margin: 0 0 24px;">
      {topic_name} &nbsp;·&nbsp; {tutor_name}
    </p>

    <div style="display: flex; gap: 16px; background: #fdf8f3;
                border: 1px solid #e8ddd0; border-radius: 10px;
                padding: 20px; margin-bottom: 24px;">
      {stats_html}
    </div>

    <h3 style="font-size: 13px; font-weight: 700; color: #999;
               text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 12px;">
      Session Summary
    </h3>
    <ul style="margin: 0 0 24px; padding-left: 20px;">
      {bullets_html}
    </ul>

    <a href="https://gradient-math.com/dashboard"
       style="display: block; text-align: center; background: #c4976a;
              color: #fff; text-decoration: none; font-weight: 600;
              padding: 12px 24px; border-radius: 8px; font-size: 14px;">
      Continue Practicing
    </a>
    """

    try:
        resend.Emails.send({
            "from": _BASE_FROM,
            "to": user_email,
            "subject": f"Session complete: {topic_name}",
            "html": _html_template("Session Complete", body),
        })
        logger.info("Session report email sent to %s", user_email)
    except Exception as exc:
        logger.warning("Failed to send session report email: %s", exc)


def send_session_reminder(
    user_email: str,
    user_name: str,
    topic_name: str,
    tutor_name: str,
    scheduled_at_iso: str,
    session_type: str,
) -> None:
    """Send a session reminder email. Fire-and-forget."""
    resend = _get_resend()
    if not resend:
        logger.debug("Resend not configured — skipping reminder email")
        return

    try:
        dt = datetime.fromisoformat(scheduled_at_iso.replace("Z", "+00:00"))
        formatted = dt.strftime("%A, %B %-d at %-I:%M %p")
    except Exception:
        formatted = scheduled_at_iso

    duration_label = "1-hour" if session_type == "1hr" else "2-hour"

    body = f"""
    <h2 style="font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px;">
      Your session starts soon
    </h2>
    <p style="font-size: 14px; color: #888; margin: 0 0 24px;">
      Reminder for your scheduled tutoring session
    </p>

    <div style="background: #fdf8f3; border: 1px solid #e8ddd0; border-radius: 10px;
                padding: 20px; margin-bottom: 24px;">
      <div style="font-size: 14px; color: #444; margin-bottom: 8px;">
        <strong>Topic:</strong> {topic_name}
      </div>
      <div style="font-size: 14px; color: #444; margin-bottom: 8px;">
        <strong>Tutor:</strong> {tutor_name}
      </div>
      <div style="font-size: 14px; color: #444; margin-bottom: 8px;">
        <strong>When:</strong> {formatted}
      </div>
      <div style="font-size: 14px; color: #444;">
        <strong>Duration:</strong> {duration_label}
      </div>
    </div>

    <a href="https://gradient-math.com/dashboard"
       style="display: block; text-align: center; background: #c4976a;
              color: #fff; text-decoration: none; font-weight: 600;
              padding: 12px 24px; border-radius: 8px; font-size: 14px;">
      Start Session
    </a>
    <p style="font-size: 12px; color: #bbb; text-align: center; margin-top: 16px;">
      1 credit has been reserved. It will be charged when your session starts.
    </p>
    """

    try:
        resend.Emails.send({
            "from": _BASE_FROM,
            "to": user_email,
            "subject": f"Session reminder: {topic_name} with {tutor_name}",
            "html": _html_template("Session Reminder", body),
        })
        logger.info("Reminder email sent to %s for %s", user_email, scheduled_at_iso)
    except Exception as exc:
        logger.warning("Failed to send reminder email: %s", exc)
