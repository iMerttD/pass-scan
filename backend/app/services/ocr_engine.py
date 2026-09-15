from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import numpy as np
from pydantic import BaseModel
from app.core.logger import logger

class OCRResult(BaseModel):
    text: str
    confidence: float
    box: List[List[int]]  # 4 corner points [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]

class BaseOCREngine(ABC):
    @abstractmethod
    def extract_text_with_boxes(self, image: np.ndarray) -> List[OCRResult]:
        """Extract text snippets with bounding polygons and confidence scores."""
        pass

class RapidOCREngine(BaseOCREngine):
    """
    PaddleOCR / PP-OCR architecture running locally via RapidOCR (ONNX Runtime).
    Completely offline, self-contained, no external API calls.
    Configured for maximum accuracy on document/passport images.
    """
    _instance: Optional["RapidOCREngine"] = None

    def __init__(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            # Local PP-OCR engine via ONNX Runtime
            self._engine = RapidOCR()
            logger.info("Local PP-OCR (RapidOCR ONNX) engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize RapidOCR: {e}")
            raise e

    @classmethod
    def get_instance(cls) -> "RapidOCREngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def extract_text_with_boxes(self, image: np.ndarray) -> List[OCRResult]:
        """
        Process an image (BGR numpy array) and return detected text lines.
        """
        if image is None or image.size == 0:
            return []

        try:
            result, elapse = self._engine(image)
        except Exception as e:
            logger.warning(f"OCR execution encountered an error: {e}")
            return []

        if not result:
            return []

        ocr_results: List[OCRResult] = []
        for item in result:
            box = item[0]  # list of 4 points [[x, y], ...]
            text = str(item[1]).strip()
            score = float(item[2])
            int_box = [[int(pt[0]), int(pt[1])] for pt in box]
            ocr_results.append(OCRResult(text=text, confidence=score, box=int_box))

        return ocr_results

def get_ocr_engine() -> BaseOCREngine:
    """Factory method to get the active local OCR engine."""
    return RapidOCREngine.get_instance()
