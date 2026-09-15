import re
import datetime
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from app.services.ocr_engine import get_ocr_engine, OCRResult
from app.core.logger import logger

# Expanded multilingual label map with more variants for better matching
MULTILINGUAL_LABEL_MAP: Dict[str, List[str]] = {
    "surname": [
        # EN / FR / DE / ES / IT / PT / NL / TR
        "surname", "family name", "last name", "nom", "nom de famille",
        "nachname", "familienname", "soyadı", "soyadi", "soyad",
        "apellidos", "apelidos", "cognome", "sobrenome", "achternaam",
        "geslachtsnaam",
        # Nordic / Baltic
        "efternamn", "etternavn", "efternavn", "sukunimi", "eftirnafn",
        "perekonnanimi", "uzvārds", "pavardė",
        # Central / Eastern Europe (Latin script)
        "nazwisko", "příjmení", "prijmeni", "priezvisko",
        "vezetéknév", "családi név", "nume", "prezime",
        "priimek",
        # Other widely issued
        "mbiemri", "jina la ukoo", "nama keluarga", "họ",
    ],
    "given_names": [
        "given names", "given name", "forenames", "first name", "first names",
        "prénoms", "prenoms", "prénom", "prenom", "vornamen", "vorname",
        "adı", "adi", "nombres", "nombre", "nome", "nomes", "nome proprio",
        "voornamen", "voornaam",
        "förnamn", "fornavn", "etunimi", "eiginnafn", "eesnimi",
        "vārds", "vardas",
        "imiona", "imię", "jméno", "jmeno", "meno", "utónév",
        "keresztnév", "prenume", "ime", "emri", "nama depan", "tên",
    ],
    "passport_number": [
        "passport no", "passport no.", "passport number", "document no",
        "document number", "doc no", "numéro de passeport",
        "no de passeport", "passeport no", "pasaport no", "pass-nr",
        "reisepass-nr", "passnummer", "pass nr", "número de pasaporte",
        "numero de pasaporte", "pasaporte no", "número do passaporte",
        "passaporto n", "numero passaporto", "paspoortnummer", "paspor no",
        "passin numero", "passets nummer", "pasas nr", "pases nr",
        "numer paszportu", "číslo pasu", "cislo pasu",
        "Útlevél száma", "seria si numarul",
        "seria și numărul", "broj pasoša",
        "številka potnega lista", "numri i pasaportës",
        "nombor pasport", "số hộ chiếu",
    ],
    "nationality": [
        "nationality", "nationalité", "nationalite",
        "staatsangehörigkeit", "staatsangehorigkeit", "uyruğu", "uyrugu",
        "nacionalidad", "nacionalidade", "nazionalità", "nazionalita",
        "cittadinanza", "nationaliteit", "kansalaisuus", "medborgarskap",
        "statsborgerskap", "statsborgerskab", "ríkisfang", "kodakondsus",
        "valstspiederība", "pilietybė", "obywatelstwo",
        "státní občanství", "štátne občianstvo",
        "állampolgárság", "cetățenie", "cetatenie",
        "državljanstvo", "shtetësia", "kewarganegaraan",
        "quốc tịch", "uraia",
    ],
    "date_of_birth": [
        "date of birth", "birth date", "born", "d.o.b", "dob",
        "date de naissance", "geburtsdatum", "doğum tarihi", "dogum tarihi",
        "fecha de nacimiento", "data de nascimento", "data di nascita",
        "geboortedatum", "födelsedatum", "fødselsdato", "syntymäaika",
        "fæðingardagur", "sünniaeg", "dzimšanas datums",
        "gimimo data", "data urodzenia", "datum narození",
        "dátum narodenia", "születési idő",
        "data nașterii", "data nasterii", "datum rođenja",
        "datum rojstva", "datëlindja", "tanggal lahir", "ngày sinh",
        "tarehe ya kuzaliwa",
    ],
    "sex": [
        "sex", "gender", "sexe", "geschlecht", "cinsiyeti", "cinsiyet",
        "sexo", "sesso", "geslacht", "kön", "kjønn", "køn",
        "sukupuoli", "kyn", "sugu", "dzimums", "lytis", "płeć", "plec",
        "pohlaví", "pohlavie", "nem", "sex/sexe", "spol", "gjinia",
        "jenis kelamin", "giới tính", "jinsia",
    ],
    "place_of_birth": [
        "place of birth", "birthplace", "lieu de naissance", "geburtsort",
        "doğum yeri", "dogum yeri", "lugar de nacimiento",
        "local de nascimento", "luogo di nascita", "geboorteplaats",
        "födelseort", "fødested", "syntymäpaikka",
        "fæðingarstaður", "sünnikoht",
        "dzimšanas vieta", "gimimo vieta", "miejsce urodzenia",
        "místo narození", "miesto narodenia", "születési hely",
        "locul nașterii", "locul nasterii", "mjesto rođenja",
        "kraj rojstva", "vendlindja", "tempat lahir", "nơi sinh",
    ],
    "date_of_issue": [
        "date of issue", "issue date", "issued", "issued on",
        "date de délivrance", "date de delivrance",
        "date d’émission", "ausstellungsdatum",
        "veriliş tarihi", "verilis tarihi", "düzenleme tarihi",
        "fecha de expedición", "fecha de expedicion", "data de emissão",
        "data di rilascio", "datum van afgifte", "utfärdandedatum",
        "utstedelsesdato", "udstedelsesdato", "myöntämispäivä",
        "útgáfudagur", "väljaandmise kuupäev",
        "izdošanas datums", "išdavimo data", "data wydania",
        "datum vydání", "dátum vydania",
        "kiállítás dátuma", "data eliberařii",
        "data eliberarii", "datum izdavanja", "datum izdaje",
        "data e lëshimit", "tanggal dikeluarkan", "ngày cấp",
    ],
    "date_of_expiry": [
        "date of expiry", "expiry date", "expiration date", "date of expiration",
        "valid until", "expires", "date d’expiration",
        "date de validité", "ablaufdatum", "gültig bis", "gultig bis",
        "son kullanma tarihi", "geçerlilik tarihi", "gecerlilik tarihi",
        "son geçerlilik tarihi", "fecha de caducidad", "válido hasta",
        "data de validade", "data di scadenza", "geldig tot", "geldigheidsdatum",
        "giltighetstid", "gyldig til", "voimassa", "gildir til", "kehtiv kuni",
        "derīga līdz", "galioja iki", "data ważności",
        "platnost do", "lejárat", "érvényes",
        "data expirării", "data expirarii", "datum isteka", "velja do",
        "vlefshme deri", "berlaku hingga", "có giá trị đến",
    ],
    "issuing_authority": [
        "authority", "issuing authority", "issuing office", "autorité",
        "autorite", "autorité de délivrance", "behörde", "behorde",
        "ausstellende behörde", "veren makam", "düzenleyen makam",
        "autoridad", "autoridade", "autorità", "autoriteit",
        "utfärdande myndighet", "utstedende myndighet",
        "myöntävä viranomainen", "väljaandja",
        "izsniedzēja iestāde", "išdavusi institucija",
        "organ wydający", "vydávající orgán",
        "kiállító hatóság", "autoritatea emitentă",
        "izdato od", "organ izdaje", "autoriteti lëshues",
        "dikeluarkan oleh", "cơ quan cấp",
    ],
}

