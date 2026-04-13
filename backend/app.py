
"""
Forest Fire Detection System — Flask Backend
Main application with REST API and WebSocket real-time updates.
"""

import os
# Prevent Intel Fortran/MKL from hard-crashing the Flask server on Windows
os.environ["FOR_DISABLE_CONSOLE_CTRL_HANDLER"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import base64
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv, set_key
from firms_service import FIRMSService
from ai_analyzer import AIAnalyzer
from image_analyzer import ImageAnalyzer
from alert_manager import AlertManager
from cloud_storage import CloudStorageService
from event_store import EventStore
from auto_scanner import AutoScanner
import threading
import time
from datetime import datetime, UTC
from models import db

app = Flask(__name__)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///firewatch.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode=os.getenv("SOCKETIO_ASYNC_MODE", "threading"),
)

# Upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize services
firms = FIRMSService()
analyzer = AIAnalyzer()
image_analyzer = ImageAnalyzer()
alert_manager = AlertManager()
cloud_storage = CloudStorageService()
event_store = EventStore()
auto_scanner = AutoScanner(app, image_analyzer, alert_manager, event_store, socketio)

auto_scanner.start()

# Global state
current_fires = []
current_analysis = None
is_fetching = False
fire_history_log = []
latest_sensor_reading = None
fetch_lock = threading.Lock()


def _bootstrap_alert_channels():
    """Load alert channels from environment for real-time delivery on startup."""
    twilio_result = alert_manager.configure_twilio(
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
        to_number=os.getenv("TWILIO_TO_NUMBER", ""),
    )
    mobile_result = alert_manager.configure_mobile(
        webhook_url=os.getenv("MOBILE_WEBHOOK_URL", ""),
        api_key=os.getenv("MOBILE_WEBHOOK_API_KEY", ""),
    )
    print(f"[Startup] SMS channel: {twilio_result.get('status', 'unknown')}")
    print(f"[Startup] Mobile channel: {mobile_result.get('status', 'unknown')}")


_bootstrap_alert_channels()


def _analysis_snapshot():
    """Return the latest analysis payload or a safe empty placeholder."""
    return current_analysis or analyzer._empty_analysis()


def _ensure_data():
    """Fetch data on demand when the dashboard has not been populated yet."""
    if not current_fires or not current_analysis:
        try:
            fetch_and_analyze()
        except Exception as e:
            print(f"[Server] _ensure_data fallback triggered: {e}")
            # Force demo data as last resort
            _force_demo_data()


def _cfg(value, env_key, default=""):
    """Prefer request values, but fall back to env/default for blank entries."""
    if value is None:
        return os.getenv(env_key, default)
    if isinstance(value, str) and not value.strip():
        return os.getenv(env_key, default)
    return value


def _save_env(key, value):
    """Save an environment variable persistently to the .env file."""
    if value is not None:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        set_key(env_path, key, str(value))


def _create_and_dispatch_alert(payload):
    """Create an alert and broadcast it to dashboard clients."""
    entry = alert_manager.add_alert(payload)
    event_store.append("fire_incidents", {
        "alert_type": payload.get("type"),
        "level": payload.get("level"),
        "title": payload.get("title"),
        "message": payload.get("message"),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "source_timestamp": payload.get("timestamp"),
    })
    socketio.emit("dashboard_alert", entry)
    return entry


def _force_demo_data():
    """Force-populate with demo data so the dashboard always has something to show."""
    global current_fires, current_analysis
    if not current_fires:
        print("[Server] Force-loading demo fire data...")
        current_fires = firms._get_demo_data()
    if not current_analysis:
        current_analysis = analyzer.analyze_fires(current_fires)
        print(f"[Server] Demo analysis complete: {len(current_fires)} fires.")


