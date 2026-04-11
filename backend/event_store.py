"""Persistent JSONL event store for incidents, sensors, and detections."""

from datetime import datetime, UTC
from models import db, FireIncident, DetectionLog, SensorReading

class EventStore:
    def __init__(self, base_dir=None):
        # base_dir is kept for signature compatibility but ignored, as we use DB now
        self._lock = None

    def append(self, category, payload):
        timestamp = datetime.now(UTC).isoformat()
        
        record = None
        if category == "fire_incidents":
            record = FireIncident(
                timestamp=timestamp,
                alert_type=payload.get("alert_type"),
                level=payload.get("level"),
                title=payload.get("title"),
                message=payload.get("message"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                source_timestamp=payload.get("source_timestamp"),
                test_alert=payload.get("test_alert", False)
            )
        elif category == "detection_logs":
            record = DetectionLog(
                timestamp=timestamp,
                source=payload.get("source"),
                fire_detected=payload.get("fire_detected", False),
                scene_classification=payload.get("scene_classification"),
                confidence=payload.get("confidence"),
                severity=payload.get("severity"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude")
            )
        elif category == "sensor_readings":
            loc = payload.get("location", {})
            record = SensorReading(
                timestamp=timestamp,
                temperature_c=payload.get("temperature_c"),
                smoke_ppm=payload.get("smoke_ppm"),
                humidity=payload.get("humidity"),
                risk_score=payload.get("risk_score"),
                level=payload.get("level"),
                latitude=loc.get("latitude"),
                longitude=loc.get("longitude")
            )
            
        if record:
            db.session.add(record)
            db.session.commit()
            return record.to_dict()
            
        return {"timestamp": timestamp, **payload}

    def read_recent(self, category, limit=200):
        items = []
        if category == "fire_incidents":
            records = FireIncident.query.order_by(FireIncident.id.desc()).limit(limit).all()
            items = [r.to_dict() for r in records]
        elif category == "detection_logs":
            records = DetectionLog.query.order_by(DetectionLog.id.desc()).limit(limit).all()
            items = [r.to_dict() for r in records]
        elif category == "sensor_readings":
            records = SensorReading.query.order_by(SensorReading.id.desc()).limit(limit).all()
            items = [r.to_dict() for r in records]
        
        return items
