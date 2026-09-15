import io
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, List, Tuple
from app.services.passport.mrz_validator import calculate_mrz_check_digit
from app.services.passport.portrait_extractor import encode_image_to_base64_url

def build_valid_td3_lines(
    doc_type: str = "P<",
    country: str = "TUR",
    surname: str = "CELIK",
    given_names: str = "YIGITCAN",
    doc_number: str = "U12345678",
    nationality: str = "TUR",
    dob_yymmdd: str = "950415",
    sex: str = "M",
    expiry_yymmdd: str = "340820",
    optional_data: str = ""
) -> tuple[str, str]:
    """
    Construct valid ICAO 9303 TD3 lines with mathematically verified check digits.
    """
    # Line 1: 44 chars
    clean_surname = surname.strip().upper().replace(" ", "<")
    clean_given = given_names.strip().upper().replace(" ", "<")
    names_field = f"{clean_surname}<<{clean_given}"
    line1 = f"{doc_type}{country}{names_field}".ljust(44, '<')[:44]

    # Line 2:
    # doc_number (9) + check (1)
    doc_clean = doc_number.replace("<", "").ljust(9, '<')[:9]
    doc_chk = calculate_mrz_check_digit(doc_clean)

    # nationality (3)
    nat = nationality.ljust(3, '<')[:3]

    # dob (6) + check (1)
    dob_chk = calculate_mrz_check_digit(dob_yymmdd)

    # sex (1)
    s = sex[:1].upper()

    # expiry (6) + check (1)
    exp_chk = calculate_mrz_check_digit(expiry_yymmdd)

    # optional (14) + check (1)
    opt_field = optional_data.replace("<", "").ljust(14, '<')[:14]
    opt_chk = calculate_mrz_check_digit(opt_field) if optional_data else "<"

    # Line 2 before composite:
    partial_line2 = f"{doc_clean}{doc_chk}{nat}{dob_yymmdd}{dob_chk}{s}{expiry_yymmdd}{exp_chk}{opt_field}{opt_chk}"
    
    # Composite check digit: covers doc_clean+doc_chk + dob_yymmdd+dob_chk + expiry+exp_chk+opt_field+opt_chk
    composite_data = partial_line2[0:10] + partial_line2[13:20] + partial_line2[21:43]
    composite_chk = calculate_mrz_check_digit(composite_data)

    line2 = f"{partial_line2}{composite_chk}"
    return line1, line2


