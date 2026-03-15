"""
AI Image Fire Detection Engine
Analyzes uploaded images for fire/smoke presence using
color histogram analysis, brightness detection, and texture features.
"""

import numpy as np
from PIL import Image
import io
import base64
from datetime import datetime


class ImageAnalyzer:
    """Analyzes images for fire and smoke detection using computer vision heuristics."""

    # Fire color ranges in RGB
    FIRE_RED_RANGE = ((180, 0, 0), (255, 100, 50))
    FIRE_ORANGE_RANGE = ((200, 100, 0), (255, 200, 80))
    FIRE_YELLOW_RANGE = ((200, 180, 0), (255, 255, 100))
    SMOKE_RANGE = ((100, 100, 100), (200, 200, 210))

    def analyze_image(self, image_bytes):
        """
        Analyze an image for fire/smoke presence.

        Args:
            image_bytes: Raw image bytes

        Returns:
            dict with detection results
        """
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_array = np.array(img)

            # Run analysis pipeline
            fire_score = self._detect_fire_colors(img_array)
            smoke_score = self._detect_smoke(img_array)
            brightness_score = self._analyze_brightness(img_array)
            texture_score = self._analyze_texture(img_array)

            # Combined confidence
            combined_score = (
                fire_score * 0.45 +
                smoke_score * 0.20 +
                brightness_score * 0.20 +
                texture_score * 0.15
            )

            fire_detected = combined_score > 35
            confidence = min(round(combined_score, 1), 99.5)

            # Classify severity
            if combined_score >= 70:
                severity = "critical"
            elif combined_score >= 50:
                severity = "high"
            elif combined_score >= 35:
                severity = "moderate"
            else:
                severity = "low"

            # Generate regions of interest
            regions = self._find_fire_regions(img_array)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                fire_detected, severity, confidence, fire_score, smoke_score
            )

            # Create thumbnail for response
            thumb = img.copy()
            thumb.thumbnail((400, 400))
            buf = io.BytesIO()
            thumb.save(buf, format="JPEG", quality=80)
            thumbnail_b64 = base64.b64encode(buf.getvalue()).decode()

            return {
                "fire_detected": fire_detected,
                "confidence": confidence,
                "severity": severity,
                "scores": {
                    "fire_color": round(fire_score, 1),
                    "smoke": round(smoke_score, 1),
                    "brightness": round(brightness_score, 1),
                    "texture": round(texture_score, 1),
                },
                "regions_of_interest": regions,
                "recommendations": recommendations,
                "image_info": {
                    "width": img.width,
                    "height": img.height,
                    "thumbnail": f"data:image/jpeg;base64,{thumbnail_b64}",
                },
                "analysis_time": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "fire_detected": False,
                "confidence": 0,
                "severity": "low",
                "error": str(e),
                "analysis_time": datetime.utcnow().isoformat(),
            }

    def _detect_fire_colors(self, img_array):
        """Detect fire-like colors (red, orange, yellow) in the image."""
        r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]
        total_pixels = img_array.shape[0] * img_array.shape[1]

        # Red-dominant fire pixels
        red_fire = (r > 180) & (g < 120) & (b < 80) & (r > g * 1.5)
        # Orange fire pixels
        orange_fire = (r > 200) & (g > 80) & (g < 180) & (b < 80) & (r > g)
        # Bright yellow fire pixels
        yellow_fire = (r > 200) & (g > 170) & (b < 100) & (r > b * 2)
        # Intense white-hot fire
        hot_fire = (r > 240) & (g > 200) & (b > 150) & (r > b)

        fire_pixels = np.sum(red_fire | orange_fire | yellow_fire | hot_fire)
        fire_ratio = fire_pixels / total_pixels

        # Score: 0-100 based on fire pixel ratio
        score = min(fire_ratio * 500, 100)  # 20% fire pixels = 100 score
        return score

    def _detect_smoke(self, img_array):
        """Detect smoke-like regions (gray, hazy areas)."""
        r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]
        total_pixels = img_array.shape[0] * img_array.shape[1]

        # Smoke: similar R, G, B values (grayish) with moderate brightness
        channel_diff = np.maximum(
            np.abs(r.astype(int) - g.astype(int)),
            np.abs(g.astype(int) - b.astype(int))
        )
        avg_brightness = (r.astype(int) + g.astype(int) + b.astype(int)) / 3

        smoke_pixels = (channel_diff < 30) & (avg_brightness > 100) & (avg_brightness < 210)
        smoke_ratio = np.sum(smoke_pixels) / total_pixels

        # Elevated smoke presence
        score = min(smoke_ratio * 150, 100)
        return score

    def _analyze_brightness(self, img_array):
        """Analyze unusual brightness patterns (fire glow)."""
        brightness = np.mean(img_array, axis=2)

        # Very bright regions
        bright_ratio = np.sum(brightness > 200) / brightness.size
        # Very hot spots
        hot_ratio = np.sum(brightness > 240) / brightness.size

        # Brightness variance (fire scenes have high variance)
        variance = np.std(brightness) / 128.0  # Normalize

        score = (bright_ratio * 200 + hot_ratio * 300 + variance * 30)
        return min(score, 100)

    def _analyze_texture(self, img_array):
        """Analyze texture for flickering/irregular patterns typical of fire."""
        gray = np.mean(img_array, axis=2)

        # Simple edge detection via gradient magnitude
        grad_x = np.diff(gray, axis=1)
        grad_y = np.diff(gray, axis=0)

        # High gradient regions (edges/texture)
        edge_density = (np.mean(np.abs(grad_x)) + np.mean(np.abs(grad_y))) / 2

        # Fire has moderate-high texture
        score = min(edge_density / 20 * 100, 100)
        return score

    def _find_fire_regions(self, img_array):
        """Identify approximate regions where fire is detected."""
        r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]

        # Fire-like pixels
        fire_mask = (r > 180) & (g < 150) & (b < 100) & (r > g)

        h, w = fire_mask.shape
        grid_h, grid_w = 4, 4
        cell_h, cell_w = h // grid_h, w // grid_w

        regions = []
        for gy in range(grid_h):
            for gx in range(grid_w):
                cell = fire_mask[gy * cell_h:(gy + 1) * cell_h, gx * cell_w:(gx + 1) * cell_w]
                density = np.mean(cell)
                if density > 0.05:  # More than 5% fire pixels
                    regions.append({
                        "x": round(gx / grid_w * 100, 1),
                        "y": round(gy / grid_h * 100, 1),
                        "width": round(100 / grid_w, 1),
                        "height": round(100 / grid_h, 1),
                        "density": round(density * 100, 1),
                    })

        return regions

    def _generate_recommendations(self, detected, severity, confidence, fire_score, smoke_score):
        """Generate actionable recommendations based on analysis."""
        recs = []

        if not detected:
            recs.append({
                "type": "info",
                "title": "No Fire Detected",
                "message": "The image does not appear to contain fire or smoke. Continue routine monitoring."
            })
            if smoke_score > 20:
                recs.append({
                    "type": "caution",
                    "title": "Haze/Smoke Possible",
                    "message": f"Some haze or smoke-like patterns detected (score: {smoke_score:.0f}%). Consider verifying air quality."
                })
            return recs

        if severity == "critical":
            recs.extend([
                {"type": "danger", "title": "🚨 Critical Fire Alert",
                 "message": "Active high-intensity fire detected. Immediate emergency response recommended."},
                {"type": "action", "title": "Evacuate Area",
                 "message": "If this is a real-time image, initiate evacuation protocols in the affected area."},
                {"type": "action", "title": "Contact Emergency Services",
                 "message": "Alert local fire departments and emergency services immediately."},
            ])
        elif severity == "high":
            recs.extend([
                {"type": "warning", "title": "⚠️ High Fire Activity",
                 "message": "Significant fire activity detected. Monitor closely and prepare response teams."},
                {"type": "action", "title": "Deploy Monitoring",
                 "message": "Set up continuous satellite monitoring for the affected region."},
            ])
        elif severity == "moderate":
            recs.extend([
                {"type": "caution", "title": "Moderate Fire Indicators",
                 "message": f"Fire indicators detected with {confidence}% confidence. Could be controlled burn or early-stage wildfire."},
                {"type": "action", "title": "Verify Source",
                 "message": "Confirm whether this is a controlled burn or wildfire via ground reports."},
            ])

        if smoke_score > 30:
            recs.append({
                "type": "info", "title": "Smoke Detected",
                "message": f"Significant smoke presence detected (score: {smoke_score:.0f}%). Wind patterns may spread smoke to nearby areas."
            })

        return recs
