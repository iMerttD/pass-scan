import cv2
import numpy as np
from PIL import Image, ExifTags
from typing import Tuple, List, Optional, Dict
from app.core.logger import logger
from app.services.passport.mrz_detector import score_mrz_presence

def correct_exif_orientation(image_pil: Image.Image) -> Image.Image:
    """
    Correct image orientation according to EXIF metadata tag.
    """
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        
        exif = image_pil._getexif()
        if exif is not None and orientation in exif:
            val = exif[orientation]
            if val == 3:
                return image_pil.rotate(180, expand=True)
            elif val == 6:
                return image_pil.rotate(270, expand=True)
            elif val == 8:
                return image_pil.rotate(90, expand=True)
    except Exception:
        pass
    return image_pil

def order_quad_points(pts: np.ndarray) -> np.ndarray:
    """
    Order coordinates as top-left, top-right, bottom-right, bottom-left.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # Top-left
    rect[2] = pts[np.argmax(s)]  # Bottom-right

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # Top-right
    rect[3] = pts[np.argmax(diff)]  # Bottom-left
    return rect

def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Perform perspective transformation based on 4 corner points.
    """
    rect = order_quad_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    # Standard passport ID-3 ratio is ~1.42 (125mm x 88mm)
    if max_width < 400 or max_height < 300:
        return image  # Fallback if degenerate

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_width, max_height))
    return warped

def detect_passport_contour(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Find the prominent 4-point passport boundary contour.
    Returns ordered 4 points or None if no confident boundary found.
    """
    h, w = image.shape[:2]
    total_area = h * w
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)
    # Dilate slightly to connect broken lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    for c in contours:
        area = cv2.contourArea(c)
        # Passport should take at least 35% of the total image area
        if area < 0.35 * total_area:
            continue
        
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            pts = approx.reshape(4, 2)
            # Check aspect ratio
            rect = order_quad_points(pts)
            width = np.linalg.norm(rect[0] - rect[1])
            height = np.linalg.norm(rect[0] - rect[3])
            if height > 0:
                aspect = max(width / height, height / width)
                # Passport aspect ratio is typically between 1.2 and 1.6
                if 1.15 <= aspect <= 1.8:
                    return pts
    return None

def _bottom_band_mrz_score(image: np.ndarray) -> float:
    """Score the bottom 30% of an image for MRZ-like content."""
    h, w = image.shape[:2]
    if h < 40 or w < 120:
        return 0.0
    return score_mrz_presence(image[int(h * 0.70):h, 0:w])


def normalize_document_orientation(image: np.ndarray) -> np.ndarray:
    """
    Rotate the document so the identity page is upright with the MRZ at the bottom.

    All four 90-degree orientations are evaluated and the one with the strongest
    MRZ evidence in its bottom band wins. A single fixed rotation cannot recover
    a phone photo taken 90 degrees off, which is why every candidate is scored.
    """
    candidates = [
        ("as_is", image),
        ("rot90_cw", cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)),
        ("rot180", cv2.rotate(image, cv2.ROTATE_180)),
        ("rot90_ccw", cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)),
    ]

    scored = []
    for name, candidate in candidates:
        ch, cw = candidate.shape[:2]
        score = _bottom_band_mrz_score(candidate)
        # Passport identity pages are landscape; a portrait candidate needs
        # clearly stronger MRZ evidence before it is preferred.
        if cw <= ch:
            score *= 0.75
        scored.append((score, name, candidate))

    best_score, best_name, best_image = max(scored, key=lambda item: item[0])

    if best_score <= 0.0:
        # No MRZ evidence in any orientation (heavy damage, crop, or glare):
        # fall back to the landscape assumption rather than guessing wildly.
        h, w = image.shape[:2]
        logger.debug("No MRZ evidence in any orientation — using landscape fallback")
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE) if h > w else image

    logger.info(f"Orientation normalized via MRZ evidence: {best_name} (score {best_score:.2f})")
    return best_image


def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Slight deskewing using Hough lines or minAreaRect on high-frequency edges.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)

    if lines is not None:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Focus on nearly horizontal lines (-20 to +20 degrees)
            if -20 < angle < 20:
                angles.append(angle)
        if len(angles) >= 5:
            median_angle = float(np.median(angles))
            if abs(median_angle) > 0.5:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return image

def normalize_resolution(image: np.ndarray, target_width: int = 1420) -> np.ndarray:
    """
    Resize image proportionally to standard high-resolution width for optimal OCR.
    Standard passport identity page width ~1420px provides ~300 DPI clarity.
    """
    h, w = image.shape[:2]
    if w == target_width:
        return image
    scale = target_width / float(w)
    target_height = int(h * scale)
    interpolation = cv2.INTER_CUBIC if scale > 1.0 else cv2.INTER_AREA
    return cv2.resize(image, (target_width, target_height), interpolation=interpolation)

def create_preprocessing_variants(image_bgr: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Generate multiple OCR-safe variants for robust fallback recognition:
    - 'original': Normalized BGR copy
    - 'grayscale': Grayscale image
    - 'clahe': Contrast Limited Adaptive Histogram Equalization
    - 'adaptive_thresh': Adaptive binarization for faint text
    - 'sharpened': High-pass edge-sharpened copy
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    clahe_img = clahe.apply(gray)

    # Adaptive Thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )

    # Sharpened
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharpened = cv2.filter2D(image_bgr, -1, kernel)

    return {
        "original": image_bgr,
        "grayscale": cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR),
        "clahe": cv2.cvtColor(clahe_img, cv2.COLOR_GRAY2BGR),
        "adaptive_thresh": cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR),
        "sharpened": sharpened
    }
