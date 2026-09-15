import os
import cv2
import base64
import numpy as np
from typing import Optional, Tuple, List
from app.schemas.passport import PortraitInfo
from app.core.logger import logger

# Cache the YuNet model path
_YUNET_MODEL_PATH: Optional[str] = None


def _find_yunet_model() -> Optional[str]:
    """
    Locate the YuNet face detection ONNX model.
    Checks multiple possible locations.
    """
    global _YUNET_MODEL_PATH
    if _YUNET_MODEL_PATH is not None:
        return _YUNET_MODEL_PATH if _YUNET_MODEL_PATH != "" else None

    # Check common locations
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet_2023mar.onnx"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "models", "face_detection_yunet_2023mar.onnx"),
        os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet.onnx"),
    ]

    # Also check if opencv has a bundled model
    try:
        opencv_model_dir = os.path.join(os.path.dirname(cv2.__file__), "data")
        possible_paths.append(os.path.join(opencv_model_dir, "face_detection_yunet_2023mar.onnx"))
    except Exception:
        pass

    for p in possible_paths:
        if os.path.exists(p):
            _YUNET_MODEL_PATH = p
            logger.info(f"YuNet model found at: {p}")
            return p

    _YUNET_MODEL_PATH = ""  # Mark as searched but not found
    return None


def encode_image_to_base64_url(image_bgr: np.ndarray, quality: int = 95) -> str:
    """Encode OpenCV BGR image into base64 data URL."""
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    success, buffer = cv2.imencode(".jpg", image_bgr, encode_params)
    if not success:
        return ""
    b64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"


def _detect_faces_yunet(
    gray: np.ndarray, w: int, h: int, search_h: int
) -> Optional[List[Tuple[int, int, int, int, float]]]:
    """
    Detect faces using OpenCV's YuNet DNN detector.
    Returns list of (x, y, w, h, confidence) tuples or None if model unavailable.
    """
    model_path = _find_yunet_model()
    if model_path is None:
        return None

    try:
        detector = cv2.FaceDetectorYN.create(
            model=model_path,
            config="",
            input_size=(w, search_h),
            score_threshold=0.7,
            nms_threshold=0.3,
            top_k=10
        )
        detector.setInputSize((w, search_h))

        # YuNet expects BGR 3-channel input
        if len(gray.shape) == 2:
            input_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        else:
            input_img = gray

        _, faces = detector.detect(input_img)

        if faces is None or len(faces) == 0:
            return None

        results = []
        for face in faces:
            fx, fy, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
            conf = float(face[-1])
            # Filter by minimum face size
            if fw >= int(w * 0.08) and fh >= int(search_h * 0.10):
                results.append((fx, fy, fw, fh, conf))

        return results if results else None

    except Exception as e:
        logger.warning(f"YuNet face detection failed: {e}")
        return None


def _detect_faces_haar(
    gray: np.ndarray, w: int, h: int, search_h: int
) -> Optional[List[Tuple[int, int, int, int, float]]]:
    """
    Fallback face detection using Haar cascade.
    Returns list of (x, y, w, h, confidence) tuples.
    """
    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    if not os.path.exists(cascade_path):
        logger.warning("Haar cascade file not found")
        return None

    face_cascade = cv2.CascadeClassifier(cascade_path)
    equalized = cv2.equalizeHist(gray)

    faces = face_cascade.detectMultiScale(
        equalized,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(int(w * 0.10), int(search_h * 0.15)),
        maxSize=(int(w * 0.50), int(search_h * 0.65))
    )

    if len(faces) == 0:
        # More sensitive pass
        faces = face_cascade.detectMultiScale(
            equalized,
            scaleFactor=1.05,
            minNeighbors=3,
            minSize=(int(w * 0.08), int(search_h * 0.12))
        )

    if len(faces) == 0:
        return None

    # Haar doesn't provide confidence, assign based on detection parameters
    return [(fx, fy, fw, fh, 0.85) for (fx, fy, fw, fh) in faces]


