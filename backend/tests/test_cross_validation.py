import pytest
from app.services.passport.cross_validation import (
    reconcile_field,
    strings_match_transliterated,
    cross_validate_all_fields
)
from app.schemas.passport import DocumentInfo, HolderInfo, PassportData, MRZData, MRZChecks, QualityData

def test_transliteration_matching():
    assert strings_match_transliterated("ÇELİK", "CELIK") is True
    assert strings_match_transliterated("YİĞİTCAN", "YIGITCAN") is True
    assert strings_match_transliterated("MÜLLER", "MULLER") is True
    assert strings_match_transliterated("SMITH", "JONES") is False

def test_reconcile_exact_match():
    ev, warning = reconcile_field(
        field_name="passport_number",
        mrz_val="U12345678",
        visual_val="U12345678",
        checksum_valid=True
    )
    assert ev.status == "VERIFIED"
    assert ev.sources_match is True
    assert ev.confidence >= 0.95
    assert ev.review_required is False
    assert warning is None

def test_reconcile_discrepancy_with_checksum_pass():
    # Visual had OCR typo 'B' instead of '8', but MRZ checksum is valid
    ev, warning = reconcile_field(
        field_name="passport_number",
        mrz_val="U12345678",
        visual_val="U1234567B",
        checksum_valid=True
    )
    assert ev.value == "U12345678"  # Prefers checksum valid MRZ
    assert ev.status == "VERIFIED WITH WARNING"
    assert ev.sources_match is False
    assert ev.review_required is False
    assert warning is not None

def test_reconcile_unicode_preservation():
    ev, warning = reconcile_field(
        field_name="surname",
        mrz_val="CELIK",
        visual_val="ÇELİK",
        checksum_valid=None
    )
    # Should select authentic Unicode spelling 'ÇELİK'
    assert ev.value == "ÇELİK"
    assert ev.sources_match is True
    assert ev.status == "VERIFIED"

def test_plausibility_date_warning():
    doc = DocumentInfo()
    holder = HolderInfo(date_of_birth="2035-01-01")  # Impossible: DOB in 2035
    passport = PassportData(passport_number="U12345678", expiry_date="2030-01-01")
    mrz = MRZData(checks=MRZChecks(document_number_checksum=True, birth_date_checksum=True, expiry_date_checksum=True))
    quality = QualityData()

    evidence, warnings, review_required = cross_validate_all_fields(
        doc_info=doc,
        holder_info=holder,
        passport_data=passport,
        mrz_data=mrz,
        visual_fields={},
        quality=quality
    )

    assert review_required is True
    assert any("Plausibility" in w for w in warnings)


def test_visual_fallback_updates_response_models():
    holder = HolderInfo()
    passport = PassportData()
    fields = {key: {"value": value, "confidence": 0.95} for key, value in {
        "surname": "SMITH", "given_names": "ANNA", "date_of_birth": "1995-04-15",
        "sex": "F", "nationality": "GBR", "passport_number": "123456789",
        "date_of_expiry": "2030-04-15",
    }.items()}
    evidence, _, review = cross_validate_all_fields(
        DocumentInfo(), holder, passport, MRZData(), fields, QualityData())
    assert holder.surname == evidence["surname"].value == "SMITH"
    assert holder.given_names == "ANNA"
    assert holder.date_of_birth == "1995-04-15"
    assert holder.sex == "F"
    assert holder.nationality == "GBR"
    assert passport.passport_number == "123456789"
    assert passport.expiry_date == "2030-04-15"
    assert review is True


def test_visual_confidence_review_status_consistent():
    evidence, _ = reconcile_field("place_of_birth", None, "ANKARA", None, base_visual_conf=0.75)
    assert evidence.status == "NEEDS REVIEW"
    assert evidence.review_required is True
