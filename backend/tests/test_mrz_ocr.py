import numpy as np

from app.services.ocr_engine import OCRResult
from app.services.passport import mrz_ocr


def test_full_block_joins_fragmented_rows(monkeypatch):
    first = "P<UTOERIKSSON<<ANNA<MARIA".ljust(44, "<")
    second = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
    fragments = []
    for row_index, line in enumerate((first, second)):
        for column, start in enumerate((0, 15, 30)):
            left = column * 150
            top = row_index * 40
            fragments.append(OCRResult(
                text=line[start:start + 15], confidence=0.95,
                box=[[left, top], [left + 140, top], [left + 140, top + 20], [left, top + 20]],
            ))

    class Engine:
        def extract_text_with_boxes(self, image):
            return list(reversed(fragments))

    monkeypatch.setattr(mrz_ocr, "get_ocr_engine", lambda: Engine())
    monkeypatch.setattr(mrz_ocr, "isolate_mrz_lines", lambda image: [])
    parsed = mrz_ocr.extract_and_parse_mrz(np.zeros((100, 500, 3), dtype=np.uint8))
    assert parsed["mrz"].valid
    assert parsed["holder"].given_names == "ANNA MARIA"
    assert parsed["passport"].passport_number == "L898902C3"


def test_rejects_page_labels_paired_with_valid_second_line():
    bad_first = "TOTDIATIUMYDANOATEOFTRSUEDATEFDEDUVSANC"
    valid_second = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"

    assert mrz_ocr._try_parse_mrz_pair(bad_first, valid_second, 0.9, 0.9) is None


def test_rejects_name_line_without_td3_name_separator():
    bad_first = "P<CZESPECIMEN<VZOR<<<<<<<<<<<<<<<<<<<<<<"
    valid_second = "990090544CZE6906229F16072996956220612<<<<74"

    assert mrz_ocr._try_parse_mrz_pair(bad_first, valid_second, 0.9, 0.9) is None
