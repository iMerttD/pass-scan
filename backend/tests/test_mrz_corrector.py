import pytest
from app.services.passport.mrz_corrector import (
    repair_td3_mrz_lines,
    repair_passport_number_field,
    force_digits_if_needed
)
from app.services.passport.mrz_validator import calculate_mrz_check_digit

def test_force_digits_if_needed():
    # Ambiguous letters in numeric fields
    raw = "95O4I5"  # 'O' and 'I' instead of '0' and '1'
    fixed = force_digits_if_needed(raw)
    assert fixed == "950415"

def test_repair_passport_number_check_digit():
    # Doc number 'U12345678' has check digit 4
    # Suppose OCR misrecognized '4' as 'A' or 'O' instead of 0
    doc_num = "L898902C3"
    # True check digit is 6
    # Suppose check digit was misread as 'G' or 'b'
    repaired_doc, repaired_chk, is_valid, note = repair_passport_number_field("L898902C3", "G")
    assert is_valid is True
    assert repaired_chk == "6"

def test_repair_passport_number_char_substitution():
    # Doc num has true value 'U12345678'
    # Calculate true check digit:
    chk = calculate_mrz_check_digit("U12345678")
    # Suppose OCR misread '1' as 'I' -> 'UI2345678'
    confused_doc = "UI2345678"
    repaired_doc, repaired_chk, is_valid, note = repair_passport_number_field(confused_doc, chk)
    assert is_valid is True
    assert repaired_doc == "U12345678"
    assert note is not None

def test_repair_full_td3_lines():
    # Specimen with deliberate OCR noise:
    # Line 1 with lowercase 'p' at pos 0
    # Line 2 with 'O' in DOB and check digit 'b' for 6
    line1 = "p<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    line2 = "L898902C36UTO74O8122F1204159ZE184226B<<<<<10"

    rep_l1, rep_l2, corrections = repair_td3_mrz_lines(line1, line2)
    assert rep_l1[0] == "P"
    assert "740812" in rep_l2  # 'O' repaired to '0'
    assert len(corrections) > 0
