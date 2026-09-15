import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Local Passport Extraction System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Storage & Processing
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    TEMP_DIR: Path = BASE_DIR / "temp_uploads"
    SAMPLES_DIR: Path = BASE_DIR / "samples"
    
    # Security
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    MAX_IMAGE_PIXELS: int = 45_000_000  # Decompression bomb threshold
    ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".heic"}
    ALLOWED_MIME_TYPES: set[str] = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "image/heic",
        "image/heif"
    }
    
    # Quality thresholds
    MIN_IMAGE_WIDTH: int = 800
    MIN_IMAGE_HEIGHT: int = 600
    BLUR_THRESHOLD_LAPLACIAN: float = 80.0
    GLARE_PIXEL_RATIO_THRESHOLD: float = 0.08
    
    # Cross-Origin Resource Sharing — override via CORS_ALLOWED_ORIGINS in .env
    # (comma-separated) when the review console is served from another host.
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    # OCR & Engine settings
    USE_GPU: bool = False
    MRZ_CONFIDENCE_THRESHOLD: float = 0.60
    
    # Session / Retention
    AUTO_CLEANUP_TEMP_FILES: bool = True
    SESSION_EXPIRY_SECONDS: int = 3600
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
