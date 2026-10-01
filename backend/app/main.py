import shutil
from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Local Text-to-Speech system for study materials."
)


@app.get("/health", tags=["Health"])
def health_check():
    ffmpeg_available = shutil.which("ffmpeg") is not None
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ffmpeg_installed": ffmpeg_available,
        "default_voice": settings.DEFAULT_VOICE,
        "max_chunk_chars": settings.MAX_CHUNK_CHARS,
    }