# Regex patterns for field validation
FIELD_VALIDATION_PATTERNS: Dict[str, str] = {
    "passport_number": r"^(?=[A-Z0-9]{6,12}$)(?=.*\d)[A-Z0-9]+$",
    "sex": r"^[MFXmfx]$",
}

MONTH_MAP = {
    # English
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    # Turkish
    "OCA": 1, "ŞUB": 2, "SUB": 2, "NIS": 4, "NİS": 4,
    "HAZ": 6, "TEM": 7, "AĞU": 8, "AGU": 8, "EYL": 9,
    "EKI": 10, "EKİ": 10, "KAS": 11, "ARA": 12,
    # French
    "FÉV": 2, "FEV": 2, "AVR": 4, "MAI": 5, "JUIN": 6, "JUIL": 7, "JUILLET": 7,
    "AOÛ": 8, "AOU": 8, "DÉC": 12,
    # German
    "MÄR": 3, "MRZ": 3, "OKT": 10, "DEZ": 12,
    # Spanish / Portuguese
    "ENE": 1, "ABR": 4, "AGO": 8, "SET": 9, "OUT": 10, "DIC": 12,
    # Italian
    "GEN": 1, "MAG": 5, "GIU": 6, "LUG": 7, "OTT": 10,
    # Dutch
    "MEI": 5,
    # Finnish
    "TAM": 1, "HEL": 2, "MAA": 3, "HUH": 4, "TOU": 5, "KES": 6,
    "ELO": 8, "SYY": 9, "LOK": 10, "JOU": 12,
    # Polish
    "STY": 1, "LUT": 2, "KWI": 4, "CZE": 6, "LIP": 7, "SIE": 8,
    "WRZ": 9, "PAŹ": 10, "PAZ": 10, "LIS": 11, "GRU": 12,
    # Romanian
    "IAN": 1, "IUN": 6, "IUL": 7, "NOI": 11,
    # Czech / Slovak
    "LED": 1, "ÚNO": 2, "DUB": 4, "KVĚ": 5, "KVE": 5,
    "ČVN": 6, "ČVC": 7, "SRP": 8, "ZÁŘ": 9, "ZAR": 9,
    "ŘÍJ": 10, "RIJ": 10, "PRO": 12,
    # Indonesian / Malay
    "AGT": 8, "DES": 12,
}

