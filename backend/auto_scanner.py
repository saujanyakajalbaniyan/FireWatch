import threading
import time
import requests
from flask import current_app

class AutoScanner:
    def __init__(self, app, image_analyzer, alert_manager, event_store, socketio):
        self.app = app
        self.image_analyzer = image_analyzer
        self.alert_manager = alert_manager
        self.event_store = event_store
        self.socketio = socketio
        self.running = False
        self.interval = 10  # Seconds
        self.thread = None
        self.scan_index = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.thread.start()
        print(f"[AutoScanner] Background image scanner started. Running every {self.interval} seconds.")

    def stop(self):
        self.running = False

    def _scan_loop(self):
        while self.running:
            try:
                # We must run within app context for SQLAlchemy to work
                # if event_store writes directly to DB without an isolated session thread.
                with self.app.app_context():
                    self._perform_scan()
            except Exception as e:
                print(f"[AutoScanner] Error in scan loop: {e}")
                
            time.sleep(self.interval)

    def _perform_scan(self):
        try:
            import os
            import random
            import json
            
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            valid_exts = (".jpg", ".jpeg", ".webp", ".png", ".avif", ".avg")
            jpg_files = sorted([f for f in os.listdir(project_root) if f.lower().endswith(valid_exts)])
            
            if not jpg_files:
                print(f"[AutoScanner] No valid image files {valid_exts} found in the project root.", flush=True)
                return
                
            self.scan_index = (self.scan_index + 1) % len(jpg_files)
            selected_file = jpg_files[self.scan_index]
            file_path = os.path.join(project_root, selected_file)
            
            print(f"[AutoScanner] Reading local image {selected_file}...", flush=True)
            
            with open(file_path, "rb") as f:
                img_bytes = f.read()

            print(f"[AutoScanner] Image {selected_file} loaded. Analyzing...", flush=True)

            # 2. Analyze the image using the existing engine
            analysis = self.image_analyzer.analyze_image(img_bytes)

            # 3. Log the detection
            log_entry = {
                "source": "auto_scanner_API",
                "fire_detected": bool(analysis["fire_detected"]),
                "scene_classification": str(analysis["scene_classification"]),
                "confidence": float(analysis["confidence"]),
                "severity": str(analysis["severity"])
            }
            self.event_store.append("detection_logs", log_entry)

            # 4. If fire is detected, alert!
            if analysis["fire_detected"]:
                print(f"[AutoScanner] [ALERT] FIRE DETECTED in random image! Conf: {analysis['confidence']}%, Sev: {analysis['severity']}")
                
                if analysis["severity"] in ["critical", "high"]:
                    alert = {
                        "alert_type": "auto_scan",
                        "level": str(analysis["severity"]),
                        "title": f"{str(analysis['severity']).upper()} Fire (Auto-Scan)",
                        "message": f"Background AI caught a {analysis['severity']} fire signature with {analysis['confidence']}% confidence.",
                        "latitude": None,
                        "longitude": None
                    }
                    self.alert_manager.add_alert(alert)
            else:
                # Silent monitoring state
                print(f"[AutoScanner] Checked random image. No fire detected (Conf: {analysis['confidence']}%).")
                
            # Broadcast the scan to the frontend Footage Analysis tab
            # Sanitize numpy types to native Python types for JSON serialization
            def sanitize(obj):
                import numpy as np
                if isinstance(obj, dict):
                    return {k: sanitize(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [sanitize(v) for v in obj]
                elif isinstance(obj, (np.bool_, )):
                    return bool(obj)
                elif isinstance(obj, (np.integer, )):
                    return int(obj)
                elif isinstance(obj, (np.floating, )):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return obj

            safe_analysis = sanitize(analysis)
            safe_log = sanitize(log_entry)

            self.socketio.emit('auto_scan_update', {
                'log': safe_log,
                'analysis': safe_analysis
            })
                
        except Exception as e:
            import traceback
            print(f"[AutoScanner] Scan failed: {e}")
            traceback.print_exc()

