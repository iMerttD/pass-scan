import cv2
import numpy as np
from typing import Dict, Any, List
from app.schemas.passport import QualityData
from app.core.config import settings

def assess_image_quality(image_bgr: np.ndarray, is_document_detected: bool = True) -> QualityData:
    """
    Evaluate optical quality indicators:
    - Blur score via Laplacian variance
    - Specular glare detection via high-intensity luminance saturation
    - Resolution checks
    - Document coverage / edge visibility
    """
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    feedback: List[str] = []

    # 1. Resolution Check
    resolution_ok = (w >= settings.MIN_IMAGE_WIDTH and h >= settings.MIN_IMAGE_HEIGHT)
    if not resolution_ok:
        feedback.append(f"Image resolution ({w}x{h}) is too low for reliable OCR. Minimum recommended is {settings.MIN_IMAGE_WIDTH}x{settings.MIN_IMAGE_HEIGHT}.")

    # 2. Blur / Sharpness Check (Laplacian Variance)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = float(laplacian.var())

    # Map variance to 0.0 - 1.0 normalized score
    # Usually variance > 120 is very sharp, 60-120 moderate, < 60 blurry
    normalized_blur_score = min(1.0, max(0.0, variance / 250.0))
    is_blurry = variance < settings.BLUR_THRESHOLD_LAPLACIAN
    if is_blurry:
        feedback.append(f"Image is too blurry (sharpness score: {normalized_blur_score:.2f}). Please provide a focused photo.")

    # 3. Specular Glare Detection
    # True glare appears as washed-out pure white saturated areas (V > 250 and S < 25 in HSV)
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    s_channel = hsv[:, :, 1]
    glare_mask = (v_channel > 250) & (s_channel < 25)
    glare_pixels = np.count_nonzero(glare_mask)
    total_pixels = h * w
    glare_ratio = float(glare_pixels / total_pixels)
    glare_detected = glare_ratio > settings.GLARE_PIXEL_RATIO_THRESHOLD


    if glare_detected:
        feedback.append(f"Strong flash glare detected covering {glare_ratio*100:.1f}% of the document surface. Avoid direct reflection.")

    # 4. Overexposure / Underexposure
    mean_brightness = float(np.mean(gray))
    if mean_brightness < 40:
        feedback.append("Document image is severely underexposed (too dark).")
    elif mean_brightness > 230:
        feedback.append("Document image is severely overexposed (washed out).")

    # 5. Boundary & Coverage
    passport_fully_visible = is_document_detected
    if not passport_fully_visible:
        feedback.append("Document boundary could not be cleanly detected; ensure the entire passport identity page is in frame.")

    # Acceptable logic:
    # If blur is severe (variance < 35) or resolution is tiny (< 400px), mark unusable.
    # If mild warnings, acceptable = True but feedback is passed to the UI.
    acceptable = True
    if variance < 35.0:
        acceptable = False
    if w < 400 or h < 300:
        acceptable = False
    if glare_ratio > 0.25:
        acceptable = False

    return QualityData(
        acceptable=acceptable,
        blur_score=round(normalized_blur_score, 3),
        laplacian_variance=round(variance, 1),
        glare_detected=glare_detected,
        glare_ratio=round(glare_ratio, 3),
        resolution_ok=resolution_ok,
        dimensions=[w, h],
        passport_fully_visible=passport_fully_visible,
        actionable_feedback=feedback
    )
