import pytest
from app.services.passport.mrz_validator import (
    calculate_mrz_check_digit,
    verify_mrz_check_digit,
    validate_td3_composite,
    mrz_char_value
)

def test_char_values():
    assert mrz_char_value('0') == 0
    assert mrz_char_value('9') == 9
    assert mrz_char_value('A') == 10
    assert mrz_char_value('B') == 11
    assert mrz_char_value('Z') == 35
    assert mrz_char_value('<') == 0

def test_check_digit_calculation():
    # Test doc number 'L898902C3'
    # Weights: 7, 3, 1, 7, 3, 1, 7, 3, 1
    # L(21)*7=147 + 8*3=24 + 9*1=9 + 8*7=56 + 9*3=27 + 0*1=0 + 2*7=14 + C(12)*3=36 + 3*1=3
    # Sum: 147+24+9+56+27+0+14+36+3 = 316. 316 % 10 = 6.
    assert calculate_mrz_check_digit("L898902C3") == "6"
    assert verify_mrz_check_digit("L898902C3", "6") is True
    assert verify_mrz_check_digit("L898902C3", "7") is False

def test_dob_check_digit():
    # DOB: 740812 (12 Aug 1974)
    # 7*7=49, 4*3=12, 0*1=0, 8*7=56, 1*3=3, 2*1=2 => 49+12+0+56+3+2 = 122 => 2
    assert calculate_mrz_check_digit("740812") == "2"
    assert verify_mrz_check_digit("740812", "2") is True

def test_expiry_check_digit():
    # Expiry: 120415 (15 Apr 2012)
    # 1*7=7, 2*3=6, 0*1=0, 4*7=28, 1*3=3, 5*1=5 => 7+6+0+28+3+5 = 49 => 9
    assert calculate_mrz_check_digit("120415") == "9"
    assert verify_mrz_check_digit("120415", "9") is True

def test_td3_composite_checksum():
    # Official ICAO Doc 9303 Part 4 specimen line 2:
    # L898902C36UTO7408122F1204159ZE184226B<<<<<10
    line2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
    assert len(line2) == 44
    assert validate_td3_composite(line2) is True

    # Tampered line 2 should fail composite
    tampered_line2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<19"
    assert validate_td3_composite(tampered_line2) is False