def fetch_and_analyze():
    """Fetch fire data and run analysis."""
    global current_fires, current_analysis, is_fetching

    if is_fetching and fetch_lock.locked():
        return _analysis_snapshot()

    if not fetch_lock.acquire(blocking=False):
        return _analysis_snapshot()

    is_fetching = True

    try:
        fires = firms.fetch_fires(bbox="-180,-90,180,90", days=1, source="VIIRS_SNPP")

        if not fires:
            print("[Server] FIRMS returned no fires, using demo data.")
            fires = firms._get_demo_data()

        current_fires = fires
        current_analysis = analyzer.analyze_fires(fires)
        print(f"[Server] Fetched {len(fires)} fires, analysis complete.")

        analysis_payload = _analysis_snapshot()

        # Log alerts to history (wrap in try/except so failures don't break data flow)
        try:
            if analysis_payload.get("alerts"):
                alert_manager.add_alerts_batch(analysis_payload["alerts"][:20])
            alert_manager.log_fire_event(fires, analysis_payload.get("analysis_time", ""))
        except Exception as alert_err:
            print(f"[Server] Alert logging warning: {alert_err}")

        # Store in fire history
        try:
            _log_fire_snapshot(fires, analysis_payload)
        except Exception as hist_err:
            print(f"[Server] History log warning: {hist_err}")

        # Store event in cloud/local storage for downstream analytics
        try:
            cloud_storage.store_event("satellite_scan", {
                "timestamp": analysis_payload.get("analysis_time"),
                "fire_count": len(fires),
                "analytics": analysis_payload.get("analytics", {}),
            })
        except Exception as cloud_err:
            print(f"[Server] Cloud storage warning: {cloud_err}")

        # Push update to connected clients
        try:
            socketio.emit("fire_update", {
                "fires": fires[:500],
                "analytics": analysis_payload["analytics"],
                "alerts": analysis_payload["alerts"][:20],
                "risk_assessments": analysis_payload.get("risk_assessments", []),
                "clusters": analysis_payload.get("clusters", []),
                "timestamp": analysis_payload["analysis_time"],
            })
        except Exception as ws_err:
            print(f"[Server] WebSocket emit warning: {ws_err}")

    except Exception as e:
        print(f"[Server] Error in fetch_and_analyze: {e}")
        import traceback
        traceback.print_exc()
        # Always ensure we have data, even on total failure
        _force_demo_data()
    finally:
        is_fetching = False
        fetch_lock.release()


def _log_fire_snapshot(fires, analysis):
    """Store a snapshot for fire history."""
    global fire_history_log

    if not fires:
        return

    snapshot = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_fires": len(fires),
        "critical": analysis["analytics"].get("critical_count", 0) if analysis else 0,
        "high": analysis["analytics"].get("high_count", 0) if analysis else 0,
        "avg_confidence": analysis["analytics"].get("avg_confidence", 0) if analysis else 0,
        "avg_frp": analysis["analytics"].get("avg_frp", 0) if analysis else 0,
        "total_frp": analysis["analytics"].get("total_frp", 0) if analysis else 0,
        "fires_sample": fires[:50],  # Keep a sample for history detail view
    }
    fire_history_log.insert(0, snapshot)
    fire_history_log = fire_history_log[:100]  # Keep last 100 snapshots


def background_updater():
    """Background thread to periodically fetch new data."""
    # Initial fetch with a small delay to let server fully start
    time.sleep(3)
    try:
        fetch_and_analyze()
    except Exception as e:
        print(f"[Server] Initial fetch failed: {e}")
        _force_demo_data()

    while True:
        time.sleep(300)  # Refresh every 5 minutes
        try:
            fetch_and_analyze()
        except Exception as e:
            print(f"[Server] Background update failed: {e}")


# ─── REST API Endpoints ─────────────────────────────────────────────

@app.route("/api/fires", methods=["GET"])
def get_fires():
    """Get current active fires, optionally filtered by region."""
    _ensure_data()

    bbox = request.args.get("bbox")
    limit = request.args.get("limit", 1000, type=int)

    fires = current_fires
    if bbox:
        try:
            west, south, east, north = map(float, bbox.split(","))
            fires = [
                f for f in fires
                if west <= f["longitude"] <= east and south <= f["latitude"] <= north
            ]
        except ValueError:
            pass

    return jsonify({
        "fires": fires[:limit],
        "total": len(fires),
        "last_updated": firms.last_fetch_time,
    })


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """Get aggregated fire analytics."""
    _ensure_data()

    return jsonify({
        "analytics": _analysis_snapshot()["analytics"],
        "last_updated": _analysis_snapshot()["analysis_time"],
    })


