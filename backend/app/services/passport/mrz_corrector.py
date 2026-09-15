from typing import Tuple, List, Dict, Optional
from app.services.passport.mrz_validator import (
    calculate_mrz_check_digit,
    verify_mrz_check_digit,
    validate_td3_composite
)

# Extended OCR confusion mapping — covers 30+ common misrecognition pairs
DIGIT_TO_LETTER = {
    '0': 'O',
    '1': 'I',
    '2': 'Z',
    '3': 'E',
    '4': 'A',
    '5': 'S',
    '6': 'G',
    '7': 'T',
    '8': 'B',
    '9': 'P',
}

LETTER_TO_DIGIT = {
    'O': '0', 'o': '0', 'Q': '0', 'D': '0',
    'I': '1', 'i': '1', 'L': '1', 'l': '1', '|': '1', 'J': '1',
    'Z': '2', 'z': '2',
    'E': '3',
    'A': '4',
    'S': '5', 's': '5',
    'G': '6', 'C': '6',
    'T': '7',
    'B': '8',
    'P': '9', 'p': '9',
}

# Full bidirectional confusion map for generic positions
CONFUSION_ALTERNATIVES: Dict[str, List[str]] = {
    '0': ['O', 'D', 'Q'],
    'O': ['0', 'D', 'Q'],
    'D': ['0', 'O'],
    'Q': ['0', 'O'],
    '1': ['I', 'L', 'J', '|'],
    'I': ['1', 'L', 'J'],
    'L': ['1', 'I'],
    'J': ['1', 'I'],
    '2': ['Z'],
    'Z': ['2'],
    '3': ['E', '8'],
    'E': ['3'],
    '4': ['A'],
    'A': ['4'],
    '5': ['S'],
    'S': ['5'],
    '6': ['G', 'C'],
    'G': ['6'],
    'C': ['6', 'G'],
    '7': ['T', '1'],
    'T': ['7'],
    '8': ['B', '3'],
    'B': ['8'],
    '9': ['P'],
    'P': ['9'],
    'U': ['V'],
    'V': ['U'],
    'M': ['N', 'W'],
    'N': ['M'],
    'W': ['M'],
    'K': ['X'],
    'X': ['K'],
    'R': ['P'],
    'H': ['N'],
    'F': ['P'],
}

# Positional constraints for TD3 Line 2 (0-indexed)
# These define which character types are valid at each position
TD3_LINE2_CONSTRAINTS = {
    # Positions 0-8: Document number (alphanumeric)
    # Position 9: Check digit (digit)
    9: 'digit',
    # Positions 10-12: Nationality (letters)
    10: 'letter', 11: 'letter', 12: 'letter',
    # Positions 13-18: Date of Birth YYMMDD (digits)
    13: 'digit', 14: 'digit', 15: 'digit', 16: 'digit', 17: 'digit', 18: 'digit',
    # Position 19: DOB check digit (digit)
    19: 'digit',
    # Position 20: Sex (M, F, or <)
    20: 'sex',
    # Positions 21-26: Expiry YYMMDD (digits)
    21: 'digit', 22: 'digit', 23: 'digit', 24: 'digit', 25: 'digit', 26: 'digit',
    # Position 27: Expiry check digit (digit)
    27: 'digit',
    # Position 43: Composite check digit (digit)
    43: 'digit',
}

