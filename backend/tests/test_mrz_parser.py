import pytest
from app.services.passport.mrz_parser import parse_td3_mrz, resolve_mrz_date

def test_resolve_mrz_date_birth():
    # Born in 1995: 950415
    iso_date, raw = resolve_mrz_date("950415", is_expiry=False, reference_year=2026)
    assert iso_date == "1995-04-15"
    assert raw == "950415"

    # Born in 2015: 150620
    iso_date, _ = resolve_mrz_date("150620", is_expiry=False, reference_year=2026)
    assert iso_date == "2015-06-20"

def test_resolve_mrz_date_expiry():
    # Expiring in 2034: 340820
    iso_date, raw = resolve_mrz_date("340820", is_expiry=True, reference_year=2026)
    assert iso_date == "2034-08-20"
    assert raw == "340820"

def test_parse_td3_specimen():
    # ICAO Doc 9303 specimen
    line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    line2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"

    parsed = parse_td3_mrz(line1, line2)
    doc = parsed["document"]
    holder = parsed["holder"]
    passport = parsed["passport"]
    mrz = parsed["mrz"]

    assert doc.document_type_code == "P"
    assert doc.issuing_country == "UTO"
    assert holder.surname == "ERIKSSON"
    assert holder.given_names == "ANNA MARIA"
    assert holder.nationality == "UTO"
    assert holder.sex == "F"
    assert holder.date_of_birth == "1974-08-12"
    assert passport.passport_number == "L898902C3"
    assert passport.expiry_date == "2012-04-15"
    assert mrz.valid is True
    assert mrz.checks.document_number_checksum is True
    assert mrz.checks.birth_date_checksum is True
    assert mrz.checks.expiry_date_checksum is True
    assert mrz.checks.composite_checksum is True

def test_parse_turkish_specimen():
    from app.api.sample_generator import build_valid_td3_lines
    l1, l2 = build_valid_td3_lines(
        surname="CELIK",
        given_names="YIGITCAN MEHMET",
        doc_number="U12345678",
        nationality="TUR",
        dob_yymmdd="950415",
        sex="M",
        expiry_yymmdd="340820"
    )

    parsed = parse_td3_mrz(l1, l2)
    assert parsed["holder"].surname == "CELIK"
    assert parsed["holder"].given_names == "YIGITCAN MEHMET"
    assert parsed["passport"].passport_number == "U12345678"
    assert parsed["mrz"].valid is True
    assert parsed["document"].issuing_country_name == "Türkiye"
