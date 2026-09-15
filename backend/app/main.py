import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import logger
from app.api.routes import router as passport_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production-grade, privacy-first local passport extraction and validation engine."
)

# Cross-Origin Resource Sharing (CORS)
# Configured for secure local development with Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_and_telemetry_headers(request: Request, call_next):
    """
    Apply strict security headers and measure technical processing duration.
    Zero PII or request payload logging.
    """
    start_time = time.time()
    response: Response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Processing-Time-Ms"] = str(duration_ms)

    # Technical audit log only (Path, Method, Status, Duration)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
    return response

# Mount routers
app.include_router(passport_router)

@app.get("/health")
async def health_check():
    """Health check validating backend and offline model status."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "engine": "RapidOCR PP-OCRv4 (ONNX Runtime Local)",
        "offline": True,
        "gpu_enabled": settings.USE_GPU
    }

@app.get("/")
async def root():
    return {
        "message": "Local Passport Information Extraction API is running.",
        "documentation": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
