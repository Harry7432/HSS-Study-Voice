import os
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.providers.tts.base import BaseTTSProvider, TTSSynthesisError
from app.providers.tts.piper_provider import PiperProvider, PIPER_PT_BR_CATALOG


def test_piper_provider_implements_base_interface():
    provider = PiperProvider()
    assert isinstance(provider, BaseTTSProvider)


def test_synthesize_empty_text_raises_error(tmp_path):
    provider = PiperProvider(voices_dir=tmp_path)
    output_file = tmp_path / "output.wav"

    with pytest.raises(TTSSynthesisError, match="Texto para síntese não pode ser vazio"):
        provider.synthesize(text="", output_path=output_file, voice="pt_BR-faber-medium")

    with pytest.raises(TTSSynthesisError, match="Texto para síntese não pode ser vazio"):
        provider.synthesize(text="   ", output_path=output_file, voice="pt_BR-faber-medium")


def test_synthesize_invalid_speed_raises_error(tmp_path):
    provider = PiperProvider(voices_dir=tmp_path)
    output_file = tmp_path / "output.wav"

    with pytest.raises(TTSSynthesisError, match="Velocidade inválida"):
        provider.synthesize(text="Teste", output_path=output_file, voice="pt_BR-faber-medium", speed=0)


def test_synthesize_unknown_voice_raises_error(tmp_path):
    provider = PiperProvider(voices_dir=tmp_path)
    output_file = tmp_path / "output.wav"

    with pytest.raises(TTSSynthesisError, match="não está presente no catálogo"):
        provider.synthesize(text="Teste", output_path=output_file, voice="voz-inexistente")


@patch("app.providers.tts.piper_provider.PiperVoice")
@patch.object(PiperProvider, "ensure_voice_downloaded")
def test_synthesize_success_with_mock(mock_ensure_download, mock_piper_voice_cls, tmp_path):
    mock_onnx = tmp_path / "pt_BR-faber-medium.onnx"
    mock_json = tmp_path / "pt_BR-faber-medium.onnx.json"
    mock_ensure_download.return_value = (mock_onnx, mock_json)

    def fake_synthesize_wav(text, wav_file, syn_config=None, set_wav_format=True):
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 22050
        assert syn_config.length_scale == 1.0
        assert set_wav_format is False
        wav_file.writeframes(b"\x00\x00" * 100)

    mock_voice_instance = MagicMock()
    mock_voice_instance.config.sample_rate = 22050
    mock_voice_instance.synthesize_wav.side_effect = fake_synthesize_wav
    mock_piper_voice_cls.load.return_value = mock_voice_instance

    provider = PiperProvider(voices_dir=tmp_path)
    output_wav = tmp_path / "test.wav"

    result_path = provider.synthesize(
        text="Texto de teste",
        output_path=output_wav,
        voice="pt_BR-faber-medium",
        speed=1.0
    )

    assert result_path == output_wav
    assert output_wav.exists()
    assert output_wav.stat().st_size > 0
    mock_ensure_download.assert_called_once_with("pt_BR-faber-medium")
    load_call = mock_piper_voice_cls.load.call_args
    assert load_call.args == (str(mock_onnx), str(mock_json))
    assert Path(load_call.kwargs["espeak_data_dir"]).is_dir()
    if os.name == "nt":
        assert str(load_call.kwargs["espeak_data_dir"]).isascii()


def test_synthesize_preserves_error_before_first_audio_chunk(tmp_path):
    provider = PiperProvider(voices_dir=tmp_path)
    piper_voice = MagicMock()
    piper_voice.config.sample_rate = 16000
    piper_voice.synthesize_wav.side_effect = ImportError("espeakbridge unavailable")
    provider.load_voice = MagicMock(return_value=piper_voice)
    output_wav = tmp_path / "test.wav"

    with pytest.raises(TTSSynthesisError, match="espeakbridge unavailable"):
        provider.synthesize(
            text="Texto de teste",
            output_path=output_wav,
            voice="pt_BR-cadu-medium",
            speed=1.25,
        )

    provider.load_voice.assert_called_once_with("pt_BR-cadu-medium")
    synthesize_call = piper_voice.synthesize_wav.call_args
    assert synthesize_call.kwargs["syn_config"].length_scale == 0.8
    assert synthesize_call.kwargs["set_wav_format"] is False

    with wave.open(str(output_wav), "rb") as wav_file:
        assert wav_file.getframerate() == 16000
