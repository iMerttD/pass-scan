import re
import cv2
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from app.services.ocr_engine import get_ocr_engine, OCRResult
from app.services.passport.mrz_corrector import repair_td3_mrz_lines
from app.services.passport.mrz_parser import parse_td3_mrz
from app.services.passport.mrz_detector import isolate_mrz_lines
from app.core.logger import logger

# Valid MRZ character set for post-OCR whitelist filtering
_MRZ_VALID_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<")

# Doc 9303 passport/travel-document type letters, plus the letters OCR most often
# substitutes for 'P' on a worn or low-contrast document.
_TD3_LINE1_TYPE_CHARS = set("PRBFCDIAVOT")

# Extended symbol-to-MRZ mappings for aggressive cleanup
_SYMBOL_REPLACEMENTS = {
    "«": "<", "‹": "<", "›": "<", "»": "<",
    "(": "<", ")": "<", "{": "<", "}": "<", "[": "<", "]": "<",
    " ": "<", ".": "<", ",": "<", ":": "<", ";": "<",
    "'": "<", "\"": "<", "`": "<", "~": "<",
    "—": "<", "–": "<", "-": "<", "_": "<",
    "@": "<", "#": "<", "$": "<", "%": "<",
    "!": "1", "?": "7", "¡": "1",
}


def clean_mrz_ocr_text(text: str) -> str:
    """
    Sanitize recognized line into strict MRZ character set:
    Upper case letters A-Z, digits 0-9, and '<'.
    Replaces spaces and common noise with '<' or standard chars.
    """
    text = text.upper().strip()
    # Apply extended symbol replacements
    for old, new in _SYMBOL_REPLACEMENTS.items():
        text = text.replace(old, new)
    # Retain only valid MRZ characters
    cleaned = "".join(c for c in text if c in _MRZ_VALID_CHARS)
    return cleaned