def parse_visual_date(text: str) -> Optional[str]:
    """
    Attempt to parse dates from visual text like '15 APR 1995', '15.04.1995', '15/04/1995', '1995-04-15'.
    Returns ISO YYYY-MM-DD or None.
    """
    cleaned = text.strip()
    
    # 1. Check DD.MM.YYYY or DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r"\b(\d{1,2})[. /\-]+(\d{1,2})[. /\-]+(\d{4})\b", cleaned)
    if m:
        d, m_val, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime.date(y, m_val, d).isoformat()
        except ValueError:
            pass

    # 2. Check YYYY-MM-DD
    m = re.search(r"\b(\d{4})[\.\/\-](\d{1,2})[\.\/\-](\d{1,2})\b", cleaned)
    if m:
        y, m_val, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime.date(y, m_val, d).isoformat()
        except ValueError:
            pass

    # 3. Check text month like '15 APR 1995' or '15 APR / AVR 95'
    m = re.search(r"\b(\d{1,2})\s+([^\W\d_]{3,})[\s/]*(?:[^\W\d_]{3,}\s*)?(\d{2}|\d{4})\b", cleaned.upper())
    if m:
        d = int(m.group(1))
        month_str = m.group(2)
        year_raw = int(m.group(3))
        y = year_raw if year_raw > 100 else (2000 + year_raw if year_raw < 50 else 1900 + year_raw)
        m_val = MONTH_MAP.get(month_str) or MONTH_MAP.get(month_str[:3])
        if m_val:
            try:
                return datetime.date(y, m_val, d).isoformat()
            except ValueError:
                pass

    # 4. Check DD MMM YYYY with bilingual month (e.g. "15 APR/AVR 1995")
    m = re.search(r"\b(\d{1,2})\s+(\w{3,4})\s*/\s*(\w{3,4})\s+(\d{2,4})\b", cleaned.upper())
    if m:
        d = int(m.group(1))
        for month_candidate in [m.group(2)[:3], m.group(3)[:3]]:
            m_val = MONTH_MAP.get(month_candidate)
            if m_val:
                year_raw = int(m.group(4))
                y = year_raw if year_raw > 100 else (2000 + year_raw if year_raw < 50 else 1900 + year_raw)
                try:
                    return datetime.date(y, m_val, d).isoformat()
                except ValueError:
                    pass

    return None

def get_box_bounds(box: List[List[int]]) -> Tuple[int, int, int, int]:
    """Return (min_x, min_y, max_x, max_y) for 4-point polygon."""
    xs = [pt[0] for pt in box]
    ys = [pt[1] for pt in box]
    return min(xs), min(ys), max(xs), max(ys)

def get_box_center(box: List[List[int]]) -> Tuple[float, float]:
    """Return center (cx, cy) of a bounding box."""
    xs = [pt[0] for pt in box]
    ys = [pt[1] for pt in box]
    return sum(xs) / len(xs), sum(ys) / len(ys)

def _validate_field_value(field_key: str, value: str) -> bool:
    """Validate extracted value against expected patterns."""
    if field_key in FIELD_VALIDATION_PATTERNS:
        pattern = FIELD_VALIDATION_PATTERNS[field_key]
        return bool(re.match(pattern, value.strip()))
    
    # Date fields: check if parseable
    if "date" in field_key:
        return parse_visual_date(value) is not None

    if field_key == "nationality":
        return 2 <= len(value) <= 60 and all(char.isalpha() or char in " /-()." for char in value)
    
    # Name fields: should contain letters
    if field_key in ("surname", "given_names"):
        return bool(re.search(r"[A-Za-zÀ-ÖÙ-öù-üÇçĞğİıÖöŞşÜü]", value))
    
    # Place of birth: should contain letters
    if field_key == "place_of_birth":
        return bool(re.search(r"[A-Za-z]", value)) and len(value) >= 2
    
    return True


