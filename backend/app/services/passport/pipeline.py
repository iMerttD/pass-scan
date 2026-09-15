import io
import time
import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image
from typing import Tuple, Optional, Dict, Any

try:
    # Registers the HEIF/HEIC decoder with Pillow. iPhones shoot HEIC by
    # default, so without this every such upload fails at load time.
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover - dependency is pinned in requirements.txt
    pillow_heif = None

from app.core.config import settings
from app.core.logger import logger
from app.core.security import generate_safe_session_id
from app.schemas.passport import (
    PassportAnalysisResponse, DocumentInfo, HolderInfo, PassportData,
    MRZData, MRZChecks, QualityData, ConfidenceScores, PortraitInfo
)
from app.services.passport.preprocessing import (
    correct_exif_orientation,
    detect_passport_contour,
    four_point_transform,
    normalize_document_orientation,
    deskew_image,
    normalize_resolution
)
from app.services.passport.quality import assess_image_quality
from app.services.passport.mrz_detector import detect_mrz_candidates, score_mrz_presence
from app.services.passport.mrz_ocr import extract_and_parse_mrz
from app.services.passport.visual_ocr import extract_visual_zone_fields
from app.services.passport.portrait_extractor import extract_primary_portrait, encode_image_to_base64_url
from app.services.passport.cross_validation import cross_validate_all_fields
from app.services.passport.confidence import compute_overall_confidence

def load_file_to_bgr_image(file_bytes: bytes, mime_type: str) -> np.ndarray:
    """
    Safely load raw bytes into an OpenCV BGR numpy array.
    Supports JPG, PNG, WEBP, and PDF (renders first page of PDF).
    """
    if mime_type == "application/pdf":
        pdf = pdfium.PdfDocument(file_bytes)
        if len(pdf) == 0:
            raise ValueError("PDF file has no pages.")
        page = pdf[0]
        # Render at 300 DPI equivalent (scale=4.16 for 72pt default)
        pil_image = page.render(scale=3.0).to_pil()
        image_np = np.array(pil_image)
        # Convert RGB/RGBA to BGR
        if len(image_np.shape) == 3 and image_np.shape[2] == 4:
            return cv2.cvtColor(image_np, cv2.COLOR_RGBA2BGR)
        elif len(image_np.shape) == 3 and image_np.shape[2] == 3:
            return cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        else:
            return cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)

    if mime_type in ("image/heic", "image/heif") and pillow_heif is None:
        raise ValueError(
            "HEIC/HEIF support is unavailable on this server. "
            "Please upload the document as JPG, PNG, WEBP or PDF."
        )

    # Standard image formats via PIL to handle EXIF
    pil_image = Image.open(io.BytesIO(file_bytes))
    pil_image = correct_exif_orientation(pil_image)
    image_np = np.array(pil_image)

    if len(image_np.shape) == 3 and image_np.shape[2] == 4:
        return cv2.cvtColor(image_np, cv2.COLOR_RGBA2BGR)
    elif len(image_np.shape) == 3 and image_np.shape[2] == 3:
        return cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    else:
        return cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)

def create_annotated_preview(
    image_bgr: np.ndarray,
    portrait_bbox: Optional[list[int]],
    mrz_bbox: Optional[Tuple[int, int, int, int]],
    visual_fields: Dict[str, Any]
) -> str:
    """
    Draw clean document annotations (portrait box in blue, MRZ in green, visual fields in purple)
    and return as base64 image data URL.
    """
    annotated = image_bgr.copy()
    h, w = annotated.shape[:2]
    font_scale = max(0.45, w / 2200.0)
    thickness = max(1, int(w / 700))

    # 1. Draw MRZ region (Green)
    if mrz_bbox:
        mx, my, mw, mh = mrz_bbox
        cv2.rectangle(annotated, (mx, my), (mx + mw, my + mh), (46, 204, 113), thickness + 1)
        cv2.putText(annotated, "ICAO MRZ ZONE", (mx + 10, my - 10), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (46, 204, 113), thickness)

    # 2. Draw Portrait (Blue)
    if portrait_bbox:
        px, py, pw, ph = portrait_bbox
        cv2.rectangle(annotated, (px, py), (px + pw, py + ph), (52, 152, 219), thickness + 1)
        cv2.putText(annotated, "PRIMARY PORTRAIT", (px + 5, py - 8), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (52, 152, 219), thickness)

    # 3. Draw Visual fields (Purple)
    for field_name, field_info in visual_fields.items():
        box = field_info.get("box")
        if box:
            pts = np.array(box, np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated, [pts], True, (155, 89, 182), thickness)

    return encode_image_to_base64_url(annotated, quality=85)

def _passing_checks(result: Optional[Dict[str, Any]]) -> int:
    """Count how many ICAO check digits a parsed MRZ candidate satisfies."""
    if result is None:
        return -1
    checks = result["mrz"].checks
    return sum(
        1 for value in (
            checks.document_number_checksum,
            checks.birth_date_checksum,
            checks.expiry_date_checksum,
            checks.composite_checksum,
        ) if value
    )