@app.route("/api/risk-analysis", methods=["GET"])
def get_risk_analysis():
    """Get AI-generated risk assessments per region."""
    _ensure_data()
    analysis = _analysis_snapshot()

    return jsonify({
        "risk_assessments": analysis["risk_assessments"],
        "clusters": analysis["clusters"],
        "last_updated": analysis["analysis_time"],
    })


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Get fire alerts sorted by severity."""
    _ensure_data()
    analysis = _analysis_snapshot()

    limit = request.args.get("limit", 50, type=int)
    level = request.args.get("level")

    alerts = analysis["alerts"]
    if level:
        alerts = [a for a in alerts if a["level"] == level]

    return jsonify({
        "alerts": alerts[:limit],
        "total": len(alerts),
        "last_updated": analysis["analysis_time"],
    })


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get server status."""
    return jsonify({
        "status": "running",
        "is_fetching": is_fetching,
        "total_fires": len(current_fires),
        "last_updated": firms.last_fetch_time,
        "analysis_available": current_analysis is not None,
        "models": image_analyzer.model_engine.get_status(),
    })


@app.route("/api/models/status", methods=["GET"])
def get_models_status():
    """Get AI model readiness for YOLOv8 and EfficientNet."""
    return jsonify(image_analyzer.model_engine.get_status())


# ─── NEW: Image Upload & Analysis ────────────────────────────────────

@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    """Upload an image for AI fire detection analysis."""
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Read image bytes
    image_bytes = file.read()

    # Run AI analysis
    result = image_analyzer.analyze_image(image_bytes)
    event_store.append("detection_logs", {
        "source": "upload",
        "fire_detected": result.get("fire_detected"),
        "scene_classification": result.get("scene_classification"),
        "confidence": result.get("confidence"),
        "severity": result.get("severity"),
    })

    # If fire detected, create an alert
    if result.get("fire_detected"):
        alert_entry = _create_and_dispatch_alert({
            "type": "image_analysis",
            "level": result["severity"],
            "title": f"[IMAGE] Fire Detected in Uploaded Image",
            "message": f"AI analysis detected fire with {result['confidence']}% confidence. "
                       f"Severity: {result['severity'].upper()}.",
            "latitude": None,
            "longitude": None,
            "timestamp": result["analysis_time"],
        })
        result["alert_dispatch"] = alert_entry.get("dispatch")

    cloud_storage.store_event("uploaded_image_analysis", result)

    return jsonify(result)


@app.route("/api/live-feed/analyze", methods=["POST"])
def analyze_live_frame():
    """Analyze a single live camera frame and return detection overlay data."""
    data = request.json or {}
    frame_data = data.get("frame")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not frame_data:
        return jsonify({"error": "Missing frame data"}), 400

    if "," in frame_data:
        frame_data = frame_data.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(frame_data)
    except Exception:
        return jsonify({"error": "Invalid base64 image data"}), 400

    result = image_analyzer.analyze_image(image_bytes)
    event_store.append("detection_logs", {
        "source": "live_feed",
        "fire_detected": result.get("fire_detected"),
        "scene_classification": result.get("scene_classification"),
        "confidence": result.get("confidence"),
        "severity": result.get("severity"),
        "latitude": latitude,
        "longitude": longitude,
    })

    if result.get("fire_detected"):
        alert_entry = _create_and_dispatch_alert({
            "type": "live_camera",
            "level": result["severity"],
            "title": "[LIVE] Live Camera Fire Detection",
            "message": f"Fire detected in live feed with {result['confidence']}% confidence.",
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": result.get("analysis_time", datetime.now(UTC).isoformat()),
        })
        result["alert_dispatch"] = alert_entry.get("dispatch")

    cloud_storage.store_event("live_feed_analysis", {
        "result": result,
        "location": {"latitude": latitude, "longitude": longitude},
    })
    return jsonify(result)


