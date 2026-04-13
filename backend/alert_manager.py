"""
Alert Manager — Fire Alert Lifecycle Management
Handles alert history, SMS/mobile notifications, and notification queue.
"""

import copy
from datetime import datetime, UTC
from collections import deque
import time

import requests

try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None


class AlertManager:
    """Manages fire alerts, history, SMS/mobile notifications, and notification queue."""

    def __init__(self, max_history=500):
        self.alert_history = deque(maxlen=max_history)
        self.notification_queue = deque(maxlen=100)
        self.twilio_config = None
        self.twilio_enabled = False
        self.mobile_config = None
        self.mobile_enabled = False
        self.last_dispatch_time = 0  # To track notification cooldown
        self.cooldown_seconds = 1800  # 30 minutes cooldown to conserve SMS quota

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
        """Dispatch alert to enabled channels and add delivery metadata.
        
        SMS and mobile notifications are ONLY sent for critical/high alerts
        that represent actual fire detections (not informational logs).
        """
        level = alert.get("level", "low")
        alert_type = alert.get("type", "")
        start = time.perf_counter()
        channel_status = {
            "dashboard": {"status": "sent"},
            "sms": {"status": "skipped"},
            "mobile": {"status": "skipped"},
        }

        # Only fire-related alerts should trigger SMS (not scan summaries or info logs)
        is_fire_alert = alert_type in (
            "critical_fire", "fire_cluster", "auto_scan", "test_alert",
            "image_analysis", "live_camera", "sensor_threshold",
        )
        is_test = alert_type == "test_alert"

        if not is_fire_alert:
            # Informational/log entries never trigger SMS
            channel_status["sms"] = {"status": "skipped", "reason": "not_fire_alert"}
            channel_status["mobile"] = {"status": "skipped", "reason": "not_fire_alert"}
        elif level not in ("critical", "high"):
            channel_status["sms"] = {"status": "skipped", "reason": f"level_too_low ({level})"}
            channel_status["mobile"] = {"status": "skipped", "reason": f"level_too_low ({level})"}
        else:
            # Check cooldown to prevent notification spam
            current_time = time.time()
            in_cooldown = (current_time - self.last_dispatch_time) < self.cooldown_seconds

            if in_cooldown and not is_test:
                remaining = int(self.cooldown_seconds - (current_time - self.last_dispatch_time))
                print(f"[AlertManager] SMS dispatch skipped — cooldown active ({remaining}s remaining)")
                channel_status["sms"] = {"status": "skipped", "reason": "cooldown_active"}
                channel_status["mobile"] = {"status": "skipped", "reason": "cooldown_active"}
            else:
                # --- SMS ---
                if self.twilio_enabled:
                    print(f"[AlertManager] Sending SMS for {level.upper()} alert: {alert.get('title', 'N/A')}")
                    channel_status["sms"] = self._send_sms_alert(alert)
                    print(f"[AlertManager] SMS result: {channel_status['sms'].get('status')}")
                else:
                    channel_status["sms"] = {"status": "skipped", "reason": "twilio_not_enabled"}

                # --- Mobile Push ---
                if self.mobile_enabled:
                    channel_status["mobile"] = self._send_mobile_push(alert)
                else:
                    channel_status["mobile"] = {"status": "skipped", "reason": "mobile_not_enabled"}

                if not is_test:
                    self.last_dispatch_time = current_time

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
            "title": f"[SUMMARY] Fire Detection Scan — {len(fires)} fires",
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

    # ── Channel Configuration ───────────────────────────────────────

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



    def _send_sms_alert(self, alert):
        """Send a Twilio SMS alert when configured."""
        if not self.twilio_config:
            return {"status": "skipped", "reason": "not_configured"}
        if TwilioClient is None:
            return {"status": "failed", "error": "twilio_package_missing — run: pip install twilio"}

        try:
            cfg = self.twilio_config
            level = alert.get("level", "high").upper()
            title = alert.get("title", "Fire Alert")
            detail = alert.get("message", "Fire detected")[:120]

            # Build location line if coordinates are available
            lat = alert.get("latitude")
            lng = alert.get("longitude")
            location = f"\nLocation: {lat:.3f}, {lng:.3f}" if lat and lng else ""

            body = (
                f"[FireWatch AI] {level} ALERT\n"
                f"{title}\n"
                f"{detail}{location}"
            )

            client = TwilioClient(cfg["account_sid"], cfg["auth_token"])
            resp = client.messages.create(
                body=body,
                from_=cfg["from_number"],
                to=cfg["to_number"],
            )
            print(f"[AlertManager] SMS sent successfully — SID: {resp.sid}")
            return {"status": "sent", "sid": resp.sid, "to": cfg["to_number"]}
        except Exception as e:
            error_msg = str(e)
            print(f"[AlertManager] SMS FAILED: {error_msg}")
            return {"status": "failed", "error": error_msg}

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
