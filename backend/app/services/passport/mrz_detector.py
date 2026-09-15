import cv2
import numpy as np
from typing import Optional, Tuple, List
from app.core.logger import logger

def detect_mrz_region(image_bgr: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """
    Locate the Machine Readable Zone (MRZ) independently.
    Uses morphological filtering and spatial priors (bottom 25-30% of document).
    Returns (mrz_crop_bgr, (x, y, w, h)).
    """
    h, w = image_bgr.shape[:2]

    # MRZ is physically constrained to the bottom portion of the passport page
    y_start = int(h * 0.65)
    bottom_crop = image_bgr[y_start:h, 0:w]
    crop_h, crop_w = bottom_crop.shape[:2]

    gray = cv2.cvtColor(bottom_crop, cv2.COLOR_BGR2GRAY)

    # Morphological Blackhat: reveals dark regions (letters) on light backgrounds
    kernel_rect = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel_rect)

    # Compute horizontal Scharr gradient
    grad_x = cv2.Sobel(blackhat, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
    grad_x = np.absolute(grad_x)
    (min_val, max_val) = (np.min(grad_x), np.max(grad_x))
    if max_val > min_val:
        grad_x = (255 * ((grad_x - min_val) / (max_val - min_val))).astype("uint8")
    else:
        grad_x = grad_x.astype("uint8")

    # Blur to smooth high frequency noise
    grad_x = cv2.GaussianBlur(grad_x, (3, 3), 0)

    # Close gaps between words horizontally and between lines vertically
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 19))
    thresh = cv2.morphologyEx(grad_x, cv2.MORPH_CLOSE, close_kernel)
    _, thresh = cv2.threshold(thresh, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    # Find candidate contours in the bottom region
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    best_box = None
    for c in contours:
        (bx, by, bw, bh) = cv2.boundingRect(c)
        aspect = bw / float(bh) if bh > 0 else 0
        coverage = bw / float(crop_w)

        # TD3 MRZ spans at least 50% of the document width with aspect ratio > 2.5
        if coverage > 0.50 and aspect > 2.5 and bh >= 40:
            best_box = (bx, by, bw, bh)
            break

    # If morphological candidate found, apply padding
    if best_box is not None:
        bx, by, bw, bh = best_box
        pad_x = int(bw * 0.05)
        pad_y = int(bh * 0.35)
        
        real_x = max(0, bx - pad_x)
        real_y = max(0, y_start + by - pad_y)
        real_w = min(w - real_x, bw + 2 * pad_x)
        real_h = min(h - real_y, bh + 2 * pad_y)
        
        mrz_crop = image_bgr[real_y:real_y + real_h, real_x:real_x + real_w]
        return mrz_crop, (real_x, real_y, real_w, real_h)


    # Reliable fallback: crop bottom 25% of the document
    fallback_y = int(h * 0.75)
    fallback_crop = image_bgr[fallback_y:h, 0:w]
    return fallback_crop, (0, fallback_y, w, h - fallback_y)


def isolate_mrz_lines(mrz_crop_bgr: np.ndarray) -> List[np.ndarray]:
    """
    Use horizontal projection profile analysis to isolate individual MRZ text lines.
    Returns a list of 1-2 cropped BGR images, one per MRZ line (top to bottom).
    Falls back to returning the full crop if lines cannot be isolated.
    """
    if mrz_crop_bgr is None or mrz_crop_bgr.size == 0:
        return []

    h, w = mrz_crop_bgr.shape[:2]
    if h < 20 or w < 100:
        return [mrz_crop_bgr]

    gray = cv2.cvtColor(mrz_crop_bgr, cv2.COLOR_BGR2GRAY)

    # Binarize with Otsu for clean projection analysis
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    # Compute horizontal projection profile (sum of white pixels per row)
    projection = np.sum(binary, axis=1).astype(np.float64)
    
    # Smooth projection to reduce noise
    kernel_size = max(3, h // 30)
    if kernel_size % 2 == 0:
        kernel_size += 1
    smoothed = cv2.GaussianBlur(projection.reshape(-1, 1), (1, kernel_size), 0).flatten()

    # Find threshold for text vs. gap (dynamic based on projection statistics)
    proj_max = np.max(smoothed)
    proj_mean = np.mean(smoothed)
    threshold = max(proj_mean * 0.3, proj_max * 0.15)

    # Find runs of rows above threshold (text bands)
    is_text = smoothed > threshold
    bands: List[Tuple[int, int]] = []
    in_band = False
    band_start = 0

    for i in range(len(is_text)):
        if is_text[i] and not in_band:
            band_start = i
            in_band = True
        elif not is_text[i] and in_band:
            band_height = i - band_start
            if band_height >= h * 0.08:  # Minimum band height (8% of MRZ crop)
                bands.append((band_start, i))
            in_band = False
    
    if in_band:
        band_height = len(is_text) - band_start
        if band_height >= h * 0.08:
            bands.append((band_start, len(is_text)))

    # We expect exactly 2 bands for TD3 MRZ
    if len(bands) == 2:
        line_crops = []
        for (y1, y2) in bands:
            # Add small vertical padding
            pad = max(2, int((y2 - y1) * 0.15))
            cy1 = max(0, y1 - pad)
            cy2 = min(h, y2 + pad)
            line_crop = mrz_crop_bgr[cy1:cy2, 0:w]
            if line_crop.size > 0:
                line_crops.append(line_crop)
        if len(line_crops) == 2:
            logger.debug(f"Projection profile isolated 2 MRZ lines: heights {[c.shape[0] for c in line_crops]}")
            return line_crops

    # If we found more than 2, try merging close bands
    if len(bands) > 2:
        merged: List[Tuple[int, int]] = [bands[0]]
        for i in range(1, len(bands)):
            prev_end = merged[-1][1]
            curr_start = bands[i][0]
            gap = curr_start - prev_end
            # If gap is very small relative to band height, merge
            avg_band_h = np.mean([b[1] - b[0] for b in bands])
            if gap < avg_band_h * 0.4:
                merged[-1] = (merged[-1][0], bands[i][1])
            else:
                merged.append(bands[i])
        
        if len(merged) == 2:
            line_crops = []
            for (y1, y2) in merged:
                pad = max(2, int((y2 - y1) * 0.15))
                cy1 = max(0, y1 - pad)
                cy2 = min(h, y2 + pad)
                line_crop = mrz_crop_bgr[cy1:cy2, 0:w]
                if line_crop.size > 0:
                    line_crops.append(line_crop)
            if len(line_crops) == 2:
                logger.debug(f"Merged projection bands into 2 MRZ lines")
                return line_crops

    # Fallback: split at midpoint if we have a single large band or couldn't parse
    if len(bands) == 1:
        mid = h // 2
        # Look for the gap closest to midpoint in the smoothed projection
        search_start = max(0, mid - h // 6)
        search_end = min(h, mid + h // 6)
        if search_end > search_start:
            search_region = smoothed[search_start:search_end]
            gap_pos = search_start + np.argmin(search_region)
            pad = max(2, h // 20)
            line1 = mrz_crop_bgr[0:gap_pos + pad, 0:w]
            line2 = mrz_crop_bgr[max(0, gap_pos - pad):h, 0:w]
            if line1.size > 0 and line2.size > 0:
                return [line1, line2]

    # Ultimate fallback: return full crop
    return [mrz_crop_bgr]


def score_mrz_presence(image_bgr: np.ndarray) -> float:
    """
    Score how strongly a region looks like a Machine Readable Zone.

    The decisive cue is that an MRZ is monospaced OCR-B: many same-height glyphs
    at a constant pitch spanning the full width. Ordinary document headings have
    word gaps and uneven glyph widths, so they score low even when they are just
    as wide and dark.

    Returns 0.0 (nothing MRZ-like) .. 1.0 (textbook MRZ).
    """
    if image_bgr is None or image_bgr.size == 0:
        return 0.0

    h, w = image_bgr.shape[:2]
    if h < 20 or w < 100:
        return 0.0

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
    _, binary = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    _, _, stats, centroids = cv2.connectedComponentsWithStats(binary, 8)
    glyphs = [
        (stat, centroid)
        for stat, centroid in zip(stats[1:], centroids[1:])
        if 0.04 * h < stat[cv2.CC_STAT_HEIGHT] < 0.45 * h and stat[cv2.CC_STAT_AREA] > 8
    ]
    if len(glyphs) < 20:
        return 0.0

    heights = np.array([stat[cv2.CC_STAT_HEIGHT] for stat, _ in glyphs], dtype=float)
    y_centers = np.array([centroid[1] for _, centroid in glyphs], dtype=float)

    # Group glyphs into text lines by vertical position.
    sorted_y = np.sort(y_centers)
    lines: List[List[float]] = [[float(sorted_y[0])]]
    for y in sorted_y[1:]:
        if y - lines[-1][-1] > heights.mean() * 0.8:
            lines.append([])
        lines[-1].append(float(y))
    lines = [line for line in lines if len(line) >= 15]
    if not lines:
        return 0.0

    best_line_score = 0.0
    for line in lines:
        low, high = min(line), max(line)
        xs = sorted(
            float(centroid[0]) for _, centroid in glyphs if low - 1 <= centroid[1] <= high + 1
        )
        if len(xs) < 20:
            continue
        gaps = np.diff(np.array(xs))
        gaps = gaps[gaps > 0]
        if len(gaps) < 15:
            continue
        # Constant character pitch is what identifies OCR-B monospace.
        pitch_cv = float(gaps.std() / max(1e-6, gaps.mean()))
        pitch_regularity = max(0.0, 1.0 - pitch_cv / 0.6)
        spread = (xs[-1] - xs[0]) / float(w)
        glyph_count = min(1.0, len(xs) / 40.0)
        best_line_score = max(
            best_line_score,
            0.35 * pitch_regularity + 0.35 * glyph_count + 0.30 * spread,
        )

    # A TD3 MRZ has two such lines; a single one still counts, just less.
    line_bonus = 0.7 + 0.3 * min(1.0, len(lines) / 2.0)
    return float(min(1.0, max(0.0, best_line_score * line_bonus)))


def check_mrz_presence_in_region(image_bgr: np.ndarray) -> bool:
    """Boolean view of :func:`score_mrz_presence` for orientation sanity checks."""
    return score_mrz_presence(image_bgr) >= 0.40


def detect_mrz_candidates(image_bgr: np.ndarray) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
    """
    Produce ordered MRZ region candidates, best guess first.

    The morphological detector assumes a cleanly cropped identity page. When the
    document boundary was not detected the page may sit anywhere in the frame,
    so wider fallback bands are offered as well and the OCR stage picks whichever
    one actually yields a checksum-valid MRZ.
    """
    h, w = image_bgr.shape[:2]
    candidates: List[Tuple[np.ndarray, Tuple[int, int, int, int]]] = []
    seen: set = set()

    def add(y1: int, y2: int, x1: int = 0, x2: Optional[int] = None) -> None:
        x2 = w if x2 is None else x2
        y1, y2 = max(0, y1), min(h, y2)
        x1, x2 = max(0, x1), min(w, x2)
        if y2 - y1 < 20 or x2 - x1 < 100:
            return
        key = (x1, y1, x2, y2)
        if key in seen:
            return
        seen.add(key)
        candidates.append((image_bgr[y1:y2, x1:x2], (x1, y1, x2 - x1, y2 - y1)))

    # 1. Morphological detector (tight crop around the detected band)
    crop, (bx, by, bw, bh) = detect_mrz_region(image_bgr)
    if crop is not None and crop.size > 0:
        seen.add((bx, by, bx + bw, by + bh))
        candidates.append((crop, (bx, by, bw, bh)))

    # 2. Fixed bottom bands — robust when morphology latches onto the wrong contour
    add(int(h * 0.75), h)
    add(int(h * 0.62), h)
    # 3. Full lower half — for uncropped photos where the page sits high in frame
    add(int(h * 0.45), h)

    return candidates
