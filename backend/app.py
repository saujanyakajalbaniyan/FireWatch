"""
Forest Fire Detection System — Flask Backend
Main application with REST API and WebSocket real-time updates.
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from firms_service import FIRMSService
from ai_analyzer import AIAnalyzer
from image_analyzer import ImageAnalyzer
from alert_manager import AlertManager
import threading
import time

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize services
firms = FIRMSService()
analyzer = AIAnalyzer()
image_analyzer = ImageAnalyzer()
alert_manager = AlertManager()

# Global state
current_fires = []
current_analysis = None
is_fetching = False
fire_history_log = []


def fetch_and_analyze():
    """Fetch fire data and run analysis."""
    global current_fires, current_analysis, is_fetching

    is_fetching = True

    try:
        fires = firms.fetch_fires(bbox="-180,-90,180,90", days=1, source="VIIRS_SNPP")
        current_fires = fires
        current_analysis = analyzer.analyze_fires(fires)
        print(f"[Server] Fetched {len(fires)} fires, analysis complete.")

        # Log alerts to history
        if current_analysis and current_analysis.get("alerts"):
            alert_manager.add_alerts_batch(current_analysis["alerts"][:20])

        # Log fire event to history
        alert_manager.log_fire_event(fires, current_analysis.get("analysis_time", ""))

        # Store in fire history
        _log_fire_snapshot(fires, current_analysis)

        # Push update to connected clients
        socketio.emit("fire_update", {
            "fires": fires[:500],
            "analytics": current_analysis["analytics"],
            "alerts": current_analysis["alerts"][:20],
            "timestamp": current_analysis["analysis_time"],
        })
    except Exception as e:
        print(f"[Server] Error in fetch_and_analyze: {e}")
    finally:
        is_fetching = False


def _log_fire_snapshot(fires, analysis):
    """Store a snapshot for fire history."""
    global fire_history_log
    from datetime import datetime

    if not fires:
        return

    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
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
    while True:
        fetch_and_analyze()
        time.sleep(300)  # Refresh every 5 minutes


# ─── REST API Endpoints ─────────────────────────────────────────────

@app.route("/api/fires", methods=["GET"])
def get_fires():
    """Get current active fires, optionally filtered by region."""
    if not current_fires:
        fetch_and_analyze()

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
    if not current_analysis:
        fetch_and_analyze()

    return jsonify({
        "analytics": current_analysis["analytics"] if current_analysis else {},
        "last_updated": current_analysis["analysis_time"] if current_analysis else None,
    })


@app.route("/api/risk-analysis", methods=["GET"])
def get_risk_analysis():
    """Get AI-generated risk assessments per region."""
    if not current_analysis:
        fetch_and_analyze()

    return jsonify({
        "risk_assessments": current_analysis["risk_assessments"] if current_analysis else [],
        "clusters": current_analysis["clusters"] if current_analysis else [],
        "last_updated": current_analysis["analysis_time"] if current_analysis else None,
    })


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Get fire alerts sorted by severity."""
    if not current_analysis:
        fetch_and_analyze()

    limit = request.args.get("limit", 50, type=int)
    level = request.args.get("level")

    alerts = current_analysis["alerts"] if current_analysis else []
    if level:
        alerts = [a for a in alerts if a["level"] == level]

    return jsonify({
        "alerts": alerts[:limit],
        "total": len(alerts),
        "last_updated": current_analysis["analysis_time"] if current_analysis else None,
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
    })


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

    # If fire detected, create an alert
    if result.get("fire_detected"):
        alert_manager.add_alert({
            "type": "image_analysis",
            "level": result["severity"],
            "title": f"📸 Fire Detected in Uploaded Image",
            "message": f"AI analysis detected fire with {result['confidence']}% confidence. "
                       f"Severity: {result['severity'].upper()}.",
            "latitude": None,
            "longitude": None,
            "timestamp": result["analysis_time"],
        })

    return jsonify(result)


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


# ─── NEW: Email Alert Configuration ──────────────────────────────────

@app.route("/api/alerts/email", methods=["POST"])
def configure_email():
    """Configure email alert settings."""
    data = request.json
    if not data:
        return jsonify({"error": "No configuration provided"}), 400

    result = alert_manager.configure_email(
        smtp_server=data.get("smtp_server", "smtp.gmail.com"),
        smtp_port=data.get("smtp_port", 587),
        sender_email=data.get("sender_email", ""),
        sender_password=data.get("sender_password", ""),
        recipient_email=data.get("recipient_email", ""),
    )
    return jsonify(result)


@app.route("/api/alerts/email", methods=["DELETE"])
def disable_email():
    """Disable email alerts."""
    result = alert_manager.disable_email()
    return jsonify(result)


# ─── NEW: Regions ─────────────────────────────────────────────────────

@app.route("/api/regions", methods=["GET"])
def get_regions():
    """Get predefined regions with fire counts."""
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
    if not current_fires:
        return jsonify({"error": "No data available"}), 404

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

    return jsonify({
        "severity_distribution": severity_dist,
        "regional_distribution": regional_dist,
        "frp_distribution": frp_buckets,
        "day_night": day_night,
        "confidence_distribution": conf_buckets,
        "total_fires": len(current_fires),
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
    print("🔥 Forest Fire Detection System — Backend Starting...")
    print("   API: http://localhost:5000/api/")
    print("   Endpoints: /fires, /analytics, /risk-analysis, /alerts, /status")
    print("   New: /upload-image, /history, /alert-history, /regions, /visualization-data")
    print("   New: /notifications, /alerts/email")

    # Start background data fetcher
    updater = threading.Thread(target=background_updater, daemon=True)
    updater.start()

    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
