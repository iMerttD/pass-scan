import pytest
from app.api.sample_generator import generate_synthetic_passport_image
from app.services.passport.pipeline import process_passport_image

def test_pipeline_clean_synthetic_passport():
    # Generate clean synthetic passport
    _, jpeg_bytes = generate_synthetic_passport_image(
        variant="clean",
        surname_unicode="ÇELİK",
        surname_mrz="CELIK",
        given_names="YİĞİTCAN",
        passport_num="U12345678"
    )

    response = process_passport_image(file_bytes=jpeg_bytes, mime_type="image/jpeg")

    # Verify ICAO 9303 parsed data
    assert response.document.type == "passport"
    assert response.mrz.valid is True
    assert response.mrz.checks.document_number_checksum is True
    assert response.mrz.checks.birth_date_checksum is True
    assert response.mrz.checks.expiry_date_checksum is True
    assert response.mrz.checks.composite_checksum is True

    # Verify extracted fields
    assert response.passport.passport_number == "U12345678"
    assert response.holder.surname_mrz == "CELIK"
    assert response.holder.nationality == "TUR"
    assert response.holder.sex == "M"
    assert response.holder.date_of_birth == "1995-04-15"
    assert response.passport.expiry_date == "2034-08-20"

    # Portrait extraction check
    assert response.portrait is not None
    assert response.portrait.url.startswith("data:image/jpeg;base64,")
    assert response.portrait.confidence > 0.70

    # Overall confidence and quality check
    assert response.confidence.overall > 0.85
    assert response.quality.acceptable is True
    assert response.annotated_image_url is not None

def test_pipeline_blurry_passport_quality_gate():
    # Generate blurry synthetic passport
    _, jpeg_bytes = generate_synthetic_passport_image(variant="blurry")

    response = process_passport_image(file_bytes=jpeg_bytes, mime_type="image/jpeg")

    # Quality gate must trigger warning/unacceptable
    assert response.quality.acceptable is False
    assert any("too blurry" in f for f in response.quality.actionable_feedback)

def test_pipeline_glare_passport():
    # Generate glare-affected passport
    _, jpeg_bytes = generate_synthetic_passport_image(variant="glare")

    response = process_passport_image(file_bytes=jpeg_bytes, mime_type="image/jpeg")

    # Glare should be detected
    assert response.quality.glare_detected is True
    assert any("glare" in f.lower() for f in response.quality.actionable_feedback)
