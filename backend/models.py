from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC

db = SQLAlchemy()

class FireIncident(db.Model):
    __tablename__ = 'fire_incidents'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String, default=lambda: datetime.now(UTC).isoformat(), index=True)
    alert_type = db.Column(db.String)
    level = db.Column(db.String)
    title = db.Column(db.String)
    message = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    source_timestamp = db.Column(db.String, nullable=True)
    test_alert = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "alert_type": self.alert_type,
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "source_timestamp": self.source_timestamp,
            "test_alert": self.test_alert
        }


class DetectionLog(db.Model):
    __tablename__ = 'detection_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String, default=lambda: datetime.now(UTC).isoformat(), index=True)
    source = db.Column(db.String)
    fire_detected = db.Column(db.Boolean, default=False)
    scene_classification = db.Column(db.String)
    confidence = db.Column(db.Float)
    severity = db.Column(db.String)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "source": self.source,
            "fire_detected": self.fire_detected,
            "scene_classification": self.scene_classification,
            "confidence": self.confidence,
            "severity": self.severity,
            "latitude": self.latitude,
            "longitude": self.longitude
        }


class SensorReading(db.Model):
    __tablename__ = 'sensor_readings'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String, default=lambda: datetime.now(UTC).isoformat(), index=True)
    temperature_c = db.Column(db.Float)
    smoke_ppm = db.Column(db.Float)
    humidity = db.Column(db.Float)
    risk_score = db.Column(db.Float)
    level = db.Column(db.String)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "temperature_c": self.temperature_c,
            "smoke_ppm": self.smoke_ppm,
            "humidity": self.humidity,
            "risk_score": self.risk_score,
            "level": self.level,
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude
            } if self.latitude is not None else {}
        }