def resolve_mrz_with_orientation(
    working_image: np.ndarray
) -> Tuple[np.ndarray, Optional[Dict[str, Any]], Optional[Tuple[int, int, int, int]]]:
    """
    Locate and read the MRZ, letting the ICAO checksums settle the one thing image
    heuristics cannot decide reliably: whether the page is upside down.

    A passport heading band looks a lot like an MRZ band to any morphological
    detector, so the 180-degree flip is only accepted when it produces an MRZ that
    actually validates. Returns the (possibly flipped) image alongside the result.
    """
    best: Tuple[np.ndarray, Optional[Dict[str, Any]], Optional[Tuple[int, int, int, int]]] = (
        working_image, None, None
    )

    for flipped in (False, True):
        # Reading the MRZ is the expensive part of the pipeline, so only pay for
        # the flipped pass when the upright pass left real doubt.
        if flipped and _passing_checks(best[1]) >= 3:
            break

        image = cv2.rotate(working_image, cv2.ROTATE_180) if flipped else working_image

        candidates = detect_mrz_candidates(image)
        # Cheap morphological pre-scoring skips regions with no MRZ-like text at all.
        scored = [(score_mrz_presence(crop), crop, bbox) for crop, bbox in candidates]
        viable = [c for c in scored if c[0] >= 0.15] or scored[:1]
        viable.sort(key=lambda c: c[0], reverse=True)

        for _, candidate_crop, candidate_bbox in viable:
            result = extract_and_parse_mrz(candidate_crop)
            if result is None:
                continue
            if result["mrz"].valid:
                if flipped:
                    logger.info("MRZ validated only after 180 degree flip — page was upside down")
                return image, result, candidate_bbox
            # Keep the most credible partial reading as a fallback.
            if _passing_checks(result) > _passing_checks(best[1]):
                best = (image, result, candidate_bbox)

    return best


def process_passport_image(
    file_bytes: bytes,
    mime_type: str,
    session_id: Optional[str] = None
) -> PassportAnalysisResponse:
    """
    Full deterministic passport analysis pipeline.
    """
    start_time = time.time()
    if session_id is None:
        session_id = generate_safe_session_id()

    logger.info(f"Starting passport processing pipeline. Session: {session_id}")

    # 1. Load original image
    original_bgr = load_file_to_bgr_image(file_bytes, mime_type)

    # 2. Document boundary detection & perspective correction
    contour_pts = detect_passport_contour(original_bgr)
    is_doc_detected = contour_pts is not None

    if is_doc_detected:
        working_image = four_point_transform(original_bgr, contour_pts)
    else:
        working_image = original_bgr.copy()

    # Orientation & Deskewing
    working_image = normalize_document_orientation(working_image)
    working_image = deskew_image(working_image)
    working_image = normalize_resolution(working_image, target_width=1420)

    # 3. Image Quality Gate
    quality = assess_image_quality(working_image, is_document_detected=is_doc_detected)
    logger.info(f"Quality gate assessed. Acceptable: {quality.acceptable}, Blur: {quality.blur_score}, Glare: {quality.glare_detected}")

    # 4. MRZ Detection and OCR (also settles upside-down pages via checksums)
    working_image, mrz_extracted, mrz_bbox = resolve_mrz_with_orientation(working_image)

    if mrz_extracted:
        doc_info = mrz_extracted["document"]
        holder_info = mrz_extracted["holder"]
        passport_data = mrz_extracted["passport"]
        mrz_data = mrz_extracted["mrz"]
        mrz_valid = mrz_data.valid
    else:
        doc_info = DocumentInfo()
        holder_info = HolderInfo()
        passport_data = PassportData()
        mrz_data = MRZData(format="TD3", raw_lines=[], valid=False, checks=MRZChecks())
        mrz_valid = False

    # 5. Portrait Extraction (after orientation is final)
    portrait_info = extract_primary_portrait(working_image)

    # 6. Visual Zone OCR & Multilingual Field Extraction
    visual_fields = extract_visual_zone_fields(working_image)

    # 7. Field Cross-Validation & Reconciliation
    evidence, warnings, review_required = cross_validate_all_fields(
        doc_info=doc_info,
        holder_info=holder_info,
        passport_data=passport_data,
        mrz_data=mrz_data,
        visual_fields=visual_fields,
        quality=quality
    )

    # 8. Deterministic Confidence Scoring
    confidence_scores = compute_overall_confidence(
        evidence=evidence,
        quality=quality,
        mrz_valid=mrz_valid
    )

    # Generate visual previews
    annotated_b64 = create_annotated_preview(
        working_image,
        portrait_info.bbox if portrait_info else None,
        mrz_bbox,
        visual_fields
    )
    normalized_b64 = encode_image_to_base64_url(working_image, quality=90)

    duration = round(time.time() - start_time, 2)
    logger.info(f"Pipeline finished in {duration}s. Confidence: {confidence_scores.overall}, Review required: {review_required}")

    return PassportAnalysisResponse(
        session_id=session_id,
        document=doc_info,
        holder=holder_info,
        passport=passport_data,
        portrait=portrait_info,
        mrz=mrz_data,
        quality=quality,
        confidence=confidence_scores,
        review_required=review_required,
        warnings=warnings,
        annotated_image_url=annotated_b64,
        normalized_image_url=normalized_b64
    )
