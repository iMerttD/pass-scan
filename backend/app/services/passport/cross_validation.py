import unicodedata
from typing import Dict, Any, Tuple, Optional, List
from app.schemas.passport import (
    DocumentInfo, HolderInfo, PassportData, MRZData, FieldEvidence, QualityData
)

def remove_accents(text: str) -> str:
    """Normalize and strip diacritical marks/accents for transliteration comparison."""
    nfkd = unicodedata.normalize('NFKD', text)
    stripped = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Turkish special char handling
    return stripped.replace("ı", "i").replace("İ", "I").upper()

def strings_match_transliterated(str1: Optional[str], str2: Optional[str]) -> bool:
    """Check whether two strings match either exactly or under transliteration/accent stripping."""
    if not str1 or not str2:
        return False
    s1 = remove_accents(str1).replace(" ", "").replace("<", "")
    s2 = remove_accents(str2).replace(" ", "").replace("<", "")
    return s1 == s2

def reconcile_field(
    field_name: str,
    mrz_val: Optional[str],
    visual_val: Optional[str],
    checksum_valid: Optional[bool],
    base_mrz_conf: float = 0.95,
    base_visual_conf: float = 0.85
) -> Tuple[FieldEvidence, Optional[str]]:
    """
    Reconcile a single field between MRZ and Visual OCR sources.
    Returns (FieldEvidence, optional_warning_string).
    """
    warning: Optional[str] = None
    
    # Case 1: Neither found
    if not mrz_val and not visual_val:
        return FieldEvidence(
            value=None,
            confidence=0.0,
            source="none",
            mrz_value=None,
            visual_value=None,
            checksum_valid=checksum_valid,
            sources_match=False,
            review_required=True,
            status="NEEDS REVIEW",
            note="Field could not be detected from either MRZ or visual zone."
        ), f"{field_name.replace('_', ' ').title()} could not be extracted reliably."

    # Case 2: Present in both
    if mrz_val and visual_val:
        exact_match = (mrz_val.strip().upper() == visual_val.strip().upper())
        trans_match = strings_match_transliterated(mrz_val, visual_val)
        matches = exact_match or trans_match

        if matches:
            # If visual has authentic Unicode accents (e.g. ÇELİK vs CELIK), prefer visual for display
            chosen_value = visual_val if len(visual_val) >= len(mrz_val) else mrz_val
            conf = min(0.999, max(base_mrz_conf, base_visual_conf) + 0.05)
            status = "VERIFIED" if (checksum_valid is not False) else "VERIFIED WITH WARNING"
            
            return FieldEvidence(
                value=chosen_value,
                confidence=round(conf, 3),
                source="both",
                mrz_value=mrz_val,
                visual_value=visual_val,
                checksum_valid=checksum_valid,
                sources_match=True,
                review_required=False,
                status=status,
                note="Verified across both MRZ and visual zones."
            ), None
        else:
            # Discrepancy between MRZ and visual!
            if checksum_valid is True:
                # Strongly prefer checksum-valid MRZ
                note = f"Discrepancy: MRZ value '{mrz_val}' verified by ICAO checksum; visual OCR observed '{visual_val}'."
                warning = f"{field_name.replace('_', ' ').title()} had discrepancy between visual ({visual_val}) and MRZ ({mrz_val}). MRZ checksum passed."
                return FieldEvidence(
                    value=mrz_val,
                    confidence=0.92,
                    source="mrz",
                    mrz_value=mrz_val,
                    visual_value=visual_val,
                    checksum_valid=True,
                    sources_match=False,
                    review_required=False,
                    status="VERIFIED WITH WARNING",
                    note=note
                ), warning
            else:
                # Checksum failed or unavailable and values disagree -> Review required!
                note = f"Discrepancy: MRZ '{mrz_val}' and visual '{visual_val}' disagree without valid checksum confirmation."
                warning = f"{field_name.replace('_', ' ').title()} requires review due to disagreement between MRZ and visual zones."
                return FieldEvidence(
                    value=mrz_val,
                    confidence=0.55,
                    source="mrz",
                    mrz_value=mrz_val,
                    visual_value=visual_val,
                    checksum_valid=checksum_valid,
                    sources_match=False,
                    review_required=True,
                    status="NEEDS REVIEW",
                    note=note
                ), warning

    # Case 3: MRZ only
    if mrz_val and not visual_val:
        if checksum_valid is True:
            return FieldEvidence(
                value=mrz_val,
                confidence=0.96,
                source="mrz",
                mrz_value=mrz_val,
                visual_value=None,
                checksum_valid=True,
                sources_match=False,
                review_required=False,
                status="VERIFIED",
                note="Derived from MRZ with verified ICAO checksum."
            ), None
        else:
            status = "VERIFIED WITH WARNING" if (checksum_valid is None) else "NEEDS REVIEW"
            review_req = (checksum_valid is False)
            return FieldEvidence(
                value=mrz_val,
                confidence=0.75 if checksum_valid is None else 0.45,
                source="mrz",
                mrz_value=mrz_val,
                visual_value=None,
                checksum_valid=checksum_valid,
                sources_match=False,
                review_required=review_req,
                status=status,
                note="Derived from MRZ; visual counterpart not detected."
            ), None

    # Case 4: Visual only (e.g. Place of Birth, Date of Issue)
    if visual_val and not mrz_val:
        return FieldEvidence(
            value=visual_val,
            confidence=round(base_visual_conf, 3),
            source="visual",
            mrz_value=None,
            visual_value=visual_val,
            checksum_valid=None,
            sources_match=False,
            review_required=base_visual_conf < 0.70,
            status="VERIFIED" if base_visual_conf >= 0.80 else "NEEDS REVIEW",
            note="Extracted from visual passport zone."
        ), None

    return FieldEvidence(value=None, confidence=0.0, source="none", status="NEEDS REVIEW"), None

