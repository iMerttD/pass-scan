import os
import time
import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks
from app.core.config import settings
from app.core.logger import logger
from app.core.security import validate_magic_bytes, generate_safe_session_id
from app.schemas.passport import (
    PassportAnalysisResponse, ConfirmationRequest, ConfirmationResponse
)
from app.services.passport.pipeline import process_passport_image

router = APIRouter(prefix="/api/passport", tags=["passport"])

# In-memory session store (with TTL cleanup)
# Completely private: no data transmitted externally
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
CONFIRMED_DATA: Dict[str, Dict[str, Any]] = {}

def cleanup_expired_sessions():
    """Background task to remove expired temporary sessions."""
    now = time.time()
    expired = [
        sid for sid, data in ACTIVE_SESSIONS.items()
        if now - data.get("created_at", 0) > settings.SESSION_EXPIRY_SECONDS
    ]
    for sid in expired:
        ACTIVE_SESSIONS.pop(sid, None)

@router.post("/analyze", response_model=PassportAnalysisResponse)
async def analyze_passport(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload and analyze a passport document image or PDF.
    Fully local processing: zero external cloud API calls.
    """
    # 1. Validate file size
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB."
        )

    # 2. Magic byte / header verification
    detected_mime, recommended_ext = validate_magic_bytes(contents[:64])

    session_id = generate_safe_session_id()

    try:
        # Run pipeline
        response = process_passport_image(
            file_bytes=contents,
            mime_type=detected_mime,
            session_id=session_id
        )

        # Store session in memory for review
        ACTIVE_SESSIONS[session_id] = {
            "created_at": time.time(),
            "response": response
        }

        # Trigger session cleanup
        background_tasks.add_task(cleanup_expired_sessions)

        return response

    except HTTPException:
        raise
    except ValueError as e:
        # Unreadable or unsupported document content — the operator can act on this.
        logger.warning(f"Rejected unreadable document: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during passport analysis pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze document. Please ensure the file is an authentic passport image."
        )

@router.get("/{session_id}", response_model=PassportAnalysisResponse)
async def get_passport_analysis(session_id: str):
    """Retrieve existing analysis session."""
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return session["response"]

@router.post("/{session_id}/confirm", response_model=ConfirmationResponse)
async def confirm_passport_data(session_id: str, request: ConfirmationRequest):
    """
    Finalize and save reviewed/verified passport data.
    """
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    record = {
        "document": request.document.model_dump(),
        "holder": request.holder.model_dump(),
        "passport": request.passport.model_dump(),
        "confirmed_at": datetime.datetime.now().isoformat(),
        "user_notes": request.user_notes
    }

    CONFIRMED_DATA[session_id] = record
    logger.info(f"Passport session {session_id} successfully confirmed by user.")

    return ConfirmationResponse(
        session_id=session_id,
        status="confirmed",
        confirmed_at=record["confirmed_at"],
        data=record
    )

@router.post("/sample/{variant}", response_model=PassportAnalysisResponse)
async def process_sample_passport(variant: str = "clean"):
    """
    Generate and analyze a synthetic demo passport:
    - 'clean': Valid ICAO Doc 9303 synthetic passport
    - 'skewed': Rotated passport with deskewing
    - 'blurry': Intentionally blurred passport triggering quality warnings
    - 'glare': Intentionally glare-affected passport
    """
    from app.api.sample_generator import generate_synthetic_passport_image
    
    img_bgr, jpeg_bytes = generate_synthetic_passport_image(variant=variant)
    session_id = generate_safe_session_id()

    response = process_passport_image(
        file_bytes=jpeg_bytes,
        mime_type="image/jpeg",
        session_id=session_id
    )

    ACTIVE_SESSIONS[session_id] = {
        "created_at": time.time(),
        "response": response
    }

    return response

@router.delete("/{session_id}")
async def delete_passport_session(session_id: str):
    """Purge temporary analysis session and associated memory."""
    ACTIVE_SESSIONS.pop(session_id, None)
    CONFIRMED_DATA.pop(session_id, None)
    return {"message": "Session purged successfully."}