def _create_mrz_preprocessing_variants(crop_bgr: np.ndarray) -> List[Tuple[str, np.ndarray]]:
    """
    Generate 8 preprocessing variants optimized for OCR-B font recognition on MRZ strips.
    Each variant targets a different image degradation scenario.
    """
    variants: List[Tuple[str, np.ndarray]] = []

    # 0. Original (baseline)
    variants.append(("original", crop_bgr))

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

    # 1. CLAHE — Contrast Limited Adaptive Histogram Equalization
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    clahe_img = clahe.apply(gray)
    variants.append(("clahe", cv2.cvtColor(clahe_img, cv2.COLOR_GRAY2BGR)))

    # 2. Otsu binarization (global threshold, excellent for clean scans)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, otsu_bin = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    variants.append(("otsu", cv2.cvtColor(otsu_bin, cv2.COLOR_GRAY2BGR)))

    # 3. Adaptive Gaussian threshold (handles uneven illumination/shadows)
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )
    variants.append(("adaptive_gauss", cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR)))

    # 4. Inverted adaptive threshold (for dark/reversed backgrounds)
    adaptive_inv = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 8
    )
    # Re-invert to get dark-on-light for OCR
    adaptive_inv = cv2.bitwise_not(adaptive_inv)
    variants.append(("adaptive_inv", cv2.cvtColor(adaptive_inv, cv2.COLOR_GRAY2BGR)))

    # 5. Morphological opening to separate touching characters
    _, morph_bin = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    morphed = cv2.morphologyEx(morph_bin, cv2.MORPH_OPEN, open_kernel)
    variants.append(("morph_open", cv2.cvtColor(morphed, cv2.COLOR_GRAY2BGR)))

    # 6. High-contrast binary + 2x upscale (the "golden" MRZ variant)
    high_contrast = cv2.convertScaleAbs(gray, alpha=1.8, beta=-80)
    _, hc_bin = cv2.threshold(high_contrast, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    hc_upscaled = cv2.resize(hc_bin, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    variants.append(("hc_upscaled", cv2.cvtColor(hc_upscaled, cv2.COLOR_GRAY2BGR)))

    # 7. Sharpened + 1.5x upscale (for slightly blurry images)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharpened = cv2.filter2D(crop_bgr, -1, sharpen_kernel)
    sharpened_up = cv2.resize(sharpened, (0, 0), fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    variants.append(("sharpened_up", sharpened_up))

    return variants


def _ocr_single_line(engine, line_img: np.ndarray) -> List[Tuple[str, float]]:
    """
    OCR a single MRZ line image and return cleaned candidate strings with confidence.
    """
    results: List[OCRResult] = engine.extract_text_with_boxes(line_img)
    
    # Sort by x-position (left to right) and concatenate
    sorted_results = sorted(results, key=lambda r: min(pt[0] for pt in r.box))
    
    candidates: List[Tuple[str, float]] = []
    
    if sorted_results:
        # Concatenate all text fragments on this line
        combined_text = "".join(r.text for r in sorted_results)
        avg_conf = sum(r.confidence for r in sorted_results) / len(sorted_results)
        cleaned = clean_mrz_ocr_text(combined_text)
        if len(cleaned) >= 28:  # TD3 line minimum viable length
            candidates.append((cleaned, avg_conf))
        
        # Also try each fragment individually if it's long enough
        for r in sorted_results:
            cleaned_single = clean_mrz_ocr_text(r.text)
            if len(cleaned_single) >= 28:
                candidates.append((cleaned_single, r.confidence))
    
    return candidates


def _score_mrz_candidate(parsed: Dict[str, Any]) -> float:
    """
    Score a parsed MRZ candidate based on checksum validity and structural integrity.
    """
    mrz_obj = parsed["mrz"]
    checks = mrz_obj.checks
    
    score = 0.0
    # Checksum scores (weighted by reliability)
    score += 2.0 if checks.document_number_checksum else 0.0
    score += 1.5 if checks.birth_date_checksum else 0.0
    score += 1.5 if checks.expiry_date_checksum else 0.0
    score += 3.0 if checks.composite_checksum else 0.0  # Composite is most important
    
    # Structural score: line 1 should start with 'P'
    raw_lines = mrz_obj.raw_lines
    if raw_lines and len(raw_lines) >= 1 and raw_lines[0].startswith("P"):
        score += 0.5
    
    # Both lines should be exactly 44 chars
    if raw_lines and len(raw_lines) >= 2:
        if len(raw_lines[0]) == 44:
            score += 0.3
        if len(raw_lines[1]) == 44:
            score += 0.3
    
    return score


def extract_and_parse_mrz(mrz_crop: np.ndarray) -> Optional[Dict[str, Any]]:
    """
    Perform local OCR on MRZ crop using PP-OCR engine with multi-strategy preprocessing.
    Uses projection profile line isolation for per-line OCR when available.
    Selects candidates based on ICAO checksum validation.
    """
    engine = get_ocr_engine()
    
    best_result: Optional[Dict[str, Any]] = None
    highest_score = -1.0

    # Strategy A: Per-line OCR using projection-isolated lines
    mrz_lines = isolate_mrz_lines(mrz_crop)
    
    if len(mrz_lines) == 2:
        logger.info("MRZ line isolation successful — using per-line OCR strategy")
        
        # For each variant, OCR each line separately
        for variant_name, variant_img in _create_mrz_preprocessing_variants(mrz_crop):
            # Re-isolate lines from the variant (variant may have different geometry if upscaled)
            variant_lines = isolate_mrz_lines(variant_img)
            if len(variant_lines) != 2:
                # Fall back to splitting the variant at the same ratio as original
                h_orig = mrz_crop.shape[0]
                h_var = variant_img.shape[0]
                ratio = h_var / max(1, h_orig)
                mid_orig = mrz_lines[0].shape[0]
                mid_var = int(mid_orig * ratio)
                variant_lines = [
                    variant_img[0:mid_var, :],
                    variant_img[mid_var:, :]
                ]
            
            # OCR each line
            line1_candidates = _ocr_single_line(engine, variant_lines[0])
            line2_candidates = _ocr_single_line(engine, variant_lines[1])
            
            # Try all combinations of line1 x line2 candidates
            for raw_l1, conf1 in line1_candidates:
                for raw_l2, conf2 in line2_candidates:
                    result = _try_parse_mrz_pair(raw_l1, raw_l2, conf1, conf2)
                    if result:
                        parsed, score = result
                        avg_conf = (conf1 + conf2) / 2.0
                        total_score = score + (avg_conf * 0.5)
                        
                        if total_score > highest_score:
                            highest_score = total_score
                            parsed["mrz_confidence"] = avg_conf
                            parsed["mrz_strategy"] = f"per_line_{variant_name}"
                            best_result = parsed
                        
                        # Perfect score: all checksums pass
                        if parsed["mrz"].valid:
                            logger.info(f"Perfect MRZ parse via per-line OCR ({variant_name})")
                            return parsed

    # Strategy B: Full-block OCR (original approach, enhanced with more variants)
    logger.info("Running full-block MRZ OCR strategy")
    
    for variant_name, crop_img in _create_mrz_preprocessing_variants(mrz_crop):
        ocr_results: List[OCRResult] = engine.extract_text_with_boxes(crop_img)
        
        # Sort detected boxes vertically from top to bottom
        sorted_results = sorted(ocr_results, key=lambda r: min(pt[1] for pt in r.box))
        
        # Candidate MRZ lines: should be relatively long and contain '<' or typical MRZ length
        candidate_lines: List[Tuple[str, float]] = []
        for res in sorted_results:
            cleaned = clean_mrz_ocr_text(res.text)
            if len(cleaned) >= 28:  # TD3 line is 44, allow partial if joined
                candidate_lines.append((cleaned, res.confidence))

        # Look for two adjacent candidate lines representing TD3
        if len(candidate_lines) >= 2:
            for i in range(len(candidate_lines) - 1):
                raw_l1, conf1 = candidate_lines[i]
                raw_l2, conf2 = candidate_lines[i + 1]
                
                result = _try_parse_mrz_pair(raw_l1, raw_l2, conf1, conf2)
                if result:
                    parsed, score = result
                    avg_conf = (conf1 + conf2) / 2.0
                    total_score = score + (avg_conf * 0.5)
                    
                    if total_score > highest_score:
                        highest_score = total_score
                        parsed["mrz_confidence"] = avg_conf
                        parsed["mrz_strategy"] = f"full_block_{variant_name}"
                        best_result = parsed
                    
                    if parsed["mrz"].valid:
                        logger.info(f"Perfect MRZ parse via full-block OCR ({variant_name})")
                        return parsed

    if best_result:
        logger.info(f"Best MRZ candidate via {best_result.get('mrz_strategy', 'unknown')} — score: {highest_score:.2f}")
    else:
        logger.warning("No viable MRZ candidates found from any preprocessing variant")

    return best_result


def _try_parse_mrz_pair(
    raw_l1: str, raw_l2: str, conf1: float, conf2: float
) -> Optional[Tuple[Dict[str, Any], float]]:
    """
    Attempt to parse and repair a pair of MRZ line candidates.
    Returns (parsed_dict, checksum_score) or None if structurally invalid.
    """
    # Structural check for TD3 line 1. The document-type letter is commonly
    # misread by OCR, so a line that carries the '<<' name separator is accepted
    # regardless of its first character; the checksums decide the winner anyway.
    if raw_l1:
        type_ok = raw_l1[0] in _TD3_LINE1_TYPE_CHARS
        if not type_ok and "<<" not in raw_l1:
            return None
    
    try:
        rep_l1, rep_l2, corrections = repair_td3_mrz_lines(raw_l1, raw_l2)
        parsed = parse_td3_mrz(rep_l1, rep_l2)
        parsed["mrz"].error_corrections_applied = corrections
        
        score = _score_mrz_candidate(parsed)
        return parsed, score
    except Exception as e:
        logger.debug(f"MRZ parse failed for candidate: {e}")
        return None