def draw_synthetic_face(w: int, h: int) -> np.ndarray:
    """Generate a clean synthetic passport portrait with head, hair, eyes, and shoulders."""
    img = np.ones((h, w, 3), dtype=np.uint8) * 230  # Light blue-gray background

    # Shoulders / suit
    shoulder_color = (60, 50, 45)  # Dark charcoal
    cv2.ellipse(img, (w // 2, int(h * 1.05)), (int(w * 0.55), int(h * 0.35)), 0, 0, 360, shoulder_color, -1)
    
    # Shirt collar
    cv2.fillPoly(img, [np.array([[w // 2 - 25, int(h * 0.72)], [w // 2 + 25, int(h * 0.72)], [w // 2, int(h * 0.85)]])], (255, 255, 255))
    
    # Neck
    skin_color = (180, 205, 240)  # BGR skin tone
    cv2.rectangle(img, (int(w * 0.40), int(h * 0.55)), (int(w * 0.60), int(h * 0.75)), skin_color, -1)

    # Face Oval
    face_center = (w // 2, int(h * 0.42))
    cv2.ellipse(img, face_center, (int(w * 0.28), int(h * 0.30)), 0, 0, 360, skin_color, -1)

    # Hair
    hair_color = (35, 30, 25)
    cv2.ellipse(img, (w // 2, int(h * 0.28)), (int(w * 0.30), int(h * 0.18)), 0, 180, 360, hair_color, -1)

    # Eyes
    eye_y = int(h * 0.40)
    cv2.circle(img, (w // 2 - 24, eye_y), 5, (50, 40, 30), -1)
    cv2.circle(img, (w // 2 + 24, eye_y), 5, (50, 40, 30), -1)

    # Eyebrows
    cv2.line(img, (w // 2 - 35, eye_y - 10), (w // 2 - 12, eye_y - 12), hair_color, 3)
    cv2.line(img, (w // 2 + 12, eye_y - 12), (w // 2 + 35, eye_y - 10), hair_color, 3)

    # Nose
    cv2.line(img, (w // 2, int(h * 0.40)), (w // 2 - 3, int(h * 0.49)), (150, 175, 210), 2)
    cv2.line(img, (w // 2 - 3, int(h * 0.49)), (w // 2 + 5, int(h * 0.49)), (150, 175, 210), 2)

    # Mouth
    cv2.ellipse(img, (w // 2, int(h * 0.57)), (18, 6), 0, 0, 180, (120, 130, 200), 2)

    return img

def generate_synthetic_passport_image(
    variant: str = "clean",
    surname_unicode: str = "ÇELİK",
    surname_mrz: str = "CELIK",
    given_names: str = "YİĞİTCAN",
    passport_num: str = "U12345678"
) -> Tuple[np.ndarray, bytes]:
    """
    Generate a realistic synthetic passport identity page with OCR-B MRZ zone.
    Returns (image_bgr, jpeg_bytes).
    """
    # Standard document canvas (1420 x 1000)
    w, h = 1420, 1000
    canvas = np.ones((h, w, 3), dtype=np.uint8) * 235  # Warm security document paper

    # Security guilloche watermark pattern (subtle diagonal lines)
    for i in range(0, w + h, 16):
        cv2.line(canvas, (0, i), (i, 0), (220, 220, 215), 1)

    # Top header bar (National header)
    cv2.rectangle(canvas, (40, 30), (w - 40, 95), (190, 20, 30), -1)  # Burgundy/crimson bar
    cv2.putText(canvas, "TURKIYE CUMHURIYETI / REPUBLIC OF TURKEY", (70, 72), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)

    # Sub-header
    cv2.putText(canvas, "PASAPORT / PASSPORT / PASSEPORT", (70, 135), cv2.FONT_HERSHEY_DUPLEX, 0.9, (40, 40, 40), 2)
    cv2.putText(canvas, "Type / Tip: P", (900, 135), cv2.FONT_HERSHEY_DUPLEX, 0.7, (60, 60, 60), 2)
    cv2.putText(canvas, "Country / Ulke: TUR", (1120, 135), cv2.FONT_HERSHEY_DUPLEX, 0.7, (60, 60, 60), 2)

    # Portrait photo (Left side: 80, 170 to 420, 590)
    portrait_w, portrait_h = 340, 430
    portrait_img = draw_synthetic_face(portrait_w, portrait_h)
    canvas[170:170 + portrait_h, 80:80 + portrait_w] = portrait_img
    cv2.rectangle(canvas, (80, 170), (80 + portrait_w, 170 + portrait_h), (120, 120, 120), 2)

    # Visual field zone (X: 470..1360)
    fields = [
        ("Passport No / Pasaport No", passport_num, 195),
        ("Surname / Soyadi", surname_unicode, 260),
        ("Given Names / Adi", given_names, 325),
        ("Nationality / Uyrugu", "TUR", 390),
        ("Date of Birth / Dogum Tarihi", "15 APR / AVR 1995", 455),
        ("Sex / Cinsiyeti", "M", 520),
        ("Place of Birth / Dogum Yeri", "BURSA", 585),
        ("Date of Issue / Verilis Tarihi", "20 AUG / AOU 2024", 650),
        ("Date of Expiry / Gecerlilik Tarihi", "20 AUG / AOU 2034", 715),
    ]

    for label, val, y_pos in fields:
        # Draw label
        cv2.putText(canvas, label.upper(), (470, y_pos - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (110, 110, 110), 1)
        # Draw value
        cv2.putText(canvas, val, (470, y_pos + 18), cv2.FONT_HERSHEY_DUPLEX, 0.85, (15, 15, 15), 2)

    # Separate right column for Authority
    cv2.putText(canvas, "AUTHORITY / VEREN MAKAM", (980, 650 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (110, 110, 110), 1)
    cv2.putText(canvas, "PASAPORT SUBE MD.", (980, 650 + 18), cv2.FONT_HERSHEY_DUPLEX, 0.80, (15, 15, 15), 2)

    # --- MRZ ZONE ---
    # Background strip for MRZ (light paper)
    cv2.rectangle(canvas, (40, 770), (w - 40, 970), (242, 242, 240), -1)
    cv2.line(canvas, (40, 770), (w - 40, 770), (200, 200, 200), 1)


    l1, l2 = build_valid_td3_lines(
        doc_type="P<",
        country="TUR",
        surname=surname_mrz,
        given_names="YIGITCAN",
        doc_number=passport_num,
        nationality="TUR",
        dob_yymmdd="950415",
        sex="M",
        expiry_yymmdd="340820"
    )

    # Render MRZ characters with OCR-B style font
    cv2.putText(canvas, l1, (70, 840), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (10, 10, 10), 2, cv2.LINE_AA)
    cv2.putText(canvas, l2, (70, 915), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (10, 10, 10), 2, cv2.LINE_AA)

    # Apply variant effects
    result = canvas.copy()

    if variant == "skewed":
        # Perspective tilt / rotation
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, -4.5, 0.95)
        result = cv2.warpAffine(result, M, (w, h), borderValue=(210, 210, 210))

    elif variant == "blurry":
        # Severe motion / lens blur
        result = cv2.GaussianBlur(result, (23, 23), 10)

    elif variant == "glare":
        # Specular bright flash spot over the document
        overlay = result.copy()
        cv2.circle(overlay, (600, 260), 240, (255, 255, 255), -1)
        cv2.addWeighted(overlay, 0.90, result, 0.10, 0, result)


    # Encode to JPEG
    success, enc = cv2.imencode(".jpg", result, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    jpeg_bytes = enc.tobytes()

    return result, jpeg_bytes
