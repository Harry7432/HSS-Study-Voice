import os
import shutil
import tempfile
import wave
from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple, Optional
import httpx
from piper import PiperVoice
from piper.config import SynthesisConfig
from piper.phonemize_espeak import ESPEAK_DATA_DIR

from app.core.config import settings
from app.providers.tts.base import BaseTTSProvider, TTSSynthesisError

PIPER_PT_BR_CATALOG: Dict[str, Dict[str, str]] = {
    "pt_BR-faber-medium": {
        "url_onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx",
        "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json",
    },
    "pt_BR-cadu-medium": {
        "url_onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/cadu/medium/pt_BR-cadu-medium.onnx",
        "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/cadu/medium/pt_BR-cadu-medium.onnx.json",
    },
    "pt_BR-jeff-medium": {
        "url_onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/jeff/medium/pt_BR-jeff-medium.onnx",
        "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/jeff/medium/pt_BR-jeff-medium.onnx.json",
    },
    "pt_BR-edresson-low": {
        "url_onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/edresson/low/pt_BR-edresson-low.onnx",
        "url_json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/edresson/low/pt_BR-edresson-low.onnx.json",
    },
}


@lru_cache(maxsize=1)
def _espeak_data_dir() -> Path:
    """Give Piper an ASCII path because its Windows bridge cannot encode Unicode paths."""
    if os.name != "nt" or str(ESPEAK_DATA_DIR).isascii():
        return ESPEAK_DATA_DIR

    cache_dir = Path(tempfile.gettempdir()) / "hss-study-voice" / "espeak-ng-data"
    shutil.copytree(ESPEAK_DATA_DIR, cache_dir, dirs_exist_ok=True)
    return cache_dir


class PiperProvider(BaseTTSProvider):
    """Piper TTS provider implementation for local offline speech synthesis."""

    def __init__(self, voices_dir: Optional[Path] = None):
        self.voices_dir = voices_dir or settings.VOICES_DIR
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        self._voice_cache: Dict[str, PiperVoice] = {}

    def _get_voice_paths(self, voice_id: str) -> Tuple[Path, Path]:
        onnx_path = self.voices_dir / f"{voice_id}.onnx"
        json_path = self.voices_dir / f"{voice_id}.onnx.json"
        return onnx_path, json_path

    def ensure_voice_downloaded(self, voice_id: str) -> Tuple[Path, Path]:
        """Download model ONNX and JSON files if they do not exist locally."""
        if voice_id not in PIPER_PT_BR_CATALOG:
            raise TTSSynthesisError(f"Voz '{voice_id}' não está presente no catálogo do Piper TTS.")

        onnx_path, json_path = self._get_voice_paths(voice_id)
        if onnx_path.exists() and json_path.exists():
            return onnx_path, json_path

        catalog_entry = PIPER_PT_BR_CATALOG[voice_id]
        try:
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                if not json_path.exists():
                    res = client.get(catalog_entry["url_json"])
                    res.raise_for_status()
                    json_path.write_bytes(res.content)

                if not onnx_path.exists():
                    res = client.get(catalog_entry["url_onnx"])
                    res.raise_for_status()
                    onnx_path.write_bytes(res.content)
        except Exception as e:
            raise TTSSynthesisError(f"Falha ao baixar modelo da voz '{voice_id}': {e}") from e

        return onnx_path, json_path

    def load_voice(self, voice_id: str) -> PiperVoice:
        """Load and cache a PiperVoice instance."""
        if voice_id not in self._voice_cache:
            onnx_path, json_path = self.ensure_voice_downloaded(voice_id)
            try:
                voice = PiperVoice.load(
                    str(onnx_path),
                    str(json_path),
                    espeak_data_dir=_espeak_data_dir(),
                )
                self._voice_cache[voice_id] = voice
            except Exception as e:
                raise TTSSynthesisError(f"Falha ao carregar modelo da voz '{voice_id}': {e}") from e
        return self._voice_cache[voice_id]

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "pt_BR-faber-medium",
        speed: float = 1.0,
    ) -> Path:
        """Synthesize text into a WAV file using Piper.

        Args:
            text: Plain text content.
            output_path: Destination WAV file path.
            voice: Voice model identifier.
            speed: Speed multiplier (1.0 = normal).

        Returns:
            Path to generated WAV file.
        """
        if not text or not text.strip():
            raise TTSSynthesisError("Texto para síntese não pode ser vazio.")

        if speed <= 0:
            raise TTSSynthesisError(f"Velocidade inválida '{speed}'. Deve ser maior que 0.")

        piper_voice = self.load_voice(voice)
        
        # In Piper, length_scale controls audio duration (1.0 / speed)
        length_scale = 1.0 / speed
        syn_config = SynthesisConfig(length_scale=length_scale)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(piper_voice.config.sample_rate)
                piper_voice.synthesize_wav(
                    text,
                    wav_file,
                    syn_config=syn_config,
                    set_wav_format=False,
                )
        except Exception as e:
            raise TTSSynthesisError(f"Erro durante síntese do áudio com Piper: {e}") from e

        return output_path
