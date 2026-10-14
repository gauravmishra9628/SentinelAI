"""
SentinelAI detector service.

Supports:
- Real YOLO when a compatible model/dependencies are available.
- Safe DEMO fallback when no model is present.
- OFFLINE state when a model exists but fails to load.

No fake YOLO result is generated when the real model is unavailable.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

_DEFAULT_CONFIDENCE = float(os.getenv("SENTINEL_YOLO_CONFIDENCE", "0.40"))
_MODEL_PATH = os.getenv("SENTINEL_YOLO_MODEL", "").strip()

_model: Any = None
_model_error: str | None = None
_model_loaded = False
_model_attempted = False
_device = "cpu"

SUPPORTED_EVENT_TYPES = (
    "NONE",
    "WRONG_WAY",
    "COLLISION",
    "PEDESTRIAN_RISK",
    "OVERSPEED",
    "DANGEROUS_DRIVING",
    "CONGESTION",
    "ROAD_OBSTRUCTION",
)

_COCO_CLASSES = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]


def _resolve_model_path() -> Path | None:
    """Find an explicitly configured model or common local model names."""
    if _MODEL_PATH:
        path = Path(_MODEL_PATH)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return path

    candidates = (
        BACKEND_DIR / "best.pt",
        BACKEND_DIR / "model.pt",
        BACKEND_DIR / "yolov8n.pt",
        BACKEND_DIR / "yolov8s.pt",
    )

    for path in candidates:
        if path.exists():
            return path

    return None


def load_model() -> Any:
    """
    Load YOLO once if a model and ultralytics are available.

    Returns the model object or None.
    """
    global _model
    global _model_error
    global _model_loaded
    global _model_attempted
    global _device

    if _model_attempted:
        return _model

    _model_attempted = True

    model_path = _resolve_model_path()

    if model_path is None:
        _model = None
        _model_loaded = False
        _model_error = "YOLO model file not found"
        return None

    try:
        from ultralytics import YOLO  # type: ignore

        _model = YOLO(str(model_path))

        # Prefer CPU unless explicitly configured otherwise.
        _device = os.getenv("SENTINEL_YOLO_DEVICE", "cpu")

        _model_loaded = True
        _model_error = None
        return _model

    except Exception as exc:
        _model = None
        _model_loaded = False
        _model_error = str(exc)
        return None


def get_ai_mode() -> str:
    """Return YOLO, OFFLINE, or DEMO."""
    if _model_loaded and _model is not None:
        return "YOLO"

    if _model_attempted and _resolve_model_path() is not None:
        return "OFFLINE"

    return "DEMO"


def is_demo_mode() -> bool:
    return get_ai_mode() == "DEMO"


def is_ai_active() -> bool:
    return get_ai_mode() == "YOLO"


def is_ai_offline() -> bool:
    return get_ai_mode() == "OFFLINE"


def get_model_classes() -> list[str]:
    if _model is not None:
        try:
            names = getattr(_model, "names", None)
            if isinstance(names, dict):
                return [str(names[k]) for k in sorted(names)]
            if isinstance(names, (list, tuple)):
                return [str(x) for x in names]
        except Exception:
            pass

    return list(_COCO_CLASSES)


def get_inference_device() -> str:
    return _device


def get_confidence_threshold() -> float:
    return _DEFAULT_CONFIDENCE


def get_model_info() -> dict[str, Any]:
    mode = get_ai_mode()
    model_path = _resolve_model_path()

    return {
        "ai_mode": mode,
        "mode": mode,
        "loaded": _model_loaded,
        "model_loaded": _model_loaded,
        "model_path": str(model_path) if model_path else None,
        "model_name": model_path.name if model_path else None,
        "device": _device,
        "confidence_threshold": _DEFAULT_CONFIDENCE,
        "classes": get_model_classes(),
        "class_count": len(get_model_classes()),
        "status_message": (
            "YOLO model loaded"
            if mode == "YOLO"
            else (
                f"Model load failed: {_model_error}"
                if mode == "OFFLINE"
                else "YOLO model not found; running in DEMO MODE"
            )
        ),
    }


def get_model_capabilities() -> dict[str, Any]:
    """Describe what the currently available detector can actually provide."""
    mode = get_ai_mode()

    return {
        "ai_mode": mode,
        "model_loaded": _model_loaded,
        "real_detection_available": mode == "YOLO",
        "demo_mode": mode == "DEMO",
        "supported_classes": get_model_classes(),
        "supported_event_types": list(SUPPORTED_EVENT_TYPES),
        "capabilities": {
            "vehicle_detection": mode == "YOLO",
            "person_detection": mode == "YOLO",
            "traffic_object_detection": mode == "YOLO",
            "wrong_way_detection": False,
            "collision_detection": False,
            "helmet_detection": False,
            "speed_estimation": False,
        },
        "limitations": [
            "Wrong-way, collision, helmet and speed estimation require domain-specific logic or additional sensors/models."
        ],
    }


def _decode_image(image_data: str | bytes) -> bytes:
    """Decode a base64 string or return raw bytes unchanged."""
    if not image_data:
        return b""

    if isinstance(image_data, bytes):
        return image_data

    value = image_data

    if "," in value and value.lower().startswith("data:"):
        value = value.split(",", 1)[1]

    try:
        return base64.b64decode(value, validate=False)
    except Exception:
        return b""


def _run_yolo(image_bytes: bytes) -> list[dict[str, Any]]:
    """Run YOLO and normalize results into SentinelAI detection dictionaries."""
    if not image_bytes or _model is None:
        return []

    try:
        import numpy as np  # type: ignore
        from PIL import Image  # type: ignore
        import io

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        frame = np.asarray(image)

        results = _model.predict(
            source=frame,
            conf=_DEFAULT_CONFIDENCE,
            device=_device,
            verbose=False,
        )

        detections: list[dict[str, Any]] = []

        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            names = getattr(result, "names", {}) or {}

            for box in boxes:
                try:
                    cls_id = int(box.cls[0].item())
                    confidence = float(box.conf[0].item())
                    xyxy = [float(x) for x in box.xyxy[0].tolist()]
                except Exception:
                    continue

                if isinstance(names, dict):
                    class_name = str(names.get(cls_id, cls_id))
                else:
                    class_name = str(cls_id)

                detections.append(
                    {
                        "class": class_name,
                        "confidence": round(confidence, 4),
                        "bbox": xyxy,
                    }
                )

        return detections

    except Exception as exc:
        print(f"[SentinelAI] Detection inference error: {exc}")
        return []


def detect_frame(image_data: str | bytes, image_format: str = "jpeg") -> dict[str, Any]:
    """
    Detect objects in a base64-encoded image or raw image bytes.

    In DEMO mode this intentionally returns no fabricated detections.
    """
    mode = get_ai_mode()

    image_bytes = _decode_image(image_data)

    if mode == "YOLO":
        detections = _run_yolo(image_bytes)
    else:
        detections = []

    return {
        "success": True,
        "detections": detections,
        "alerts": [],
        "model": "YOLO" if mode == "YOLO" else "MOCK",
        "ai_mode": mode,
        "demo_mode": mode == "DEMO",
        "image_format": image_format,
    }


def enrich_detections(
    detections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add normalized category metadata without changing original detection data."""
    enriched: list[dict[str, Any]] = []

    vehicle_classes = {
        "car",
        "truck",
        "bus",
        "motorcycle",
        "bicycle",
    }

    for detection in detections or []:
        item = dict(detection)
        class_name = str(item.get("class", "")).lower()

        if class_name in vehicle_classes:
            category = "vehicle"
        elif class_name == "person":
            category = "pedestrian"
        else:
            category = "object"

        item["category"] = category
        enriched.append(item)

    return enriched


def classify_event(
    detections: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Conservative event classifier.

    It does not claim accident/wrong-way detection from a single frame.
    """
    detections = detections or []

    if not detections:
        return {
            "event_type": "NONE",
            "factors": [],
        }

    vehicle_count = sum(
        1
        for d in detections
        if str(d.get("class", "")).lower()
        in {"car", "truck", "bus", "motorcycle", "bicycle"}
    )

    pedestrian_count = sum(
        1
        for d in detections
        if str(d.get("class", "")).lower() == "person"
    )

    factors: list[str] = []

    if vehicle_count >= 5:
        factors.append("multiple vehicles detected")

    if pedestrian_count > 0:
        factors.append("pedestrian detected")

    return {
        "event_type": "NONE",
        "factors": factors,
    }
