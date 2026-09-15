"""
Rotation robustness: a passport photographed at any 90-degree multiple must
still yield the same checksum-valid MRZ.
"""
import cv2
import pytest

from app.api.sample_generator import generate_synthetic_passport_image
from app.services.passport.mrz_detector import score_mrz_presence
from app.services.passport.pipeline import process_passport_image


def _encode(image):
    ok, buf = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    assert ok
    return buf.tobytes()


@pytest.mark.parametrize("rotation", [None, cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE])
def test_mrz_survives_every_rotation(rotation):
    image, _ = generate_synthetic_passport_image(variant="clean")
    rotated = image if rotation is None else cv2.rotate(image, rotation)

    response = process_passport_image(_encode(rotated), "image/jpeg")

    assert response.mrz.valid is True, f"MRZ failed to validate for rotation {rotation}"
    assert response.passport.passport_number == "U12345678"


def test_mrz_band_scores_above_plain_document_text():
    """The MRZ band must outscore an equally wide heading band."""
    image, _ = generate_synthetic_passport_image(variant="clean")
    h, w = image.shape[:2]
    mrz_band = image[int(h * 0.78):h, 0:w]
    heading_band = image[0:int(h * 0.22), 0:w]

    assert score_mrz_presence(mrz_band) > score_mrz_presence(heading_band)
