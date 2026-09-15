import numpy as np
import pytest

from app.services.ocr_engine import OCRResult
from app.services.passport import visual_ocr


def result(text, left=100, top=100, width=200):
    return OCRResult(text=text, confidence=0.95, box=[
        [left, top], [left + width, top],
        [left + width, top + 20], [left, top + 20],
    ])


def extract(monkeypatch, items):
    class Engine:
        def extract_text_with_boxes(self, image):
            return [item for item in items if item.box[2][1] <= image.shape[0]]

    monkeypatch.setattr(visual_ocr, "get_ocr_engine", lambda: Engine())
    return visual_ocr.extract_visual_zone_fields(np.zeros((1000, 1400, 3), dtype=np.uint8))


@pytest.mark.parametrize("text,field,value", [
    ("Surname / Nom: ÇELİK", "surname", "ÇELİK"),
    ("Given names: ANNA MARIA", "given_names", "ANNA MARIA"),
    ("Passport No.: C4X9T82K1", "passport_number", "C4X9T82K1"),
    ("Sex: FEMALE", "sex", "F"),
    ("Sex: FEMME", "sex", "F"),
    ("Nationality: TÜRKİYE", "nationality", "TÜRKİYE"),
    ("Date of issue: 15.04.2024", "date_of_issue", "2024-04-15"),
])
def test_inline_values(monkeypatch, text, field, value):
    assert extract(monkeypatch, [result(text)])[field]["value"] == value


def test_fields_below_old_fixed_crop(monkeypatch):
    fields = extract(monkeypatch, [result("Authority", top=780), result("ANKARA", top=810)])
    assert fields["issuing_authority"]["value"] == "ANKARA"


def test_invalid_date_not_accepted(monkeypatch):
    fields = extract(monkeypatch, [result("Date of birth"), result("31.02.1995", top=125)])
    assert "date_of_birth" not in fields


def test_multiple_inline_fields(monkeypatch):
    fields = extract(monkeypatch, [result("Surname: SMITH Given names: ANNA")])
    assert fields["surname"]["value"] == "SMITH"
    assert fields["given_names"]["value"] == "ANNA"


def test_three_name_fragments(monkeypatch):
    fields = extract(monkeypatch, [result("Given names"),
        result("ANNA", top=125, width=50),
        result("MARIA", left=160, top=125, width=60),
        result("ELENA", left=230, top=125, width=60)])
    assert fields["given_names"]["value"] == "ANNA MARIA ELENA"


def test_neighboring_column_not_joined(monkeypatch):
    fields = extract(monkeypatch, [result("Given names", width=110),
        result("Nationality", left=230, width=100),
        result("ANNA", top=125, width=110),
        result("TUR", left=230, top=125, width=100)])
    assert fields["given_names"]["value"] == "ANNA"


@pytest.mark.parametrize("text,expected", [
    ("15 JUIN 1995", "1995-06-15"),
    ("15 JUIL 1995", "1995-07-15"),
    ("15 JUILLET 1995", "1995-07-15"),
    ("15 SEPTEMBER 1995", "1995-09-15"),
    ("15 04 1995", "1995-04-15"),
    ("31.02.1995", None),
])
def test_visual_date_formats(text, expected):
    assert visual_ocr.parse_visual_date(text) == expected
