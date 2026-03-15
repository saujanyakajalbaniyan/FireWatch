"""
Alert Manager — Fire Alert Lifecycle Management
Handles alert history, email notifications, and notification queue.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import deque


class AlertManager:
    """Manages fire alerts, history, email notifications, and notification queue."""

    def __init__(self, max_history=500):
        self.alert_history = deque(maxlen=max_history)
        self.notification_queue = deque(maxlen=100)
        self.email_config = None
        self.email_enabled = False

    # ── Alert History ──────────────────────────────────────────────

    def add_alert(self, alert):
        """Add an alert to the history."""
        entry = {
            **alert,
            "logged_at": datetime.utcnow().isoformat(),
            "acknowledged": False,
        }
        self.alert_history.appendleft(entry)
        self.notification_queue.append(entry)

        # Trigger email for critical alerts
        if self.email_enabled and alert.get("level") in ("critical", "high"):
            self._send_email_alert(entry)

        return entry

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
            "logged_at": datetime.utcnow().isoformat(),
            "acknowledged": True,  # Auto-acknowledge scan logs
        }
        self.alert_history.appendleft(entry)

    # ── Email Configuration ────────────────────────────────────────

    def configure_email(self, smtp_server, smtp_port, sender_email,
                        sender_password, recipient_email):
        """Configure email alert settings."""
        self.email_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "sender_email": sender_email,
            "sender_password": sender_password,
            "recipient_email": recipient_email,
        }
        self.email_enabled = True
        return {"status": "configured", "recipient": recipient_email}

    def disable_email(self):
        """Disable email alerts."""
        self.email_enabled = False
        return {"status": "disabled"}

    def _send_email_alert(self, alert):
        """Send an email notification for a fire alert."""
        if not self.email_config:
            return

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

            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
                server.starttls()
                server.login(cfg["sender_email"], cfg["sender_password"])
                server.send_message(msg)

            print(f"[AlertManager] Email sent to {cfg['recipient_email']}")

        except Exception as e:
            print(f"[AlertManager] Email failed: {e}")
