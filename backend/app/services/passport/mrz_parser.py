import datetime
from typing import Optional, Dict, Any, Tuple
from app.schemas.passport import DocumentInfo, HolderInfo, PassportData, MRZData, MRZChecks
from app.services.passport.countries import resolve_country_name
from app.services.passport.mrz_validator import (
    calculate_mrz_check_digit,
    verify_mrz_check_digit,
    validate_td3_composite
)

def resolve_mrz_date(yymmdd: str, is_expiry: bool = False, reference_year: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse 6-digit YYMMDD into ISO YYYY-MM-DD with century inference.
    Does NOT do naive 20+YY.
    Returns (iso_date, raw_yymmdd).
    """
    if not yymmdd or len(yymmdd) != 6 or not yymmdd.isdigit():
        return None, yymmdd

    if reference_year is None:
        reference_year = datetime.datetime.now().year

    curr_century = (reference_year // 100) * 100  # e.g., 2000

    yy = int(yymmdd[0:2])
    mm = int(yymmdd[2:4])
    dd = int(yymmdd[4:6])

    # Validate month and day bounds
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None, yymmdd

    if is_expiry:
        # Expiry dates sit in a sliding window around today: documents issued in
        # the past are still presented after expiry, and the longest validity
        # currently issued is 10 years. Window: [today - 20y, today + 79y].
        year = curr_century + yy
        if year > reference_year + 79:
            year -= 100
        elif year < reference_year - 20:
            year += 100
    else:
        # Birth dates can never be in the future, and nobody alive exceeds 99
        # years of MRZ-representable age. Window: [today - 99y, today].
        year = curr_century + yy
        if year > reference_year:
            year -= 100

    try:
        dt = datetime.date(year, mm, dd)
    except ValueError:
        return None, yymmdd

    if not is_expiry and dt > datetime.date(reference_year, 12, 31):
        # A birth date later in the current year belongs to the previous century.
        try:
            dt = datetime.date(year - 100, mm, dd)
        except ValueError:
            return None, yymmdd

    return dt.isoformat(), yymmdd

def parse_td3_mrz(line1: str, line2: str) -> Dict[str, Any]:
    """
    Parse standard ICAO Doc 9303 TD3 (2 lines x 44 characters).
    """
    line1 = line1.strip().upper().replace(" ", "")
    line2 = line2.strip().upper().replace(" ", "")

    # Ensure length 44 padded with '<' if slightly truncated
    if len(line1) < 44:
        line1 = line1.ljust(44, '<')
    elif len(line1) > 44:
        line1 = line1[:44]

    if len(line2) < 44:
        line2 = line2.ljust(44, '<')
    elif len(line2) > 44:
        line2 = line2[:44]

    # --- Line 1 parsing ---
    doc_code = line1[0]  # Usually 'P'
    issuing_country = line1[2:5].replace("<", "")
    issuing_country_name = resolve_country_name(line1[2:5])

    name_field = line1[5:44]
    name_parts = name_field.split("<<", 1)
    surname_raw = name_parts[0].replace("<", " ").strip() if len(name_parts) > 0 else ""
    given_raw = name_parts[1].replace("<", " ").strip() if len(name_parts) > 1 else ""

    # Clean multiple spaces
    surname_mrz = " ".join(surname_raw.split())
    given_names_mrz = " ".join(given_raw.split())

    # --- Line 2 parsing ---
    doc_number_raw = line2[0:9].replace("<", "")
    doc_number_check = line2[9]
    nationality = line2[10:13].replace("<", "")
    nationality_name = resolve_country_name(line2[10:13])

    dob_raw = line2[13:19]
    dob_check = line2[19]

    sex_char = line2[20]
    sex = "M" if sex_char == "M" else ("F" if sex_char == "F" else "X")

    expiry_raw = line2[21:27]
    expiry_check = line2[27]

    optional_data = line2[28:42].replace("<", "")
    optional_check = line2[42]
    composite_check = line2[43]

    # Checksums
    doc_num_valid = verify_mrz_check_digit(line2[0:9], doc_number_check)
    dob_valid = verify_mrz_check_digit(dob_raw, dob_check)
    expiry_valid = verify_mrz_check_digit(expiry_raw, expiry_check)
    
    personal_valid: Optional[bool] = None
    if optional_data and optional_check != '<':
        personal_valid = verify_mrz_check_digit(line2[28:42], optional_check)

    composite_valid = validate_td3_composite(line2)

    all_checks_passed = doc_num_valid and dob_valid and expiry_valid and composite_valid

    # Dates
    dob_iso, _ = resolve_mrz_date(dob_raw, is_expiry=False)
    expiry_iso, _ = resolve_mrz_date(expiry_raw, is_expiry=True)

    checks = MRZChecks(
        document_number_checksum=doc_num_valid,
        birth_date_checksum=dob_valid,
        expiry_date_checksum=expiry_valid,
        personal_number_checksum=personal_valid,
        composite_checksum=composite_valid
    )

    mrz_obj = MRZData(
        format="TD3",
        raw_lines=[line1, line2],
        valid=all_checks_passed,
        checks=checks,
        error_corrections_applied=[]
    )

    doc_info = DocumentInfo(
        type="passport",
        document_type_code=doc_code,
        issuing_country=issuing_country,
        issuing_country_name=issuing_country_name
    )

    holder_info = HolderInfo(
        surname=surname_mrz,
        surname_mrz=surname_mrz,
        given_names=given_names_mrz,
        given_names_mrz=given_names_mrz,
        nationality=nationality,
        nationality_name=nationality_name,
        date_of_birth=dob_iso,
        date_of_birth_raw_mrz=dob_raw,
        sex=sex
    )

    passport_info = PassportData(
        passport_number=doc_number_raw,
        issue_date=None,  # Not present in MRZ, must come from visual OCR
        expiry_date=expiry_iso,
        expiry_date_raw_mrz=expiry_raw,
        personal_number=optional_data if optional_data else None
    )

    return {
        "document": doc_info,
        "holder": holder_info,
        "passport": passport_info,
        "mrz": mrz_obj
    }
