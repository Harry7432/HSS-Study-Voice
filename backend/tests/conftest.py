import wave
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def wav_builder() -> Callable[..., Path]:
    def build(
        path: Path,
        *,
        frame_count: int,
        sample_rate: int = 22050,
        channels: int = 1,
        sample_width: int = 2,
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00" * frame_count * channels * sample_width)
        return path

    return build
