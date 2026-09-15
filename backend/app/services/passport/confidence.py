from typing import Dict
from app.schemas.passport import FieldEvidence, ConfidenceScores, QualityData

def compute_overall_confidence(
    evidence: Dict[str, FieldEvidence],
    quality: QualityData,
    mrz_valid: bool
) -> ConfidenceScores:
    """
    Compute a deterministic overall confidence score based on:
    - Individual field confidences weighted by criticality
    - ICAO checksum validity
    - Document visual quality (blur, glare, resolution)
    """
    # Critical fields have higher weight in the overall index
    weights = {
        "passport_number": 0.25,
        "surname": 0.15,
        "given_names": 0.15,
        "date_of_birth": 0.15,
        "expiry_date": 0.15,
        "nationality": 0.05,
        "sex": 0.05,
        "place_of_birth": 0.025,
        "date_of_issue": 0.025
    }

    weighted_sum = 0.0
    total_weight = 0.0

    for field_name, weight in weights.items():
        if field_name in evidence and evidence[field_name].value:
            conf = evidence[field_name].confidence
            # Penalty if review required
            if evidence[field_name].review_required:
                conf = min(conf, 0.60)
            weighted_sum += conf * weight
            total_weight += weight
        else:
            # Field missing
            total_weight += weight

    base_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0

    # Quality penalties
    if not quality.acceptable:
        base_score *= 0.70
    elif quality.glare_detected or (quality.blur_score < 0.5):
        base_score *= 0.88

    # ICAO MRZ integrity boost/penalty
    if mrz_valid:
        base_score = min(1.0, base_score * 1.05)
    else:
        base_score = min(base_score, 0.75)

    overall = round(max(0.0, min(0.999, base_score)), 3)

    return ConfidenceScores(
        overall=overall,
        fields=evidence
    )
