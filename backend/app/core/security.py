import os
import uuid
from pathlib import Path
from typing import Tuple
from PIL import Image
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logger import logger

# Set PIL safety limit against decompression bombs
Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS

# Known magic bytes signatures
MAGIC_SIGNATURES = {
    b"\xFF\xD8\xFF": ("image/jpeg", ".jpg"),
    b"\x89PNG\r\n\x1a\n": ("image/png", ".png"),
    b"RIFF": ("image/webp", ".webp"),  # WEBP has 'RIFF....WEBP'
    b"%PDF": ("application/pdf", ".pdf"),
}

def validate_magic_bytes(header: bytes) -> Tuple[str, str]:
    """
    Inspect raw file header to verify authentic file signature.
    Returns (detected_mime, recommended_ext).
    Raises HTTPException 400 if invalid or untrusted.
    """
    if len(header) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is too small or empty."
        )

    # JPEG
    if header.startswith(b"\xFF\xD8\xFF"):
        return "image/jpeg", ".jpg"

    # PNG
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"

    # WEBP
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp", ".webp"

    # PDF
    if header.startswith(b"%PDF"):
        return "application/pdf", ".pdf"

    # HEIC/HEIF check (ftypheic, ftypmif1, etc.)
    if len(header) >= 12 and header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in [b"heic", b"heix", b"hevc", b"heim", b"mif1", b"msf1"]:
            return "image/heic", ".heic"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported or invalid file signature. Only authentic JPG, PNG, WEBP, and PDF files are allowed."
    )

def sanitize_file_path(base_dir: Path, filename: str) -> Path:
    """
    Safely resolve a file path within base_dir, preventing path traversal attacks.
    """
    safe_name = Path(filename).name  # Strips any directory components
    resolved_path = (base_dir / safe_name).resolve()
    if not str(resolved_path).startswith(str(base_dir.resolve())):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Illegal file path detected."
        )
    return resolved_path

def generate_safe_session_id() -> str:
    """Generate a random cryptographically secure UUID v4 for the request session."""
    return str(uuid.uuid4())
