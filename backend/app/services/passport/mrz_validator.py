from typing import Optional, Dict

# ICAO 9303 repeating weights
MRZ_WEIGHTS = [7, 3, 1]

def mrz_char_value(char: str) -> int:
    """
    Map character to ICAO 9303 numeric value:
    '0'-'9' -> 0-9
    'A'-'Z' -> 10-35
    '<'     -> 0
    Any other character -> 0 (fallback)
    """
    char = char.upper()
    if '0' <= char <= '9':
        return ord(char) - ord('0')
    elif 'A' <= char <= 'Z':
        return ord(char) - ord('A') + 10
    elif char == '<':
        return 0
    return 0

def calculate_mrz_check_digit(data: str) -> str:
    """
    Compute ICAO 9303 check digit using weights 7, 3, 1 repeating modulo 10.
    """
    total = 0
    for idx, ch in enumerate(data):
        weight = MRZ_WEIGHTS[idx % 3]
        total += mrz_char_value(ch) * weight
    return str(total % 10)

def verify_mrz_check_digit(data: str, expected_digit: str) -> bool:
    """
    Verify whether the check digit matches the computed ICAO 9303 check digit.
    Handles '<' as '0' if used in filler positions.
    """
    if not expected_digit:
        return False
    # If the check digit position is filler '<', it can sometimes represent 0 in non-standard docs,
    # but standard is numeric '0'-'9'.
    computed = calculate_mrz_check_digit(data)
    if expected_digit == '<' and computed == '0':
        return True
    return computed == expected_digit

def validate_td3_composite(line2: str) -> bool:
    """
    Validate TD3 composite check digit (position index 43 of line 2).
    Composite covers:
    - Passport number (indices 0-8) + check digit (index 9) -> line2[0:10]
    - Date of birth (indices 13-18) + check digit (index 19) -> line2[13:20]
    - Expiry date (indices 21-26) + check digit (index 27) -> line2[21:28]
    - Optional field (indices 28-41) + optional check digit (index 42) -> line2[28:43]
    In total: line2[0:10] + line2[13:20] + line2[21:43] (39 chars).
    """
    if len(line2) < 44:
        return False
    composite_data = line2[0:10] + line2[13:20] + line2[21:43]
    expected_check = line2[43]
    return verify_mrz_check_digit(composite_data, expected_check)