@app.route("/api/sensors", methods=["POST"])
def ingest_sensor_data():
    """Ingest sensor readings (temperature/smoke) and trigger alerts when thresholds are exceeded."""
    global latest_sensor_reading
    payload = request.json or {}

    temperature_c = float(payload.get("temperature_c", 0))
    smoke_ppm = float(payload.get("smoke_ppm", 0))
    humidity = float(payload.get("humidity", 0))
    location = payload.get("location", {})

    risk_score = min(100.0, temperature_c * 0.7 + smoke_ppm * 0.8 + max(0, (60 - humidity) * 0.3))
    if risk_score >= 80:
        level = "critical"
    elif risk_score >= 60:
        level = "high"
    elif risk_score >= 35:
        level = "moderate"
    else:
        level = "low"

    latest_sensor_reading = {
        "timestamp": datetime.now(UTC).isoformat(),
        "temperature_c": temperature_c,
        "smoke_ppm": smoke_ppm,
        "humidity": humidity,
        "risk_score": round(risk_score, 1),
        "level": level,
        "location": location,
    }
    event_store.append("sensor_readings", latest_sensor_reading)

    if level in ("critical", "high"):
        _create_and_dispatch_alert({
            "type": "sensor_threshold",
            "level": level,
            "title": "[SENSOR] Sensor Threshold Alert",
            "message": f"Sensors report temp {temperature_c:.1f}C and smoke {smoke_ppm:.1f} ppm. Risk {risk_score:.1f}.",
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "timestamp": latest_sensor_reading["timestamp"],
        })

    cloud_storage.store_event("sensor_ingestion", latest_sensor_reading)
    return jsonify({"status": "ok", "reading": latest_sensor_reading})


@app.route("/api/sensors", methods=["GET"])
def get_sensor_data():
    """Get the latest ingested sensor reading."""
    history = event_store.read_recent("sensor_readings", limit=100)
    return jsonify({"reading": latest_sensor_reading, "history": history})


@app.route("/api/sensors/history", methods=["GET"])
def get_sensor_history():
    """Get sensor reading history for charting."""
    limit = request.args.get("limit", 200, type=int)
    return jsonify({"history": event_store.read_recent("sensor_readings", limit=limit)})


@app.route("/api/incidents", methods=["GET"])
def get_incidents_history():
    """Get persisted fire incident history."""
    limit = request.args.get("limit", 200, type=int)
    return jsonify({"incidents": event_store.read_recent("fire_incidents", limit=limit)})


@app.route("/api/detections/history", methods=["GET"])
def get_detection_history():
    """Get persisted detection logs for uploads/live feed."""
    limit = request.args.get("limit", 200, type=int)
    return jsonify({"detections": event_store.read_recent("detection_logs", limit=limit)})


@app.route("/api/predictions", methods=["GET"])
def get_future_predictions():
    """Simple trend-based future prediction and pattern summary."""
    sensor_history = event_store.read_recent("sensor_readings", limit=120)
    incidents = event_store.read_recent("fire_incidents", limit=120)

    def _trend(values):
        if len(values) < 2:
            return 0.0
        return round((values[0] - values[-1]) / max(len(values) - 1, 1), 3)

    temps = [float(s.get("temperature_c", 0)) for s in sensor_history]
    smoke = [float(s.get("smoke_ppm", 0)) for s in sensor_history]
    risk = [float(s.get("risk_score", 0)) for s in sensor_history]

    temp_trend = _trend(temps)
    smoke_trend = _trend(smoke)
    risk_trend = _trend(risk)

    forecast_risk_30m = round((risk[0] if risk else 0) + risk_trend * 6, 1)
    if forecast_risk_30m >= 80:
        forecast_level = "critical"
    elif forecast_risk_30m >= 60:
        forecast_level = "high"
    elif forecast_risk_30m >= 35:
        forecast_level = "moderate"
    else:
        forecast_level = "low"

    return jsonify({
        "forecast": {
            "risk_score_30m": max(0, min(100, forecast_risk_30m)),
            "risk_level_30m": forecast_level,
            "incident_volume_recent": len(incidents),
        },
        "trends": {
            "temperature_per_step": temp_trend,
            "smoke_per_step": smoke_trend,
            "risk_per_step": risk_trend,
        },
        "patterns": {
            "hot_and_smoky": sum(1 for s in sensor_history if s.get("temperature_c", 0) > 40 and s.get("smoke_ppm", 0) > 50),
            "critical_incidents": sum(1 for i in incidents if i.get("level") == "critical"),
        }
    })