def repair_passport_number_field(data: str, check_digit: str) -> Tuple[str, str, bool, Optional[str]]:
    """
    Attempt to repair document number and check digit using checksum verification.
    Only accept candidate if checksum verifies.
    Returns (repaired_data, repaired_check_digit, is_valid, correction_note).
    """
    # First check as-is
    if verify_mrz_check_digit(data, check_digit):
        return data, check_digit, True, None

    # Try repairing check digit first if it's a confused letter
    cand_check = LETTER_TO_DIGIT.get(check_digit, check_digit)
    if verify_mrz_check_digit(data, cand_check):
        note = f"Repaired document check digit from '{check_digit}' to '{cand_check}' based on ICAO checksum."
        return data, cand_check, True, note

    # Get all alternatives for each ambiguous character using extended confusion map
    ambiguous_indices = [i for i, ch in enumerate(data) if ch in CONFUSION_ALTERNATIVES]
    
    # Try single substitution first (most common)
    for idx in ambiguous_indices:
        ch = data[idx]
        alternatives = CONFUSION_ALTERNATIVES.get(ch, [])
        for alt in alternatives:
            cand_data = data[:idx] + alt + data[idx+1:]
            # Try with both original and repaired check digit
            for cd in set([check_digit, cand_check]):
                if verify_mrz_check_digit(cand_data, cd):
                    note = f"Repaired document number at pos {idx}: '{ch}' -> '{alt}' (checksum verified)."
                    return cand_data, cd, True, note

    # Try two substitutions if not resolved
    if len(ambiguous_indices) >= 2:
        for i in range(len(ambiguous_indices)):
            for j in range(i + 1, min(len(ambiguous_indices), i + 6)):  # Limit search breadth
                idx1 = ambiguous_indices[i]
                idx2 = ambiguous_indices[j]
                c1, c2 = data[idx1], data[idx2]
                for alt1 in CONFUSION_ALTERNATIVES.get(c1, []):
                    for alt2 in CONFUSION_ALTERNATIVES.get(c2, []):
                        cand_chars = list(data)
                        cand_chars[idx1] = alt1
                        cand_chars[idx2] = alt2
                        cand_data = "".join(cand_chars)
                        for cd in set([check_digit, cand_check]):
                            if verify_mrz_check_digit(cand_data, cd):
                                note = f"Repaired document number positions {idx1} and {idx2} (checksum verified)."
                                return cand_data, cd, True, note

    # Try triple substitution for severely degraded images
    if len(ambiguous_indices) >= 3 and len(ambiguous_indices) <= 8:
        for i in range(len(ambiguous_indices)):
            for j in range(i + 1, min(len(ambiguous_indices), i + 4)):
                for k in range(j + 1, min(len(ambiguous_indices), j + 3)):
                    idx1, idx2, idx3 = ambiguous_indices[i], ambiguous_indices[j], ambiguous_indices[k]
                    c1, c2, c3 = data[idx1], data[idx2], data[idx3]
                    for alt1 in CONFUSION_ALTERNATIVES.get(c1, [])[:2]:
                        for alt2 in CONFUSION_ALTERNATIVES.get(c2, [])[:2]:
                            for alt3 in CONFUSION_ALTERNATIVES.get(c3, [])[:2]:
                                cand_chars = list(data)
                                cand_chars[idx1] = alt1
                                cand_chars[idx2] = alt2
                                cand_chars[idx3] = alt3
                                cand_data = "".join(cand_chars)
                                for cd in set([check_digit, cand_check]):
                                    if verify_mrz_check_digit(cand_data, cd):
                                        note = f"Repaired document number positions {idx1}, {idx2}, {idx3} (checksum verified)."
                                        return cand_data, cd, True, note

    # Return original if unable to deterministically repair
    return data, check_digit, False, None


def force_digits_if_needed(field: str) -> str:
    """Deterministic conversion of ambiguous characters to digits in strictly numeric fields."""
    chars = []
    for c in field:
        if c in LETTER_TO_DIGIT:
            chars.append(LETTER_TO_DIGIT[c])
        elif c == '<':
            chars.append(c)
        elif not c.isdigit():
            # Try confusion alternatives
            alts = CONFUSION_ALTERNATIVES.get(c, [])
            digit_alt = next((a for a in alts if a.isdigit()), None)
            if digit_alt:
                chars.append(digit_alt)
            else:
                chars.append(c)
        else:
            chars.append(c)
    return "".join(chars)


def force_letters_if_needed(field: str) -> str:
    """Deterministic conversion of ambiguous characters to letters in strictly alpha fields."""
    chars = []
    for c in field:
        if c in DIGIT_TO_LETTER:
            chars.append(DIGIT_TO_LETTER[c])
        elif c == '<':
            chars.append(c)
        elif not c.isalpha():
            alts = CONFUSION_ALTERNATIVES.get(c, [])
            letter_alt = next((a for a in alts if a.isalpha()), None)
            if letter_alt:
                chars.append(letter_alt)
            else:
                chars.append(c)
        else:
            chars.append(c)
    return "".join(chars)


def apply_positional_constraints(l2_chars: list, corrections: List[str]) -> list:
    """
    Apply context-aware positional constraints to TD3 line 2.
    Forces characters to match their expected type based on ICAO 9303 format.
    """
    for pos, constraint in TD3_LINE2_CONSTRAINTS.items():
        if pos >= len(l2_chars):
            continue
        ch = l2_chars[pos]
        
        if constraint == 'digit':
            if not ch.isdigit() and ch != '<':
                if ch in LETTER_TO_DIGIT:
                    new_ch = LETTER_TO_DIGIT[ch]
                    corrections.append(f"Position {pos}: forced '{ch}' -> '{new_ch}' (must be digit)")
                    l2_chars[pos] = new_ch
                else:
                    alts = CONFUSION_ALTERNATIVES.get(ch, [])
                    digit_alt = next((a for a in alts if a.isdigit()), None)
                    if digit_alt:
                        corrections.append(f"Position {pos}: forced '{ch}' -> '{digit_alt}' (must be digit)")
                        l2_chars[pos] = digit_alt
        
        elif constraint == 'letter':
            if not ch.isalpha() and ch != '<':
                if ch in DIGIT_TO_LETTER:
                    new_ch = DIGIT_TO_LETTER[ch]
                    corrections.append(f"Position {pos}: forced '{ch}' -> '{new_ch}' (must be letter)")
                    l2_chars[pos] = new_ch
        
        elif constraint == 'sex':
            if ch not in ('M', 'F', '<'):
                # Common confusions for sex field
                sex_map = {'W': 'M', 'N': 'M', 'H': 'M', 'E': 'F'}
                if ch in sex_map:
                    new_ch = sex_map[ch]
                    corrections.append(f"Position {pos}: corrected sex '{ch}' -> '{new_ch}'")
                    l2_chars[pos] = new_ch
                elif ch in LETTER_TO_DIGIT:
                    # Digit in sex position is almost always wrong, default to '<'
                    corrections.append(f"Position {pos}: cleared invalid sex character '{ch}' -> '<'")
                    l2_chars[pos] = '<'

    return l2_chars


