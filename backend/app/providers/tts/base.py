from abc import ABC, abstractmethod
from pathlib import Path


class TTSSynthesisError(Exception):
    """Exception raised when TTS audio synthesis fails."""
    pass


class BaseTTSProvider(ABC):
    """Abstract interface for Text-to-Speech (TTS) providers."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        speed: float = 1.0,
    ) -> Path:
        """Synthesize plain text into a WAV audio file at output_path.

        Args:
            text: Plain text content to be converted into speech.
            output_path: Destination Path for the generated .wav file.
            voice: Name or identifier of the target voice model.
            speed: Playback speed multiplier (1.0 = normal, 1.25 = 25% faster).

        Returns:
            Path: Absolute path to the generated WAV file.

        Raises:
            TTSSynthesisError: If audio synthesis fails.
        """
        pass
