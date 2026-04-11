"""
Alert Manager — Fire Alert Lifecycle Management
Handles alert history, email notifications, and notification queue.
"""

import copy
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, UTC
from collections import deque
import time

import requests

try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None


class AlertManager:
    """Manages fire alerts, history, email notifications, and notification queue."""

    def __init__(self, max_history=500):
        self.alert_history = deque(maxlen=max_history)
        self.notification_queue = deque(maxlen=100)
        self.email_config = None
        self.email_enabled = False
        self.twilio_config = None
        self.twilio_enabled = False
        self.mobile_config = None
        self.mobile_enabled = False
        self.last_dispatch_time = 0  # To track notification cooldown
        self.cooldown_seconds = 300  # 5 minutes global cooldown

    def _masked_config(self, config):
        """Return a safe-to-display copy of channel configuration."""
        if not config:
            return None

        masked = copy.deepcopy(config)
        for key in ("sender_password", "auth_token", "api_key"):
            value = masked.get(key)
            if value:
                masked[key] = self._mask_secret(value)
        return masked

    def _mask_secret(self, value):
        if not value:
            return ""
        if len(value) <= 4:
            return "*" * len(value)
        return f"{value[:2]}{'*' * max(len(value) - 4, 2)}{value[-2:]}"

    # ── Alert History ──────────────────────────────────────────────

    def add_alert(self, alert):
        """Add an alert to the history."""
        entry = {
            **alert,
            "logged_at": datetime.now(UTC).isoformat(),
            "acknowledged": False,
        }
        self.alert_history.appendleft(entry)
        self.notification_queue.append(entry)

        self.dispatch_alert(entry)

        return entry

    def dispatch_alert(self, alert):
        """Dispatch alert to enabled channels and add delivery metadata."""
        level = alert.get("level", "low")
        start = time.perf_counter()
        channel_status = {
            "dashboard": {"status": "sent"},
            "email": {"status": "skipped"},
            "sms": {"status": "skipped"},
            "mobile": {"status": "skipped"},
        }

        # Check cooldown to prevent notification spam
        current_time = time.time()
        in_cooldown = (current_time - self.last_dispatch_time) < self.cooldown_seconds
        is_test = alert.get("type") == "test_alert"

        if level in ("critical", "high") and (not in_cooldown or is_test):
            if self.email_enabled:
                channel_status["email"] = self._send_email_alert(alert)
            if self.twilio_enabled:
                channel_status["sms"] = self._send_sms_alert(alert)
            if self.mobile_enabled:
                channel_status["mobile"] = self._send_mobile_push(alert)
            
            if not is_test:
                self.last_dispatch_time = current_time
        elif in_cooldown and not is_test:
            channel_status["email"] = {"status": "skipped", "reason": "cooldown_active"}
            channel_status["sms"] = {"status": "skipped", "reason": "cooldown_active"}
            channel_status["mobile"] = {"status": "skipped", "reason": "cooldown_active"}

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        alert["dispatch"] = {
            "sent_at": datetime.now(UTC).isoformat(),
            "latency_ms": elapsed_ms,
            "within_5_seconds": elapsed_ms <= 5000,
            "channels": channel_status,
        }

        return alert["dispatch"]

    def add_alerts_batch(self, alerts):
        """Add multiple alerts to history."""
        for alert in alerts:
            self.add_alert(alert)

    def get_history(self, limit=100, level=None, region=None):
        """Get alert history with optional filters."""
        history = list(self.alert_history)

        if level:
            history = [a for a in history if a.get("level") == level]
        if region:
            region_lower = region.lower()
            history = [a for a in history if region_lower in a.get("title", "").lower()
                       or region_lower in a.get("message", "").lower()]

        return history[:limit]

    def get_notifications(self):
        """Get and clear pending notifications."""
        notifications = list(self.notification_queue)
        self.notification_queue.clear()
        return notifications

    def acknowledge_alert(self, index):
        """Mark an alert as acknowledged."""
        if 0 <= index < len(self.alert_history):
            self.alert_history[index]["acknowledged"] = True
            return True
        return False

    # ── Fire History Log ───────────────────────────────────────────

    def log_fire_event(self, fires, analysis_time):
        """Log fire detection events for history tracking."""
        if not fires:
            return

        # Create summarized log entry
        severity_counts = {}
        for f in fires:
            sev = f.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        regions = {}
        for f in fires:
            region = f.get("region", "Unknown")
            regions[region] = regions.get(region, 0) + 1

        entry = {
            "type": "fire_detection_log",
            "level": "info",
            "title": f"📊 Fire Detection Scan — {len(fires)} fires",
            "message": f"Detected {len(fires)} active fires. "
                       f"Critical: {severity_counts.get('critical', 0)}, "
                       f"High: {severity_counts.get('high', 0)}, "
                       f"Moderate: {severity_counts.get('moderate', 0)}, "
                       f"Low: {severity_counts.get('low', 0)}.",
            "fire_count": len(fires),
            "severity_counts": severity_counts,
            "timestamp": analysis_time,
            "logged_at": datetime.now(UTC).isoformat(),
            "acknowledged": True,  # Auto-acknowledge scan logs
        }
        self.alert_history.appendleft(entry)

    # ── Email Configuration ────────────────────────────────────────

    def configure_email(self, smtp_server, smtp_port, sender_email,
                        sender_password, recipient_email):
        """Configure email alert settings."""
        smtp_port = int(smtp_port or 587)
        self.email_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "sender_email": sender_email,
            "sender_password": sender_password,
            "recipient_email": recipient_email,
        }
        self.email_enabled = all([
            smtp_server,
            smtp_port,
            sender_email,
            sender_password,
            recipient_email,
        ])
        return {
            "status": "configured" if self.email_enabled else "incomplete",
            "recipient": recipient_email,
            "enabled": self.email_enabled,
        }

    def disable_email(self):
        """Disable email alerts."""
        self.email_enabled = False
        return {"status": "disabled"}

    def configure_twilio(self, account_sid, auth_token, from_number, to_number):
        """Configure Twilio SMS alert settings."""
        self.twilio_config = {
            "account_sid": account_sid,
            "auth_token": auth_token,
            "from_number": from_number,
            "to_number": to_number,
        }
        self.twilio_enabled = all([account_sid, auth_token, from_number, to_number])
        return {
            "status": "configured" if self.twilio_enabled else "incomplete",
            "to_number": to_number,
        }

    def disable_twilio(self):
        """Disable Twilio SMS alerts."""
        self.twilio_enabled = False
        return {"status": "disabled"}

    def configure_mobile(self, webhook_url, api_key=None):
        """Configure mobile notification webhook settings."""
        self.mobile_config = {
            "webhook_url": webhook_url,
            "api_key": api_key,
        }
        self.mobile_enabled = bool(webhook_url)
        return {
            "status": "configured" if self.mobile_enabled else "incomplete",
            "webhook_url": webhook_url,
        }

    def disable_mobile(self):
        """Disable mobile push notifications."""
        self.mobile_enabled = False
        return {"status": "disabled"}

    def get_channel_status(self):
        """Expose channel configuration state for the frontend."""
        return {
            "email": {
                "enabled": self.email_enabled,
                "configured": bool(self.email_config),
                "config": self._masked_config(self.email_config),
            },
            "sms": {
                "enabled": self.twilio_enabled,
                "configured": bool(self.twilio_config),
                "config": self._masked_config(self.twilio_config),
            },
            "mobile": {
                "enabled": self.mobile_enabled,
                "configured": bool(self.mobile_config),
                "config": self._masked_config(self.mobile_config),
            },
        }

    def create_test_alert(self, title="Test Fire Alert", message=None):
        """Create a synthetic alert to verify downstream channel delivery."""
        return self.add_alert({
            "type": "test_alert",
            "level": "high",
            "title": title,
            "message": message or "This is a live channel test from FireWatch AI.",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    def _send_email_alert(self, alert):
        """Send an email notification for a fire alert."""
        if not self.email_config:
            return {"status": "skipped", "reason": "not_configured"}

        try:
            cfg = self.email_config
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🔥 FireWatch Alert: {alert.get('title', 'Fire Detected')}"
            msg["From"] = cfg["sender_email"]
            msg["To"] = cfg["recipient_email"]

            severity = alert.get("level", "unknown").upper()
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background: #0a0e17; color: #f1f5f9; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: #111827; border-radius: 12px; padding: 24px;
                            border: 1px solid rgba(255,255,255,0.1);">
                    <h1 style="color: #f97316; margin: 0 0 16px;">🔥 FireWatch AI — Fire Alert</h1>
                    <div style="background: rgba(239,68,68,0.1); border-left: 4px solid #ef4444; padding: 12px 16px;
                                border-radius: 4px; margin-bottom: 16px;">
                        <strong style="color: #ef4444;">{severity} ALERT</strong>
                        <p style="margin: 8px 0 0; color: #94a3b8;">{alert.get('message', '')}</p>
                    </div>
                    <table style="width: 100%; color: #94a3b8; font-size: 14px;">
                        <tr><td><strong>Location:</strong></td>
                            <td>{alert.get('latitude', 'N/A')}, {alert.get('longitude', 'N/A')}</td></tr>
                        <tr><td><strong>Time:</strong></td>
                            <td>{alert.get('timestamp', 'N/A')}</td></tr>
                        <tr><td><strong>Type:</strong></td>
                            <td>{alert.get('type', 'fire_detection')}</td></tr>
                    </table>
                    <hr style="border: 1px solid rgba(255,255,255,0.1); margin: 16px 0;">
                    <p style="color: #64748b; font-size: 12px;">
                        Sent by FireWatch AI — Forest Fire Detection System
                    </p>
                </div>
            </body>
            </html>
            """

            plain = (
                f"FireWatch Alert\n\n"
                f"Severity: {severity}\n"
                f"Message: {alert.get('message', '')}\n"
                f"Location: {alert.get('latitude', 'N/A')}, {alert.get('longitude', 'N/A')}\n"
                f"Time: {alert.get('timestamp', 'N/A')}\n"
                f"Type: {alert.get('type', 'fire_detection')}\n"
            )

            msg.attach(MIMEText(plain, "plain"))
            msg.attach(MIMEText(html, "html"))

            smtp_cls = smtplib.SMTP_SSL if int(cfg["smtp_port"]) == 465 else smtplib.SMTP
            with smtp_cls(cfg["smtp_server"], cfg["smtp_port"]) as server:
                if int(cfg["smtp_port"]) != 465:
                    server.starttls()
                server.login(cfg["sender_email"], cfg["sender_password"])
                server.send_message(msg)

            print(f"[AlertManager] Email sent to {cfg['recipient_email']}")
            return {"status": "sent", "recipient": cfg["recipient_email"]}

        except Exception as e:
            print(f"[AlertManager] Email failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _send_sms_alert(self, alert):
        """Send a Twilio SMS alert when configured."""
        if not self.twilio_config:
            return {"status": "skipped", "reason": "not_configured"}
        if TwilioClient is None:
            return {"status": "failed", "error": "twilio_package_missing"}

        try:
            cfg = self.twilio_config
            message = (
                f"FireWatch {alert.get('level', 'high').upper()} alert: "
                f"{alert.get('message', 'Fire detected')[:140]}"
            )
            client = TwilioClient(cfg["account_sid"], cfg["auth_token"])
            resp = client.messages.create(
                body=message,
                from_=cfg["from_number"],
                to=cfg["to_number"],
            )
            return {"status": "sent", "sid": resp.sid, "to": cfg["to_number"]}
        except Exception as e:
            print(f"[AlertManager] SMS failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _send_mobile_push(self, alert):
        """Send mobile push through configured webhook (e.g., Firebase relay)."""
        if not self.mobile_config:
            return {"status": "skipped", "reason": "not_configured"}

        try:
            cfg = self.mobile_config
            headers = {"Content-Type": "application/json"}
            if cfg.get("api_key"):
                headers["Authorization"] = f"Bearer {cfg['api_key']}"

            payload = {
                "title": alert.get("title", "Fire Alert"),
                "body": alert.get("message", "Fire detected"),
                "level": alert.get("level", "high"),
                "timestamp": alert.get("timestamp"),
                "lat": alert.get("latitude"),
                "lng": alert.get("longitude"),
            }

            response = requests.post(
                cfg["webhook_url"],
                json=payload,
                headers=headers,
                timeout=4,
            )
            response.raise_for_status()
            return {"status": "sent", "code": response.status_code}
        except Exception as e:
            print(f"[AlertManager] Mobile push failed: {e}")
            return {"status": "failed", "error": str(e)}
