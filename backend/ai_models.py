"""
Hybrid AI model engine for fire detection.
Supports YOLOv8 object detection and EfficientNet classification.
"""

import os
from typing import Any, Dict, List

import numpy as np

try:
    import torch
    from torchvision import models, transforms
except Exception:
    torch = None
    models = None
    transforms = None

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


class AIModelEngine:
    """Runs YOLOv8 and EfficientNet inference and returns unified confidence."""

    def __init__(self):
        self.device = "cpu"
        if torch is not None and torch.cuda.is_available():
            self.device = "cuda"

        self.yolo_model = None
        self.effnet_model = None
        self.effnet_transform = None
        self.scene_labels = [
            label.strip().lower()
            for label in os.getenv("SCENE_CLASSES", "fire,sunlight,smoke,fog,normal").split(",")
            if label.strip()
        ]

        self.yolo_labels = {
            label.strip().lower()
            for label in os.getenv("YOLO_FIRE_CLASS_NAMES", "fire,smoke").split(",")
            if label.strip()
        }
        self.yolo_conf_threshold = float(os.getenv("YOLO_CONF_THRESHOLD", "0.25"))

        self.effnet_enabled = os.getenv("ENABLE_EFFICIENTNET", "true").lower() == "true"
        self.yolo_enabled = os.getenv("ENABLE_YOLOV8", "true").lower() == "true"

        self.model_status = {
            "yolov8": {"enabled": self.yolo_enabled, "ready": False, "error": None},
            "efficientnet": {"enabled": self.effnet_enabled, "ready": False, "error": None},
            "cnn_lstm": {"enabled": True, "ready": False, "error": None},
        }
        
        self.frame_buffer = []
        self.seq_length = 5
        self.cnn_lstm_model = None

        self._load_yolo()
        self._load_efficientnet()
        self._load_cnn_lstm()

    def _load_cnn_lstm(self):
        try:
            from models_custom.cnn_lstm import CNNLSTMModel
            if torch is None:
                self.model_status["cnn_lstm"]["error"] = "Torch not installed"
                return
                
            self.cnn_lstm_model = CNNLSTMModel(num_classes=2, hidden_size=256, num_layers=1)
            
            weights_path = "cnn_lstm_best.pth"
            if os.path.exists(weights_path):
                checkpoint = torch.load(weights_path, map_location=self.device)
                self.cnn_lstm_model.load_state_dict(checkpoint, strict=False)
            else:
                self.model_status["cnn_lstm"]["error"] = "using_random_weights"
                
            self.cnn_lstm_model.eval()
            self.cnn_lstm_model.to(self.device)
            self.model_status["cnn_lstm"]["ready"] = True
        except Exception as e:
            self.model_status["cnn_lstm"]["error"] = str(e)

    def _load_yolo(self):
        if not self.yolo_enabled:
            return
        if YOLO is None:
            self.model_status["yolov8"]["error"] = "ultralytics_not_installed"
            return

        try:
            model_path = os.getenv("YOLOV8_MODEL_PATH", "yolov8n.pt")
            self.yolo_model = YOLO(model_path)
            self.model_status["yolov8"]["ready"] = True
        except Exception as e:
            self.model_status["yolov8"]["error"] = str(e)

    def _load_efficientnet(self):
        if not self.effnet_enabled:
            return
        if torch is None or models is None or transforms is None:
            self.model_status["efficientnet"]["error"] = "torch_or_torchvision_not_installed"
            return

        try:
            weights_path = os.getenv("EFFICIENTNET_WEIGHTS_PATH", "")
            if not weights_path:
                # Fallback to pretrained backbone if custom fire weights are not provided.
                self.effnet_model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
                self.effnet_model.eval()
                self.effnet_model.to(self.device)
                self.model_status["efficientnet"]["ready"] = True
                self.model_status["efficientnet"]["error"] = "using_imagenet_fallback"
            else:
                self.effnet_model = models.efficientnet_b0(weights=None)
                in_features = self.effnet_model.classifier[1].in_features
                self.effnet_model.classifier[1] = torch.nn.Linear(in_features, len(self.scene_labels))

                checkpoint = torch.load(weights_path, map_location=self.device)
                state_dict = checkpoint.get("state_dict", checkpoint)
                self.effnet_model.load_state_dict(state_dict, strict=False)
                self.effnet_model.eval()
                self.effnet_model.to(self.device)
                self.model_status["efficientnet"]["ready"] = True

            self.effnet_transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
        except Exception as e:
            self.model_status["efficientnet"]["error"] = str(e)

    def get_status(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "models": self.model_status,
        }

    def predict(self, img_array: np.ndarray) -> Dict[str, Any]:
        # Update sequence buffer
        import cv2
        resized_frame = cv2.resize(img_array, (224, 224))
        self.frame_buffer.append(resized_frame)
        if len(self.frame_buffer) > self.seq_length:
            self.frame_buffer.pop(0)

        yolo_result = self._predict_yolo(img_array)
        effnet_result = self._predict_efficientnet(img_array)
        lstm_result = self._predict_cnn_lstm()

        model_scores = []
        if yolo_result.get("available"):
            model_scores.append(("yolov8", yolo_result.get("confidence", 0.0)))
        if effnet_result.get("available"):
            model_scores.append(("efficientnet", effnet_result.get("confidence", 0.0)))
        if lstm_result.get("available") and len(self.frame_buffer) == self.seq_length:
            model_scores.append(("cnn_lstm", lstm_result.get("confidence", 0.0)))

        if not model_scores:
            return {
                "model_used": False,
                "confidence": 0.0,
                "fire_detected": False,
                "scene_classification": "unknown",
                "regions": [],
                "details": {
                    "yolov8": yolo_result,
                    "efficientnet": effnet_result,
                    "cnn_lstm": lstm_result,
                },
            }

        yolo_conf = yolo_result.get("confidence", 0.0)
        eff_conf = effnet_result.get("confidence", 0.0)
        lstm_conf = lstm_result.get("confidence", 0.0)

        if yolo_result.get("available") and effnet_result.get("available") and lstm_result.get("available"):
            ensemble_conf = yolo_conf * 0.50 + eff_conf * 0.20 + lstm_conf * 0.30
        elif yolo_result.get("available") and effnet_result.get("available"):
            ensemble_conf = yolo_conf * 0.65 + eff_conf * 0.35
        elif yolo_result.get("available"):
            ensemble_conf = yolo_conf
        else:
            ensemble_conf = eff_conf

        ensemble_conf = round(float(max(0.0, min(99.5, ensemble_conf))), 1)
        
        predicted_fallback = "fire" if ensemble_conf >= 35 else "normal"
        if lstm_result.get("available") and lstm_conf >= 40:
            predicted_fallback = "fire"
            
        scene_class = effnet_result.get("predicted_class", predicted_fallback)

        return {
            "model_used": True,
            "confidence": ensemble_conf,
            "fire_detected": scene_class == "fire" or (scene_class == "smoke" and ensemble_conf >= 45) or (lstm_conf >= 55),
            "scene_classification": scene_class,
            "regions": yolo_result.get("regions", []),
            "details": {
                "yolov8": yolo_result,
                "efficientnet": effnet_result,
                "cnn_lstm": lstm_result,
            },
        }

    def _predict_cnn_lstm(self) -> Dict[str, Any]:
        if self.cnn_lstm_model is None or len(self.frame_buffer) < self.seq_length or torch is None:
            return {"available": False, "confidence": 0.0, "reason": "not_loaded_or_buffering"}
            
        try:
            import numpy as np
            from PIL import Image
            
            tensors = []
            for frame in self.frame_buffer:
                img = Image.fromarray(frame).convert("RGB")
                if self.effnet_transform:
                    t = self.effnet_transform(img)
                else:
                    t = torch.zeros(3, 224, 224)
                tensors.append(t)
                
            input_tensor = torch.stack(tensors).unsqueeze(0).to(self.device)  # (1, seq_length, C, H, W)
            
            with torch.no_grad():
                logits = self.cnn_lstm_model(input_tensor)
                probs = torch.softmax(logits, dim=1)[0]
                fire_prob = float(probs[1].item())
                confidence = round(fire_prob * 100, 1)
                
            return {
                "available": True,
                "confidence": confidence,
                "predicted_class": "fire" if fire_prob >= 0.5 else "normal",
            }
        except Exception as e:
            return {
                "available": False,
                "confidence": 0.0,
                "reason": str(e),
            }

    def _predict_yolo(self, img_array: np.ndarray) -> Dict[str, Any]:
        if self.yolo_model is None:
            return {"available": False, "confidence": 0.0, "regions": [], "reason": "not_loaded"}

        try:
            results = self.yolo_model.predict(
                source=img_array,
                conf=self.yolo_conf_threshold,
                verbose=False,
                device=self.device,
            )

            fire_regions: List[Dict[str, float]] = []
            confidences: List[float] = []
            h, w = img_array.shape[:2]

            for result in results:
                names = result.names
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    cls_id = int(box.cls[0].item()) if box.cls is not None else -1
                    label = str(names.get(cls_id, "unknown")).lower()
                    conf = float(box.conf[0].item()) if box.conf is not None else 0.0

                    if label not in self.yolo_labels:
                        continue

                    xyxy = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = xyxy
                    region = {
                        "x": round(max(0.0, (x1 / max(w, 1)) * 100), 2),
                        "y": round(max(0.0, (y1 / max(h, 1)) * 100), 2),
                        "width": round(max(0.0, ((x2 - x1) / max(w, 1)) * 100), 2),
                        "height": round(max(0.0, ((y2 - y1) / max(h, 1)) * 100), 2),
                        "density": round(conf * 100, 1),
                        "label": label,
                    }
                    fire_regions.append(region)
                    confidences.append(conf)

            confidence = round((max(confidences) * 100), 1) if confidences else 0.0
            return {
                "available": True,
                "confidence": confidence,
                "regions": fire_regions,
                "detections": len(fire_regions),
            }
        except Exception as e:
            return {
                "available": False,
                "confidence": 0.0,
                "regions": [],
                "reason": str(e),
            }

    def _predict_efficientnet(self, img_array: np.ndarray) -> Dict[str, Any]:
        if self.effnet_model is None or self.effnet_transform is None or torch is None:
            return {"available": False, "confidence": 0.0, "reason": "not_loaded"}

        try:
            input_tensor = self.effnet_transform(img_array).unsqueeze(0).to(self.device)
            with torch.no_grad():
                logits = self.effnet_model(input_tensor)

            if logits.shape[-1] == 2:
                probs = torch.softmax(logits, dim=1)[0]
                fire_prob = float(probs[1].item())
                confidence = round(fire_prob * 100, 1)
                mode = "binary_fire_classifier"
                predicted_class = "fire" if fire_prob >= 0.5 else "normal"
                class_scores = {
                    "normal": round((1 - fire_prob) * 100, 1),
                    "fire": confidence,
                }
            else:
                probs = torch.softmax(logits, dim=1)[0]
                if logits.shape[-1] == len(self.scene_labels):
                    top_idx = int(torch.argmax(probs).item())
                    predicted_class = self.scene_labels[top_idx]
                    top_prob = float(torch.max(probs).item())
                    confidence = round(top_prob * 100, 1)
                    mode = "multiclass_scene_classifier"
                    class_scores = {
                        label: round(float(probs[idx].item()) * 100, 1)
                        for idx, label in enumerate(self.scene_labels)
                    }
                else:
                    # Fallback heuristic for ImageNet model if custom fire weights are absent.
                    top_prob = float(torch.max(probs).item())
                    confidence = round(top_prob * 100 * 0.2, 1)
                    mode = "imagenet_fallback"
                    predicted_class = "normal"
                    class_scores = {"normal": confidence}

            return {
                "available": True,
                "confidence": confidence,
                "mode": mode,
                "predicted_class": predicted_class,
                "class_scores": class_scores,
            }
        except Exception as e:
            return {
                "available": False,
                "confidence": 0.0,
                "reason": str(e),
            }
