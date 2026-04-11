import os
import json
from app import app, db
from models import FireIncident, DetectionLog, SensorReading

def migrate():
    event_logs_dir = os.path.join(os.path.dirname(__file__), "uploads", "event_logs")
    if not os.path.exists(event_logs_dir):
        print(f"Directory {event_logs_dir} does not exist. Nothing to migrate.")
        return

    with app.app_context():
        for filename in os.listdir(event_logs_dir):
            if not filename.endswith(".jsonl"):
                continue
            
            filepath = os.path.join(event_logs_dir, filename)
            category = filename.replace(".jsonl", "")
            print(f"Migrating category: {category}...")
            
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            count = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    timestamp = payload.get("timestamp")
                    
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
                        db.session.add(record)
                        count += 1
                        
                    elif category == "detection_logs":
                        record = DetectionLog(
                            timestamp=timestamp,
                            source=payload.get("source", "unknown"),
                            fire_detected=payload.get("fire_detected", False),
                            scene_classification=payload.get("scene_classification"),
                            confidence=payload.get("confidence"),
                            severity=payload.get("severity"),
                            latitude=payload.get("latitude"),
                            longitude=payload.get("longitude")
                        )
                        db.session.add(record)
                        count += 1
                        
                    elif category == "sensor_readings":
                        loc = payload.get("location", {})
                        if isinstance(loc, dict):
                            lat = loc.get("latitude")
                            lon = loc.get("longitude")
                        else:
                            lat = payload.get("latitude")
                            lon = payload.get("longitude")
                            
                        record = SensorReading(
                            timestamp=timestamp,
                            temperature_c=payload.get("temperature_c"),
                            smoke_ppm=payload.get("smoke_ppm"),
                            humidity=payload.get("humidity"),
                            risk_score=payload.get("risk_score"),
                            level=payload.get("level"),
                            latitude=lat,
                            longitude=lon
                        )
                        db.session.add(record)
                        count += 1
                        
                except Exception as e:
                    print(f"Error migrating line: {e}")
            
            db.session.commit()
            print(f"Successfully migrated {count} records from {filename}.")
            
            # Optionally rename the file so it's not migrated twice
            os.rename(filepath, filepath + ".migrated")

if __name__ == "__main__":
    migrate()