def extract_primary_portrait(image_bgr: np.ndarray) -> Optional[PortraitInfo]:
    """
    Detect and extract the PRIMARY passport holder portrait with layout reasoning.
    Uses YuNet DNN as primary detector, Haar cascade as fallback.
    Filters out holograms, ghost thumbnails, and background watermarks.
    """
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # Restrict search area to upper 75% of document (above MRZ)
    search_h = int(h * 0.75)
    search_gray = gray[0:search_h, 0:w]
    search_bgr = image_bgr[0:search_h, 0:w]

    # Try YuNet first (better accuracy), then fall back to Haar
    detected_faces = _detect_faces_yunet(search_bgr, w, h, search_h)
    detection_method = "yunet"

    if detected_faces is None:
        detected_faces = _detect_faces_haar(search_gray, w, h, search_h)
        detection_method = "haar"

    if detected_faces is None:
        logger.info("No faces detected — using ICAO layout fallback for portrait")
        # Fallback to standard ICAO Doc 9303 ID-3 portrait photo layout zone
        photo_x = int(w * 0.055)
        photo_y = int(h * 0.17)
        photo_w = int(w * 0.24)
        photo_h = int(h * 0.43)

        portrait_crop = image_bgr[photo_y:photo_y + photo_h, photo_x:photo_x + photo_w]
        if portrait_crop.size > 0:
            portrait_b64 = encode_image_to_base64_url(portrait_crop)
            return PortraitInfo(
                url=portrait_b64,
                confidence=0.82,
                bbox=[photo_x, photo_y, photo_w, photo_h]
            )
        return None

    logger.info(f"Face detection via {detection_method}: found {len(detected_faces)} candidate(s)")

    # Score each detected face candidate
    max_area = max(fw * fh for (_, _, fw, fh, _) in detected_faces)
    candidates: List[Tuple[float, Tuple[int, int, int, int]]] = []

    for (fx, fy, fw, fh, det_conf) in detected_faces:
        area = fw * fh
        # Reject miniature ghost faces (< 35% of largest face area)
        if area < 0.35 * max_area and len(detected_faces) > 1:
            continue

        # Size score
        size_score = area / float(max_area)

        # Position bonus: primary portrait is typically left-aligned on ICAO passports
        rel_x = fx / float(w)
        pos_bonus = 0.2 if (rel_x < 0.38) else (0.1 if rel_x > 0.60 else 0.0)

        # Aspect ratio bonus: passport photos have ~3:4 or ~2:3 aspect ratio
        aspect = fw / float(fh) if fh > 0 else 0
        aspect_bonus = 0.1 if 0.6 <= aspect <= 0.85 else 0.0

        # Detection confidence bonus
        conf_bonus = det_conf * 0.15

        score = size_score + pos_bonus + aspect_bonus + conf_bonus
        candidates.append((score, (fx, fy, fw, fh)))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, (fx, fy, fw, fh) = candidates[0]

    # Calculate portrait crop with natural passport photo margins
    margin_top = int(fh * 0.28)
    margin_bottom = int(fh * 0.38)
    margin_side = int(fw * 0.22)

    crop_x1 = max(0, fx - margin_side)
    crop_y1 = max(0, fy - margin_top)
    crop_x2 = min(w, fx + fw + margin_side)
    crop_y2 = min(h, fy + fh + margin_bottom)

    portrait_crop = image_bgr[crop_y1:crop_y2, crop_x1:crop_x2]
    if portrait_crop.size == 0:
        return None

    portrait_b64 = encode_image_to_base64_url(portrait_crop)
    confidence = round(min(0.99, 0.85 + (best_score * 0.14)), 2)

    return PortraitInfo(
        url=portrait_b64,
        confidence=confidence,
        bbox=[crop_x1, crop_y1, crop_x2 - crop_x1, crop_y2 - crop_y1]
    )