def repair_td3_mrz_lines(line1: str, line2: str) -> Tuple[str, str, List[str]]:
    """
    Carefully apply deterministic ICAO error correction to TD3 lines.
    Now with context-aware positional constraints and extended confusion matrix.
    Returns (cleaned_line1, cleaned_line2, list_of_corrections).
    """
    corrections: List[str] = []

    # Clean non-printable characters and ensure length 44
    l1 = line1.strip().upper().replace(" ", "")
    l2 = line2.strip().upper().replace(" ", "")

    if len(l1) < 44:
        l1 = l1.ljust(44, '<')
    if len(l2) < 44:
        l2 = l2.ljust(44, '<')

    l1_chars = list(l1[:44])
    l2_chars = list(l2[:44])

    # 1. Line 1: Pos 0 must be 'P'
    if l1_chars[0] not in ['P']:
        if l1_chars[0] in ['R', 'p', 'b', 'F', '9', 'B']:
            corrections.append(f"Standardized Doc Type line 1 pos 0 from '{l1_chars[0]}' to 'P'.")
            l1_chars[0] = 'P'

    # 2. Line 1: Pos 2..5 (Issuing State) must be 3 letters
    country_code = "".join(l1_chars[2:5])
    country_fixed = force_letters_if_needed(country_code)
    if country_fixed != country_code:
        corrections.append(f"Corrected issuing state code '{country_code}' to '{country_fixed}'.")
        l1_chars[2:5] = list(country_fixed)

    # 3. Apply positional constraints to line 2 FIRST (before checksum repair)
    l2_chars = apply_positional_constraints(l2_chars, corrections)

    # 4. Line 2: Pos 10..13 (Nationality) must be 3 letters
    nat_code = "".join(l2_chars[10:13])
    nat_fixed = force_letters_if_needed(nat_code)
    if nat_fixed != nat_code:
        corrections.append(f"Corrected nationality code '{nat_code}' to '{nat_fixed}'.")
        l2_chars[10:13] = list(nat_fixed)

    # 5. Line 2: Pos 0..9 (Doc number) and Pos 9 (Check digit)
    doc_data = "".join(l2_chars[0:9])
    doc_check = l2_chars[9]
    rep_doc, rep_check, is_valid, note = repair_passport_number_field(doc_data, doc_check)
    if note:
        corrections.append(note)
    l2_chars[0:9] = list(rep_doc)
    l2_chars[9] = rep_check

    # 6. Line 2: Pos 13..19 (DOB) and Pos 19 (Check digit) -> MUST BE DIGITS
    dob_raw = "".join(l2_chars[13:19])
    dob_check = l2_chars[19]
    dob_digits = force_digits_if_needed(dob_raw)
    dob_check_digit = LETTER_TO_DIGIT.get(dob_check, dob_check)
    if dob_digits != dob_raw or dob_check_digit != dob_check:
        if verify_mrz_check_digit(dob_digits, dob_check_digit):
            corrections.append(f"Corrected OCR letters to digits in DOB '{dob_raw}{dob_check}' -> '{dob_digits}{dob_check_digit}'.")
            l2_chars[13:19] = list(dob_digits)
            l2_chars[19] = dob_check_digit

    # 7. Line 2: Pos 21..27 (Expiry) and Pos 27 (Check digit) -> MUST BE DIGITS
    exp_raw = "".join(l2_chars[21:27])
    exp_check = l2_chars[27]
    exp_digits = force_digits_if_needed(exp_raw)
    exp_check_digit = LETTER_TO_DIGIT.get(exp_check, exp_check)
    if exp_digits != exp_raw or exp_check_digit != exp_check:
        if verify_mrz_check_digit(exp_digits, exp_check_digit):
            corrections.append(f"Corrected OCR letters to digits in Expiry '{exp_raw}{exp_check}' -> '{exp_digits}{exp_check_digit}'.")
            l2_chars[21:27] = list(exp_digits)
            l2_chars[27] = exp_check_digit

    # 8. Line 2: Composite Check Digit at pos 43 -> MUST BE DIGIT
    if l2_chars[43] in LETTER_TO_DIGIT:
        c_cand = LETTER_TO_DIGIT[l2_chars[43]]
        curr_l2 = "".join(l2_chars)
        test_l2 = curr_l2[:43] + c_cand
        if validate_td3_composite(test_l2):
            corrections.append(f"Repaired composite check digit '{l2_chars[43]}' to '{c_cand}'.")
            l2_chars[43] = c_cand

    cleaned_l1 = "".join(l1_chars)
    cleaned_l2 = "".join(l2_chars)
    return cleaned_l1, cleaned_l2, corrections