def _find_adjacent_value_boxes(
    label_bounds: Tuple[int, int, int, int],
    other_items: List[Tuple['OCRResult', Tuple[int, int, int, int]]],
    doc_w: int,
    doc_h: int
) -> List[Tuple[float, 'OCRResult']]:
    """
    Find value boxes adjacent to a label using relative spatial thresholds.
    Returns scored candidates list.
    """
    lx1, ly1, lx2, ly2 = label_bounds
    lbl_height = ly2 - ly1
    lbl_width = lx2 - lx1
    
    # Relative thresholds based on document dimensions
    max_below_dist = max(lbl_height * 3.0, doc_h * 0.06)  # Max vertical gap below
    max_right_dist = max(lbl_width * 1.5, doc_w * 0.15)   # Max horizontal gap to right
    max_x_offset = max(80, doc_w * 0.06)                   # Max horizontal alignment offset

    candidates: List[Tuple[float, OCRResult]] = []

    for val_item, (vx1, vy1, vx2, vy2) in other_items:
        # Check below: value is below the label
        below_dist_y = vy1 - ly2
        overlap_x = max(0, min(lx2, vx2) - max(lx1, vx1))
        x_offset = abs(vx1 - lx1)

        if 0 <= below_dist_y <= max_below_dist and (overlap_x > 0 or x_offset < max_x_offset):
            # Score: closer is better, alignment is better
            proximity = 1.0 / (1.0 + below_dist_y / max(1, lbl_height))
            alignment = 1.0 / (1.0 + x_offset / max(1, doc_w) * 10)
            score = proximity * 0.7 + alignment * 0.3
            candidates.append((score, val_item))

        # Check right: value is to the right of label on same line
        right_dist_x = vx1 - lx2
        overlap_y = max(0, min(ly2, vy2) - max(ly1, vy1))
        
        if 0 <= right_dist_x <= max_right_dist and overlap_y > (lbl_height * 0.3):
            proximity = 1.0 / (1.0 + right_dist_x / max(1, doc_w) * 20)
            score = 0.9 * proximity
            candidates.append((score, val_item))

    return candidates


def _concatenate_adjacent_boxes(
    primary_item: 'OCRResult',
    primary_bounds: Tuple[int, int, int, int],
    other_items: List[Tuple['OCRResult', Tuple[int, int, int, int]]],
    doc_w: int
) -> Tuple[str, float]:
    """
    Check if the value spans multiple OCR boxes on the same line (e.g. long names).
    Concatenates text from adjacent boxes to the right.
    Returns (concatenated_text, average_confidence).
    """
    px1, py1, px2, py2 = primary_bounds
    text_parts = [primary_item.text.strip()]
    confidences = [primary_item.confidence]
    current_right = px2
    line_y_center = (py1 + py2) / 2.0
    line_height = py2 - py1

    # Sort remaining items by x position
    right_items = []
    for item, (ix1, iy1, ix2, iy2) in other_items:
        if item is primary_item:
            continue
        item_y_center = (iy1 + iy2) / 2.0
        # Must be on the same horizontal line (within ±60% of line height)
        if abs(item_y_center - line_y_center) < line_height * 0.6:
            gap = ix1 - current_right
            # Must be close to the right (within 2x line height gap)
            if gap >= 0:
                right_items.append((ix1, item, (ix1, iy1, ix2, iy2)))

    right_items.sort(key=lambda x: x[0])

    for _, item, (ix1, iy1, ix2, iy2) in right_items:
        gap = ix1 - current_right
        if 0 <= gap <= line_height * 2.0:
            text_parts.append(item.text.strip())
            confidences.append(item.confidence)
            current_right = ix2
        else:
            break

    combined = " ".join(text_parts)
    avg_conf = sum(confidences) / len(confidences)
    return combined, avg_conf


