"""
NASA FIRMS Data Fetching Service
Fetches near real-time active fire data from NASA's FIRMS API.
Supports VIIRS S-NPP, VIIRS NOAA-20, and MODIS satellite sources.
"""

import requests
import pandas as pd
import time
import io
from datetime import datetime

# NASA FIRMS API configuration
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Demo MAP_KEY — register your own at https://firms.modaps.eosdis.nasa.gov/api/map_key/
DEFAULT_MAP_KEY = "DEMO_KEY"

# Satellite sources
SOURCES = {
    "VIIRS_SNPP": "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20": "VIIRS_NOAA20_NRT",
    "MODIS": "MODIS_NRT",
}

# Cache configuration
_cache = {}
_cache_ttl = 300  # 5 minutes


class FIRMSService:
    def __init__(self, map_key=None):
        self.map_key = map_key or DEFAULT_MAP_KEY
        self.last_fetch_time = None
        self.fire_data = []

    def fetch_fires(self, bbox="-180,-90,180,90", days=1, source="VIIRS_SNPP"):
        """
        Fetch active fire data from NASA FIRMS.
        
        Args:
            bbox: Bounding box as "west,south,east,north"
            days: Number of days to query (1-5)
            source: Satellite source key
        
        Returns:
            List of fire records as dicts
        """
        cache_key = f"{source}_{bbox}_{days}"

        # Check cache
        if cache_key in _cache:
            cached_time, cached_data = _cache[cache_key]
            if time.time() - cached_time < _cache_ttl:
                return cached_data

        source_id = SOURCES.get(source, SOURCES["VIIRS_SNPP"])
        url = f"{FIRMS_BASE_URL}/{self.map_key}/{source_id}/{bbox}/{days}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse CSV data
            df = pd.read_csv(io.StringIO(response.text))

            if df.empty:
                print("[FIRMS] API returned empty data, using demo data.")
                return self._get_demo_data()

            fires = self._process_dataframe(df, source)

            if not fires:
                print("[FIRMS] No fires parsed from API response, using demo data.")
                return self._get_demo_data()

            # Update cache
            _cache[cache_key] = (time.time(), fires)
            self.fire_data = fires
            self.last_fetch_time = datetime.utcnow().isoformat()

            return fires

        except requests.exceptions.RequestException as e:
            print(f"[FIRMS] Error fetching data: {e}")
            # Return cached data if available
            if cache_key in _cache:
                return _cache[cache_key][1]
            return self._get_demo_data()

        except Exception as e:
            print(f"[FIRMS] Unexpected error: {e}")
            return self._get_demo_data()

    def _process_dataframe(self, df, source):
        """Process raw FIRMS CSV DataFrame into structured fire records."""
        fires = []

        # Normalize column names (different sources have slightly different schemas)
        col_map = {}
        for col in df.columns:
            lower = col.lower()
            if lower == "latitude":
                col_map["latitude"] = col
            elif lower == "longitude":
                col_map["longitude"] = col
            elif lower in ("bright_ti4", "brightness"):
                col_map["brightness"] = col
            elif lower == "frp":
                col_map["frp"] = col
            elif lower == "confidence":
                col_map["confidence"] = col
            elif lower == "acq_date":
                col_map["acq_date"] = col
            elif lower == "acq_time":
                col_map["acq_time"] = col
            elif lower == "daynight":
                col_map["daynight"] = col

        for _, row in df.iterrows():
            try:
                lat = float(row.get(col_map.get("latitude", "latitude"), 0))
                lng = float(row.get(col_map.get("longitude", "longitude"), 0))
                brightness = float(row.get(col_map.get("brightness", "bright_ti4"), 0))
                frp = float(row.get(col_map.get("frp", "frp"), 0))

                # Handle confidence — can be text (low/nominal/high) or numeric
                conf_raw = row.get(col_map.get("confidence", "confidence"), "nominal")
                if isinstance(conf_raw, str):
                    confidence = {"low": 30, "nominal": 60, "n": 60, "high": 90, "h": 90, "l": 30}.get(
                        conf_raw.lower(), 50
                    )
                else:
                    confidence = int(conf_raw)

                acq_date = str(row.get(col_map.get("acq_date", "acq_date"), ""))
                acq_time = str(row.get(col_map.get("acq_time", "acq_time"), "")).zfill(4)
                daynight = str(row.get(col_map.get("daynight", "daynight"), "D"))

                # Determine severity
                severity = self._classify_severity(confidence, frp, brightness)

                fires.append({
                    "id": f"{source}_{lat}_{lng}_{acq_date}_{acq_time}",
                    "latitude": lat,
                    "longitude": lng,
                    "brightness": brightness,
                    "frp": frp,
                    "confidence": confidence,
                    "acq_date": acq_date,
                    "acq_time": f"{acq_time[:2]}:{acq_time[2:]}",
                    "daynight": daynight,
                    "satellite": source,
                    "severity": severity,
                })
            except Exception as e:
                print(f"[FIRMS] Error processing row: {e}")
                continue

        return fires

    def _classify_severity(self, confidence, frp, brightness):
        """Classify fire severity based on multiple indicators."""
        score = 0
        score += min(confidence / 100 * 40, 40)  # confidence contributes up to 40
        score += min(frp / 100 * 30, 30)           # FRP contributes up to 30
        score += min(brightness / 500 * 30, 30)    # brightness contributes up to 30

        if score >= 70:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 30:
            return "moderate"
        else:
            return "low"

    def _get_demo_data(self):
        """Return demo data when API is unavailable."""
        import random
        demo_fires = []
        # Generate realistic demo fire data across globally active fire regions
        regions = [
            {"name": "Amazon", "lat_range": (-15, -3), "lng_range": (-65, -45)},
            {"name": "Central Africa", "lat_range": (-10, 5), "lng_range": (15, 30)},
            {"name": "Southeast Asia", "lat_range": (10, 20), "lng_range": (95, 110)},
            {"name": "Australia", "lat_range": (-35, -20), "lng_range": (120, 150)},
            {"name": "Western US", "lat_range": (33, 45), "lng_range": (-122, -110)},
            {"name": "Siberia", "lat_range": (55, 65), "lng_range": (90, 130)},
            {"name": "Mediterranean", "lat_range": (35, 42), "lng_range": (20, 35)},
            {"name": "India", "lat_range": (15, 28), "lng_range": (75, 85)},
        ]

        for region in regions:
            num_fires = random.randint(5, 25)
            for i in range(num_fires):
                lat = random.uniform(*region["lat_range"])
                lng = random.uniform(*region["lng_range"])
                confidence = random.randint(20, 100)
                frp = round(random.uniform(1, 200), 1)
                brightness = round(random.uniform(300, 500), 1)
                severity = self._classify_severity(confidence, frp, brightness)

                demo_fires.append({
                    "id": f"DEMO_{region['name']}_{i}",
                    "latitude": round(lat, 4),
                    "longitude": round(lng, 4),
                    "brightness": brightness,
                    "frp": frp,
                    "confidence": confidence,
                    "acq_date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "acq_time": f"{random.randint(0,23):02d}:{random.randint(0,59):02d}",
                    "daynight": random.choice(["D", "N"]),
                    "satellite": "DEMO",
                    "severity": severity,
                })

        self.fire_data = demo_fires
        self.last_fetch_time = datetime.utcnow().isoformat()
        return demo_fires

    def get_fires_by_region(self, region_bbox, days=1):
        """Fetch fires for a specific region bounding box."""
        return self.fetch_fires(bbox=region_bbox, days=days)

    def get_all_sources(self, bbox="-180,-90,180,90", days=1):
        """Fetch fires from all satellite sources and merge."""
        all_fires = []
        for source_key in SOURCES:
            fires = self.fetch_fires(bbox=bbox, days=days, source=source_key)
            all_fires.extend(fires)
        return all_fires
