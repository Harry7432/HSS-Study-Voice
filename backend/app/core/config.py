from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "HSS Study Voice"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Directory Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    VOICES_DIR: Path = DATA_DIR / "voices"
    OUTPUT_DIR: Path = BASE_DIR.parent / "output"
    TEMP_DIR: Path = BASE_DIR / "temp"

    # Default TTS Settings
    DEFAULT_PROVIDER: str = "piper"
    DEFAULT_VOICE: str = "pt_BR-cadu-medium"
    DEFAULT_SPEED: float = 1.0

    # Centralized Chunking Configuration
    MAX_CHUNK_CHARS: int = 500
    MIN_CHUNK_CHARS: int = 20

    # Study API Configuration
    MAX_REQUEST_TEXT_CHARS: int = 200_000

    # Audio Export Configuration
    MP3_BITRATE: str = "192k"
    # Leave FFMPEG_PATH empty to auto-detect via shutil.which("ffmpeg").
    # Set it in .env to force a specific binary, e.g. /usr/local/bin/ffmpeg.
    FFMPEG_PATH: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def init_directories(self) -> None:
        """Ensure all required runtime directories exist."""
        self.VOICES_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.init_directories()