def extract_visual_zone_fields(image_bgr: np.ndarray) -> Dict[str, Dict[str, Any]]:
    """
    Extract visible zone fields using spatial proximity and multilingual label anchors.
    Uses relative spatial thresholds that adapt to document dimensions.
    Scans the whole identity page and excludes recognized MRZ text.
    """
    h, w = image_bgr.shape[:2]
    visual_crop_h = h
    visual_zone = image_bgr[0:visual_crop_h, 0:w]

    engine = get_ocr_engine()
    ocr_results: List[OCRResult] = engine.extract_text_with_boxes(visual_zone)

    extracted_fields: Dict[str, Dict[str, Any]] = {}

    label_patterns = sorted(
        ((key, label) for key, labels in MULTILINGUAL_LABEL_MAP.items() for label in labels),
        key=lambda entry: len(entry[1]), reverse=True,
    )

    def label_matches(text: str):
        matches = []
        for key, label in label_patterns:
            for match in re.finditer(rf"(?<!\w){re.escape(label)}(?!\w)", text, re.IGNORECASE):
                if not any(match.start() < end and match.end() > start for start, end, _ in matches):
                    matches.append((match.start(), match.end(), key))
        return sorted(matches)

    def match_label_key(text_lower: str) -> Optional[str]:
        matches = label_matches(text_lower)
        return matches[0][2] if matches else None

    def normalize_value(key: str, value: str) -> str:
        value = value.strip(" :./-\t")
        if "date" in key:
            return parse_visual_date(value) or ""
        if key == "passport_number":
            return value.replace(" ", "").upper()
        if key == "sex":
            tokens = re.split(r"[\s/]+", value.upper())
            sexes = {"M": "M", "MALE": "M", "ERKEK": "M", "H": "M", "HOMME": "M",
                     "F": "F", "FEMALE": "F", "KADIN": "F", "W": "F", "FEMME": "F", "X": "X"}
            resolved = {sexes[token] for token in tokens if token in sexes}
            return resolved.pop() if len(resolved) == 1 else ""
        return value

    # Identify label boxes vs candidate value boxes
    label_items: List[Tuple[str, OCRResult, Tuple[int, int, int, int]]] = []
    other_items: List[Tuple[OCRResult, Tuple[int, int, int, int]]] = []

    for item in ocr_results:
        if "<<" in item.text or len(item.text.replace(" ", "")) >= 40 and "<" in item.text:
            continue
        bounds = get_box_bounds(item.box)
        text_lower = item.text.lower()
        matched_key = match_label_key(text_lower)
        if matched_key:
            label_items.append((matched_key, item, bounds))
            matches = label_matches(item.text)
            for index, (_, end, key) in enumerate(matches):
                next_start = matches[index + 1][0] if index + 1 < len(matches) else len(item.text)
                value = normalize_value(key, item.text[end:next_start])
                if value and _validate_field_value(key, value):
                    extracted_fields[key] = {"value": value, "confidence": item.confidence, "box": item.box}
        else:
            other_items.append((item, bounds))

    # For each detected label, find the best value box
    for field_key, lbl_item, lbl_bounds in label_items:
        if field_key in extracted_fields:
            continue

        candidates = _find_adjacent_value_boxes(lbl_bounds, other_items, w, visual_crop_h)

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            
            # Try candidates in order, validate each
            for _, best_val_item in candidates:
                val_bounds = get_box_bounds(best_val_item.box)
                
                # Try concatenating adjacent boxes for multi-word values
                bounded_items = [
                    (item, bounds) for item, bounds in other_items
                    if not any(
                        other_key != field_key and val_bounds[0] < other_bounds[0] <= bounds[0]
                        and abs(other_bounds[1] - lbl_bounds[1]) < max(1, lbl_bounds[3] - lbl_bounds[1])
                        for other_key, _, other_bounds in label_items
                    )
                ]
                val_text, val_conf = _concatenate_adjacent_boxes(
                    best_val_item, val_bounds, bounded_items, w
                )
                val_text = val_text.strip()

                # Date normalization for date fields
                if "date" in field_key:
                    parsed_dt = parse_visual_date(val_text)
                    if parsed_dt:
                        val_text = parsed_dt

                val_text = normalize_value(field_key, val_text)

                # Validate the extracted value
                if val_text and _validate_field_value(field_key, val_text):
                    extracted_fields[field_key] = {
                        "value": val_text,
                        "confidence": val_conf,
                        "box": best_val_item.box
                    }
                    break

    # Also search for standalone passport number patterns if not matched by label
    if "passport_number" not in extracted_fields:
        for val_item, (vx1, vy1, vx2, vy2) in other_items:
            t = val_item.text.strip().replace(" ", "")
            # Pattern: letter(s) followed by digits, or mixed alphanumeric 8-10 chars
            if re.match(r"^[A-Z]{1,2}\d{6,9}$", t):
                extracted_fields["passport_number"] = {
                    "value": t,
                    "confidence": val_item.confidence,
                    "box": val_item.box
                }
                break
            elif re.match(r"^[A-Z0-9]{8,10}$", t) and any(c.isdigit() for c in t) and any(c.isalpha() for c in t):
                extracted_fields["passport_number"] = {
                    "value": t,
                    "confidence": val_item.confidence * 0.9,  # Slightly lower confidence for generic pattern
                    "box": val_item.box
                }
                break

    return extracted_fields
