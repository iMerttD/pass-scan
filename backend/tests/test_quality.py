import cv2
import numpy as np
import pytest
from app.services.passport.quality import assess_image_quality

def test_sharp_image_quality():
    # Generate high frequency sharp checkerboard / edges on paper background
    img = np.ones((800, 1000, 3), dtype=np.uint8) * 235
    for x in range(0, 1000, 20):
        cv2.line(img, (x, 0), (x, 800), (30, 30, 30), 2)

    quality = assess_image_quality(img, is_document_detected=True)
    assert quality.acceptable is True
    assert quality.blur_score > 0.40
    assert quality.glare_detected is False
    assert quality.resolution_ok is True


def test_blurry_image_quality():
    # Blurry image
    img = np.ones((800, 1000, 3), dtype=np.uint8) * 128
    # Uniform gray has 0 variance
    quality = assess_image_quality(img, is_document_detected=True)
    assert quality.acceptable is False
    assert quality.blur_score < 0.1
    assert any("too blurry" in f for f in quality.actionable_feedback)

def test_glare_detection():
    img = np.ones((800, 1000, 3), dtype=np.uint8) * 100
    # Add large bright specular flash covering > 15% of surface
    cv2.circle(img, (500, 400), 220, (255, 255, 255), -1)

    quality = assess_image_quality(img, is_document_detected=True)
    assert quality.glare_detected is True
    assert any("glare detected" in f for f in quality.actionable_feedback)

def test_low_resolution_quality():
    tiny_img = np.ones((200, 200, 3), dtype=np.uint8) * 150
    quality = assess_image_quality(tiny_img, is_document_detected=True)
    assert quality.resolution_ok is False
    assert quality.acceptable is False