# ─── NEW: Fire History ────────────────────────────────────────────────

@app.route("/api/history", methods=["GET"])
def get_history():
    """Get fire detection history log."""
    limit = request.args.get("limit", 50, type=int)
    return jsonify({
        "history": fire_history_log[:limit],
        "total": len(fire_history_log),
    })


@app.route("/api/alert-history", methods=["GET"])
def get_alert_history():
    """Get alert history from alert manager."""
    limit = request.args.get("limit", 100, type=int)
    level = request.args.get("level")
    region = request.args.get("region")

    history = alert_manager.get_history(limit=limit, level=level, region=region)
    return jsonify({
        "alerts": history,
        "total": len(history),
    })


# ─── NEW: Notifications ──────────────────────────────────────────────

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Get pending notifications (polling endpoint)."""
    notifications = alert_manager.get_notifications()
    return jsonify({
        "notifications": notifications,
        "count": len(notifications),
    })


@app.route("/api/alerts/sms", methods=["POST"])
def configure_sms():
    """Configure Twilio SMS alerts and save to .env.
    
    Handles partial updates: if a field contains a masked value (has '**')
    the original .env value is preserved. This lets the user update just
    the to_number without re-entering their auth_token.
    """
    data = request.json or {}

    def _resolve(field_name, env_key):
        """Use the submitted value unless it is masked or empty, then keep .env value."""
        val = data.get(field_name, "")
        if not val or "**" in str(val):
            return os.getenv(env_key, "")
        return val.strip()

    account_sid = _resolve("account_sid", "TWILIO_ACCOUNT_SID")
    auth_token = _resolve("auth_token", "TWILIO_AUTH_TOKEN")
    from_number = _resolve("from_number", "TWILIO_FROM_NUMBER")
    to_number = _resolve("to_number", "TWILIO_TO_NUMBER")

    result = alert_manager.configure_twilio(
        account_sid=account_sid,
        auth_token=auth_token,
        from_number=from_number,
        to_number=to_number,
    )

    # Persist to .env
    _save_env("TWILIO_ACCOUNT_SID", account_sid)
    _save_env("TWILIO_AUTH_TOKEN", auth_token)
    _save_env("TWILIO_FROM_NUMBER", from_number)
    _save_env("TWILIO_TO_NUMBER", to_number)

    print(f"[SMS Config] Updated — enabled: {alert_manager.twilio_enabled}, to: {to_number}")

    return jsonify(result)


@app.route("/api/alerts/sms", methods=["DELETE"])
def disable_sms():
    """Disable Twilio SMS alerts."""
    return jsonify(alert_manager.disable_twilio())


@app.route("/api/alerts/mobile", methods=["POST"])
def configure_mobile_alerts():
    """Configure mobile push webhook alerts and save to .env."""
    data = request.json or {}
    
    webhook_url = _cfg(data.get("webhook_url"), "MOBILE_WEBHOOK_URL", "")
    api_key = _cfg(data.get("api_key"), "MOBILE_WEBHOOK_API_KEY", "")

    result = alert_manager.configure_mobile(
        webhook_url=webhook_url,
        api_key=api_key,
    )

    # Persist to .env
    _save_env("MOBILE_WEBHOOK_URL", webhook_url)
    _save_env("MOBILE_WEBHOOK_API_KEY", api_key)

    return jsonify(result)


@app.route("/api/alerts/mobile", methods=["DELETE"])
def disable_mobile_alerts():
    """Disable mobile alerts."""
    return jsonify(alert_manager.disable_mobile())


@app.route("/api/alerts/channels", methods=["GET"])
def get_alert_channels():
    """Get alert channel status and masked configuration."""
    return jsonify(alert_manager.get_channel_status())


@app.route("/api/alerts/test", methods=["POST"])
def send_test_alert():
    """Send a synthetic alert through all enabled channels."""
    data = request.json or {}
    alert = alert_manager.create_test_alert(
        title=data.get("title", "Test Fire Alert"),
        message=data.get("message", "This is a live channel test from FireWatch AI."),
    )
    socketio.emit("dashboard_alert", alert)
    event_store.append("fire_incidents", {
        "alert_type": alert.get("type"),
        "level": alert.get("level"),
        "title": alert.get("title"),
        "message": alert.get("message"),
        "latitude": alert.get("latitude"),
        "longitude": alert.get("longitude"),
        "source_timestamp": alert.get("timestamp"),
        "test_alert": True,
    })
    return jsonify({"status": "sent", "alert": alert})


@app.route("/api/alerts/sms/test", methods=["POST"])
def send_test_sms():
    """Send a direct test SMS to verify Twilio configuration works.
    
    This bypasses the alert system and cooldown — it directly calls Twilio
    to send a quick verification message so the user can confirm their
    credentials and phone numbers are correct.
    """
    if not alert_manager.twilio_enabled:
        return jsonify({
            "status": "failed",
            "error": "SMS is not configured. Please save your Twilio credentials first.",
        }), 400

    test_alert = {
        "type": "test_alert",
        "level": "high",
        "title": "FireWatch AI — SMS Test",
        "message": "Your SMS alert channel is working! Fire alerts will be sent to this number.",
        "latitude": None,
        "longitude": None,
    }
    result = alert_manager._send_sms_alert(test_alert)

    return jsonify({
        "status": result.get("status"),
        "to": alert_manager.twilio_config.get("to_number", "N/A") if alert_manager.twilio_config else "N/A",
        "sid": result.get("sid"),
        "error": result.get("error"),
    })


@app.route("/api/cloud/status", methods=["GET"])
def get_cloud_status():
    """Get cloud provider integration status."""
    return jsonify(cloud_storage.status())


# ─── NEW: Regions ─────────────────────────────────────────────────────

@app.route("/api/regions", methods=["GET"])
def get_regions():
    """Get predefined regions with fire counts."""
    _ensure_data()
    from ai_analyzer import REGIONS

    region_data = []
    for name, info in REGIONS.items():
        west, south, east, north = info["bbox"]
        fires_in_region = [
            f for f in current_fires
            if west <= f["longitude"] <= east and south <= f["latitude"] <= north
        ]

        severity_counts = {}
        for f in fires_in_region:
            sev = f["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        region_data.append({
            "name": name,
            "bbox": info["bbox"],
            "fire_count": len(fires_in_region),
            "severity_distribution": severity_counts,
            "avg_frp": round(sum(f["frp"] for f in fires_in_region) / max(len(fires_in_region), 1), 1),
            "dominant_severity": max(severity_counts, key=severity_counts.get) if severity_counts else "none",
        })

    region_data.sort(key=lambda r: r["fire_count"], reverse=True)
    return jsonify({"regions": region_data})


# ─── NEW: Visualization Data ──────────────────────────────────────────

@app.route("/api/visualization-data", methods=["GET"])
def get_visualization_data():
    """Get aggregated data for charts and visualizations."""
    _ensure_data()

    # Severity distribution
    severity_dist = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
    for f in current_fires:
        sev = f.get("severity", "low")
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

    # Regional distribution
    from ai_analyzer import REGIONS
    regional_dist = {}
    for name, info in REGIONS.items():
        west, south, east, north = info["bbox"]
        count = sum(1 for f in current_fires
                    if west <= f["longitude"] <= east and south <= f["latitude"] <= north)
        regional_dist[name] = count

    # FRP distribution (buckets)
    frp_buckets = {"0-10": 0, "10-25": 0, "25-50": 0, "50-100": 0, "100+": 0}
    for f in current_fires:
        frp = f.get("frp", 0)
        if frp < 10:
            frp_buckets["0-10"] += 1
        elif frp < 25:
            frp_buckets["10-25"] += 1
        elif frp < 50:
            frp_buckets["25-50"] += 1
        elif frp < 100:
            frp_buckets["50-100"] += 1
        else:
            frp_buckets["100+"] += 1

    # Day vs Night
    day_night = {"Day": 0, "Night": 0}
    for f in current_fires:
        if f.get("daynight", "D") == "D":
            day_night["Day"] += 1
        else:
            day_night["Night"] += 1

    # Confidence distribution
    conf_buckets = {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
    for f in current_fires:
        conf = f.get("confidence", 0)
        if conf < 25:
            conf_buckets["0-25"] += 1
        elif conf < 50:
            conf_buckets["25-50"] += 1
        elif conf < 75:
            conf_buckets["50-75"] += 1
        else:
            conf_buckets["75-100"] += 1

    sensor_history = event_store.read_recent("sensor_readings", limit=100)
    detection_history = event_store.read_recent("detection_logs", limit=100)

    scene_distribution = {"fire": 0, "sunlight": 0, "smoke": 0, "fog": 0, "normal": 0, "unknown": 0}
    for d in detection_history:
        scene = d.get("scene_classification", "unknown")
        scene_distribution[scene] = scene_distribution.get(scene, 0) + 1

    heatmap_points = [
        {
            "lat": f["latitude"],
            "lng": f["longitude"],
            "weight": round(min(1.0, (f.get("frp", 0) / 120.0) + 0.05), 3),
        }
        for f in current_fires[:2000]
    ]

    sensor_time_series = [
        {
            "timestamp": s.get("timestamp"),
            "temperature_c": s.get("temperature_c"),
            "smoke_ppm": s.get("smoke_ppm"),
            "humidity": s.get("humidity"),
            "risk_score": s.get("risk_score"),
        }
        for s in reversed(sensor_history)
    ]

    return jsonify({
        "severity_distribution": severity_dist,
        "regional_distribution": regional_dist,
        "frp_distribution": frp_buckets,
        "day_night": day_night,
        "confidence_distribution": conf_buckets,
        "scene_distribution": scene_distribution,
        "heatmap_points": heatmap_points,
        "sensor_time_series": sensor_time_series,
        "total_fires": len(current_fires),
        "sensor": latest_sensor_reading,
    })


# ─── WebSocket Events ─────────────────────────────────────────────

@socketio.on("connect")
def handle_connect():
    print("[WS] Client connected")
    if current_fires and current_analysis:
        socketio.emit("fire_update", {
            "fires": current_fires[:500],
            "analytics": current_analysis["analytics"],
            "alerts": current_analysis["alerts"][:20],
            "risk_assessments": current_analysis.get("risk_assessments", []),
            "clusters": current_analysis.get("clusters", []),
            "timestamp": current_analysis["analysis_time"],
        })


@socketio.on("disconnect")
def handle_disconnect():
    print("[WS] Client disconnected")


@socketio.on("request_refresh")
def handle_refresh():
    """Client-requested data refresh."""
    print("[WS] Manual refresh requested")
    fetch_and_analyze()


# ─── Startup ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[STARTUP] Forest Fire Detection System — Backend Starting...")
    print("   API: http://localhost:5000/api/")
    print("   Endpoints: /fires, /analytics, /risk-analysis, /alerts, /status")
    print("   New: /upload-image, /history, /alert-history, /regions, /visualization-data")
    print("   New: /notifications, /alerts/email, /alerts/sms, /alerts/mobile")
    print("   New: /live-feed/analyze, /sensors, /cloud/status")
    print("   New: /models/status")

    # Start background data fetcher
    updater = threading.Thread(target=background_updater, daemon=True)
    updater.start()

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