def cross_validate_all_fields(
    doc_info: DocumentInfo,
    holder_info: HolderInfo,
    passport_data: PassportData,
    mrz_data: MRZData,
    visual_fields: Dict[str, Dict[str, Any]],
    quality: QualityData
) -> Tuple[Dict[str, FieldEvidence], List[str], bool]:
    """
    Perform complete cross-validation between MRZ extracted data and Visual OCR fields.
    Returns (evidence_dict, warnings_list, overall_review_required).
    """
    evidence: Dict[str, FieldEvidence] = {}
    warnings: List[str] = list(quality.actionable_feedback)
    review_required = False

    checks = mrz_data.checks

    # Helper to get visual field value & confidence
    def get_vis(key: str) -> Tuple[Optional[str], float]:
        if key in visual_fields:
            item = visual_fields[key]
            return item.get("value"), float(item.get("confidence", 0.85))
        return None, 0.0

    # 1. Passport Number
    vis_doc, vis_doc_conf = get_vis("passport_number")
    ev, w = reconcile_field(
        "passport_number",
        passport_data.passport_number,
        vis_doc,
        checks.document_number_checksum,
        base_visual_conf=vis_doc_conf
    )
    evidence["passport_number"] = ev
    if w: warnings.append(w)
    if ev.review_required: review_required = True

    # 2. Surname
    vis_sur, vis_sur_conf = get_vis("surname")
    ev, w = reconcile_field(
        "surname",
        holder_info.surname_mrz,
        vis_sur,
        None,
        base_visual_conf=vis_sur_conf
    )
    if ev.value and vis_sur and strings_match_transliterated(holder_info.surname_mrz, vis_sur):
        holder_info.surname = vis_sur  # Retain authentic Unicode
    evidence["surname"] = ev
    if w: warnings.append(w)
    if ev.review_required: review_required = True

    # 3. Given Names
    vis_giv, vis_giv_conf = get_vis("given_names")
    ev, w = reconcile_field(
        "given_names",
        holder_info.given_names_mrz,
        vis_giv,
        None,
        base_visual_conf=vis_giv_conf
    )
    if ev.value and vis_giv and strings_match_transliterated(holder_info.given_names_mrz, vis_giv):
        holder_info.given_names = vis_giv  # Retain authentic Unicode
    evidence["given_names"] = ev
    if w: warnings.append(w)
    if ev.review_required: review_required = True

    # 4. Date of Birth
    vis_dob, vis_dob_conf = get_vis("date_of_birth")
    ev, w = reconcile_field(
        "date_of_birth",
        holder_info.date_of_birth,
        vis_dob,
        checks.birth_date_checksum,
        base_visual_conf=vis_dob_conf
    )
    evidence["date_of_birth"] = ev
    if w: warnings.append(w)
    if ev.review_required: review_required = True

    # 5. Sex
    vis_sex, vis_sex_conf = get_vis("sex")
    ev, w = reconcile_field("sex", holder_info.sex, vis_sex, None, base_visual_conf=vis_sex_conf)
    evidence["sex"] = ev
    if w: warnings.append(w)

    # 6. Expiry Date
    vis_exp, vis_exp_conf = get_vis("date_of_expiry")
    ev, w = reconcile_field(
        "expiry_date",
        passport_data.expiry_date,
        vis_exp,
        checks.expiry_date_checksum,
        base_visual_conf=vis_exp_conf
    )
    evidence["expiry_date"] = ev
    if w: warnings.append(w)
    if ev.review_required: review_required = True

    # 7. Nationality
    vis_nat, vis_nat_conf = get_vis("nationality")
    ev, w = reconcile_field("nationality", holder_info.nationality, vis_nat, None, base_visual_conf=vis_nat_conf)
    evidence["nationality"] = ev
    if w: warnings.append(w)

    # 8. Date of Issue (Visual only)
    vis_iss, vis_iss_conf = get_vis("date_of_issue")
    ev, w = reconcile_field("date_of_issue", None, vis_iss, None, base_visual_conf=vis_iss_conf)
    evidence["date_of_issue"] = ev
    passport_data.issue_date = ev.value
    if w: warnings.append(w)

    # 9. Place of Birth (Visual only)
    vis_pob, vis_pob_conf = get_vis("place_of_birth")
    ev, w = reconcile_field("place_of_birth", None, vis_pob, None, base_visual_conf=vis_pob_conf)
    evidence["place_of_birth"] = ev
    holder_info.place_of_birth = ev.value
    if w: warnings.append(w)

    # 10. Issuing Authority (Visual only)
    vis_auth, vis_auth_conf = get_vis("issuing_authority")
    ev, w = reconcile_field("issuing_authority", None, vis_auth, None, base_visual_conf=vis_auth_conf)
    evidence["issuing_authority"] = ev
    passport_data.issuing_authority = ev.value
    if w: warnings.append(w)

    # Plausibility checks on dates
    if holder_info.date_of_birth and passport_data.expiry_date:
        if holder_info.date_of_birth >= passport_data.expiry_date:
            warnings.append("Plausibility warning: Date of birth is after expiry date.")
            review_required = True

    if passport_data.issue_date and passport_data.expiry_date:
        if passport_data.issue_date >= passport_data.expiry_date:
            warnings.append("Plausibility warning: Issue date is after expiry date.")
            review_required = True

    return evidence, warnings, review_required
