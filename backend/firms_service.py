"""
NASA FIRMS Data Fetching Service
Fetches near real-time active fire data from NASA's FIRMS API.
Supports VIIRS S-NPP, VIIRS NOAA-20, and MODIS satellite sources.
"""

import os
import requests
import time
import io
from datetime import datetime, UTC

# NASA FIRMS API configuration
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Read MAP_KEY from env — register at https://firms.modaps.eosdis.nasa.gov/api/map_key/
DEFAULT_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "DEMO_KEY")

# Satellite sources
SOURCES = {
    "VIIRS_SNPP": "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20": "VIIRS_NOAA20_NRT",
    "MODIS": "MODIS_NRT",
}

# Regional bounding boxes for fallback queries (smaller than global)
REGIONAL_BBOXES = [
    ("-125,24,-66,50",   "North America"),   # Continental US
    ("-70,-35,-35,5",    "South America"),    # Brazil / Amazon
    ("10,-15,40,10",     "Central Africa"),   # Central Africa
    ("95,5,115,25",      "Southeast Asia"),   # SE Asia
    ("115,-40,155,-10",  "Australia"),        # Australia
    ("70,5,90,30",       "India"),            # India
    ("60,50,140,70",     "Siberia"),          # Siberia
    ("15,34,40,45",      "Mediterranean"),    # Mediterranean
]

# Cache configuration
_cache = {}
_cache_ttl = 300  # 5 minutes


def _try_pandas():
    """Lazy import pandas — not critical if missing."""
    try:
        import pandas as pd
        return pd
    except ImportError:
        return None


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
                self.fire_data = cached_data
                self.last_fetch_time = datetime.now(UTC).isoformat()
                return cached_data

        # Try primary bbox first
        fires = self._try_fetch_from_api(bbox, days, source)

        # If global bbox failed, try regional bboxes
        if not fires and bbox == "-180,-90,180,90":
            print("[FIRMS] Global bbox failed, trying regional queries...")
            fires = self._fetch_regional_fallback(days, source)

        # Final fallback: demo data
        if not fires:
            print("[FIRMS] All API attempts failed, using demo data.")
            fires = self._get_demo_data()

        # Update cache
        _cache[cache_key] = (time.time(), fires)
        self.fire_data = fires
        self.last_fetch_time = datetime.now(UTC).isoformat()

        print(f"[FIRMS] Returning {len(fires)} fire records.")
        return fires

    def _try_fetch_from_api(self, bbox, days, source):
        """Attempt a single FIRMS API fetch. Returns list of fires or empty list."""
        source_id = SOURCES.get(source, SOURCES["VIIRS_SNPP"])
        url = f"{FIRMS_BASE_URL}/{self.map_key}/{source_id}/{bbox}/{days}"

        try:
            print(f"[FIRMS] Fetching: {url[:120]}...")
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                print(f"[FIRMS] API returned status {response.status_code}")
                return []

            text = response.text.strip()
            if not text or text.startswith("<!") or text.startswith("{"):
                print(f"[FIRMS] API returned non-CSV response")
                return []

            fires = self._parse_csv_text(text, source)
            return fires

        except requests.exceptions.Timeout:
            print("[FIRMS] Request timed out")
            return []
        except requests.exceptions.ConnectionError:
            print("[FIRMS] Connection error")
            return []
        except Exception as e:
            print(f"[FIRMS] Unexpected error: {e}")
            return []

    def _fetch_regional_fallback(self, days, source):
        """Try fetching from multiple regional bboxes and merge results."""
        all_fires = []
        for bbox, region_name in REGIONAL_BBOXES:
            fires = self._try_fetch_from_api(bbox, days, source)
            if fires:
                print(f"[FIRMS] Got {len(fires)} fires from {region_name}")
                all_fires.extend(fires)
            # Small delay to be polite to the API
            time.sleep(0.2)

        return all_fires

    def _parse_csv_text(self, text, source):
        """Parse CSV text into fire records."""
        pd = _try_pandas()

        if pd is not None:
            return self._parse_with_pandas(text, source, pd)
        else:
            return self._parse_manual_csv(text, source)

    def _parse_with_pandas(self, text, source, pd):
        """Parse CSV using pandas."""
        try:
            df = pd.read_csv(io.StringIO(text))
            if df.empty:
                return []
            return self._process_dataframe(df, source)
        except Exception as e:
            print(f"[FIRMS] Pandas parse error: {e}")
            return self._parse_manual_csv(text, source)

    def _parse_manual_csv(self, text, source):
        """Fallback CSV parser without pandas."""
        import csv
        fires = []
        try:
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                try:
                    lat = float(row.get("latitude", 0))
                    lng = float(row.get("longitude", 0))
                    brightness = float(row.get("bright_ti4", row.get("brightness", 0)))
                    frp = float(row.get("frp", 0))
                    conf_raw = row.get("confidence", "nominal")

                    if isinstance(conf_raw, str) and not conf_raw.replace('.', '').isdigit():
                        confidence = {"low": 30, "nominal": 60, "n": 60, "high": 90, "h": 90, "l": 30}.get(
                            conf_raw.lower(), 50
                        )
                    else:
                        try:
                            confidence = int(float(conf_raw))
                        except Exception:
                            confidence = 50

                    acq_date = row.get("acq_date", "")
                    acq_time_raw = str(row.get("acq_time", "")).strip()
                    acq_time = acq_time_raw.zfill(4) if acq_time_raw.isdigit() else "0000"
                    daynight = row.get("daynight", "D")

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
                    continue
        except Exception as e:
            print(f"[FIRMS] Manual CSV parse error: {e}")

        return fires

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
                    try:
                        confidence = int(float(conf_raw))
                    except Exception:
                        confidence = 50

                acq_date = str(row.get(col_map.get("acq_date", "acq_date"), ""))
                acq_time_raw = str(row.get(col_map.get("acq_time", "acq_time"), "")).strip()
                acq_time = acq_time_raw.zfill(4) if acq_time_raw.isdigit() else "0000"
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
                    "acq_date": datetime.now(UTC).strftime("%Y-%m-%d"),
                    "acq_time": f"{random.randint(0,23):02d}:{random.randint(0,59):02d}",
                    "daynight": random.choice(["D", "N"]),
                    "satellite": "DEMO",
                    "severity": severity,
                })

        self.fire_data = demo_fires
        self.last_fetch_time = datetime.now(UTC).isoformat()
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
