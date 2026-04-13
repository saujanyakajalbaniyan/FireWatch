"""
AI Fire Risk Analysis Engine
Computes risk scores, identifies fire clusters, and generates
natural-language risk assessments for active fire data.
"""

import numpy as np
from collections import defaultdict
from datetime import datetime, UTC


# Region definitions for analysis
REGIONS = {
    "North America": {"bbox": (-170, 15, -50, 72), "base_risk": 0.3},
    "South America": {"bbox": (-85, -57, -32, 14), "base_risk": 0.5},
    "Europe": {"bbox": (-25, 35, 45, 72), "base_risk": 0.2},
    "Africa": {"bbox": (-20, -35, 55, 38), "base_risk": 0.6},
    "Asia": {"bbox": (25, 5, 180, 75), "base_risk": 0.4},
    "Australia": {"bbox": (110, -48, 180, -10), "base_risk": 0.5},
}


class AIAnalyzer:
    def __init__(self):
        self.last_analysis_time = None
        self.cached_analysis = None

    def analyze_fires(self, fires):
        """
        Run full AI analysis on fire data.
        
        Returns:
            dict with analytics, risk_assessments, alerts, and clusters
        """
        if not fires:
            return self._empty_analysis()

        analytics = self._compute_analytics(fires)
        clusters = self._find_clusters(fires)
        risk_assessments = self._assess_regional_risks(fires, clusters)
        alerts = self._generate_alerts(fires, clusters)

        analysis = {
            "analytics": analytics,
            "clusters": clusters,
            "risk_assessments": risk_assessments,
            "alerts": alerts,
            "analysis_time": datetime.now(UTC).isoformat(),
            "total_fires_analyzed": len(fires),
        }

        self.cached_analysis = analysis
        self.last_analysis_time = datetime.now(UTC)
        return analysis

    def _compute_analytics(self, fires):
        """Compute aggregate statistics from fire data."""
        confidences = [f["confidence"] for f in fires]
        frps = [f["frp"] for f in fires]
        brightnesses = [f["brightness"] for f in fires]

        severity_counts = defaultdict(int)
        satellite_counts = defaultdict(int)
        daynight_counts = {"D": 0, "N": 0}

        for f in fires:
            severity_counts[f["severity"]] += 1
            satellite_counts[f["satellite"]] += 1
            daynight_counts[f.get("daynight", "D")] += 1

        return {
            "total_fires": len(fires),
            "avg_confidence": round(np.mean(confidences), 1),
            "max_confidence": max(confidences),
            "min_confidence": min(confidences),
            "avg_frp": round(np.mean(frps), 1),
            "max_frp": round(max(frps), 1),
            "total_frp": round(sum(frps), 1),
            "avg_brightness": round(np.mean(brightnesses), 1),
            "severity_distribution": dict(severity_counts),
            "satellite_distribution": dict(satellite_counts),
            "day_night_ratio": daynight_counts,
            "critical_count": severity_counts.get("critical", 0),
            "high_count": severity_counts.get("high", 0),
        }

    def _find_clusters(self, fires, distance_threshold=2.0):
        """
        Find fire clusters using simple spatial proximity.
        Groups nearby fires within distance_threshold degrees.
        """
        if not fires:
            return []

        points = np.array([[f["latitude"], f["longitude"]] for f in fires])

        # Simple grid-based clustering
        visited = set()
        clusters = []

        for i, fire in enumerate(fires):
            if i in visited:
                continue

            cluster_fires = [fire]
            visited.add(i)

            for j, other in enumerate(fires):
                if j in visited:
                    continue
                dist = np.sqrt(
                    (fire["latitude"] - other["latitude"]) ** 2 +
                    (fire["longitude"] - other["longitude"]) ** 2
                )
                if dist < distance_threshold:
                    cluster_fires.append(other)
                    visited.add(j)

            if len(cluster_fires) >= 3:  # Only report clusters with 3+ fires
                center_lat = np.mean([f["latitude"] for f in cluster_fires])
                center_lng = np.mean([f["longitude"] for f in cluster_fires])
                avg_frp = np.mean([f["frp"] for f in cluster_fires])
                max_conf = max([f["confidence"] for f in cluster_fires])
                total_frp = sum([f["frp"] for f in cluster_fires])

                # Determine cluster severity
                if len(cluster_fires) >= 15 or total_frp > 500:
                    cluster_severity = "critical"
                elif len(cluster_fires) >= 8 or total_frp > 200:
                    cluster_severity = "high"
                elif len(cluster_fires) >= 5:
                    cluster_severity = "moderate"
                else:
                    cluster_severity = "low"

                region = self._point_to_region(center_lat, center_lng)

                clusters.append({
                    "id": f"cluster_{len(clusters)}",
                    "center_lat": round(center_lat, 4),
                    "center_lng": round(center_lng, 4),
                    "fire_count": len(cluster_fires),
                    "avg_frp": round(avg_frp, 1),
                    "max_confidence": max_conf,
                    "total_frp": round(total_frp, 1),
                    "severity": cluster_severity,
                    "region": region,
                    "radius_deg": round(distance_threshold, 2),
                })

        # Sort clusters by severity/fire_count
        severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
        clusters.sort(key=lambda c: (severity_order.get(c["severity"], 4), -c["fire_count"]))

        return clusters

    def _assess_regional_risks(self, fires, clusters):
        """Generate AI risk assessments per region."""
        region_fires = defaultdict(list)
        for f in fires:
            region = self._point_to_region(f["latitude"], f["longitude"])
            region_fires[region].append(f)

        assessments = []
        for region_name, region_info in REGIONS.items():
            r_fires = region_fires.get(region_name, [])
            r_clusters = [c for c in clusters if c["region"] == region_name]

            # Compute region risk score
            fire_density_score = min(len(r_fires) / 50, 1.0) * 30
            cluster_score = min(len(r_clusters) / 5, 1.0) * 25

            if r_fires:
                avg_confidence = np.mean([f["confidence"] for f in r_fires])
                avg_frp = np.mean([f["frp"] for f in r_fires])
                confidence_score = (avg_confidence / 100) * 25
                intensity_score = min(avg_frp / 100, 1.0) * 20
            else:
                avg_confidence = 0
                avg_frp = 0
                confidence_score = 0
                intensity_score = 0

            risk_score = fire_density_score + cluster_score + confidence_score + intensity_score
            risk_score = min(round(risk_score + region_info["base_risk"] * 10, 1), 100)

            # Classify risk level
            if risk_score >= 75:
                risk_level = "critical"
            elif risk_score >= 50:
                risk_level = "high"
            elif risk_score >= 25:
                risk_level = "moderate"
            else:
                risk_level = "low"

            # Generate assessment text
            assessment_text = self._generate_assessment_text(
                region_name, len(r_fires), len(r_clusters), risk_level,
                avg_confidence, avg_frp, risk_score
            )

            assessments.append({
                "region": region_name,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "fire_count": len(r_fires),
                "cluster_count": len(r_clusters),
                "avg_confidence": round(avg_confidence, 1),
                "avg_frp": round(avg_frp, 1),
                "assessment": assessment_text,
                "bbox": region_info["bbox"],
            })

        # Sort by risk score descending
        assessments.sort(key=lambda a: a["risk_score"], reverse=True)
        return assessments

    def _generate_assessment_text(self, region, fire_count, cluster_count,
                                   risk_level, avg_confidence, avg_frp, score):
        """Generate natural-language risk assessment."""
        if fire_count == 0:
            return f"No active fires currently detected in {region}. Conditions appear stable."

        level_desc = {
            "critical": "extremely high",
            "high": "significantly elevated",
            "moderate": "moderately elevated",
            "low": "relatively low"
        }

        text = f"Fire risk in {region} is {level_desc[risk_level]} (score: {score}/100). "
        text += f"Currently tracking {fire_count} active fire{'s' if fire_count > 1 else ''}"

        if cluster_count > 0:
            text += f" forming {cluster_count} distinct cluster{'s' if cluster_count > 1 else ''}"

        text += ". "

        if avg_frp > 50:
            text += f"High average Fire Radiative Power ({avg_frp:.1f} MW) indicates intense burning. "
        elif avg_frp > 20:
            text += f"Moderate Fire Radiative Power ({avg_frp:.1f} MW) suggests active burning. "

        if avg_confidence > 80:
            text += "Detection confidence is high, indicating reliable satellite observations. "
        elif avg_confidence > 50:
            text += "Detection confidence is moderate. "

        if risk_level in ("critical", "high"):
            text += "[WARNING] Immediate monitoring recommended."
        elif risk_level == "moderate":
            text += "Continued observation advised."

        return text

    def _generate_alerts(self, fires, clusters):
        """Generate alert notifications for significant fire events."""
        alerts = []

        # Alert for critical/high severity individual fires
        for fire in fires:
            if fire["severity"] == "critical":
                alerts.append({
                    "type": "critical_fire",
                    "level": "critical",
                    "title": "[CRITICAL] Critical Fire Detected",
                    "message": f"High-intensity fire at ({fire['latitude']:.3f}, {fire['longitude']:.3f}) "
                               f"with FRP {fire['frp']} MW and {fire['confidence']}% confidence.",
                    "latitude": fire["latitude"],
                    "longitude": fire["longitude"],
                    "timestamp": f"{fire['acq_date']} {fire['acq_time']}",
                    "fire_id": fire["id"],
                })

        # Alert for large clusters
        for cluster in clusters:
            if cluster["severity"] in ("critical", "high"):
                alerts.append({
                    "type": "fire_cluster",
                    "level": cluster["severity"],
                    "title": f"[{cluster['severity'].upper()}] Large Fire Cluster — {cluster['region']}",
                    "message": f"Cluster of {cluster['fire_count']} fires detected near "
                               f"({cluster['center_lat']:.2f}, {cluster['center_lng']:.2f}) "
                               f"with total FRP of {cluster['total_frp']} MW.",
                    "latitude": cluster["center_lat"],
                    "longitude": cluster["center_lng"],
                    "timestamp": datetime.now(UTC).isoformat(),
                    "cluster_id": cluster["id"],
                })

        # Sort by severity
        level_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
        alerts.sort(key=lambda a: level_order.get(a["level"], 4))

        return alerts[:50]  # Cap to top 50 alerts

    def _point_to_region(self, lat, lng):
        """Determine which region a lat/lng point belongs to."""
        for name, info in REGIONS.items():
            west, south, east, north = info["bbox"]
            if west <= lng <= east and south <= lat <= north:
                return name
        return "Other"

    def _empty_analysis(self):
        """Return empty analysis structure."""
        return {
            "analytics": {
                "total_fires": 0, "avg_confidence": 0, "max_confidence": 0,
                "min_confidence": 0, "avg_frp": 0, "max_frp": 0, "total_frp": 0,
                "avg_brightness": 0, "severity_distribution": {},
                "satellite_distribution": {}, "day_night_ratio": {"D": 0, "N": 0},
                "critical_count": 0, "high_count": 0,
            },
            "clusters": [],
            "risk_assessments": [],
            "alerts": [],
            "analysis_time": datetime.now(UTC).isoformat(),
            "total_fires_analyzed": 0,
        }
