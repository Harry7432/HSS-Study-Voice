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

    def fake_synthesize_wav(text, wav_file, syn_config=None):
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x00\x00" * 100)

    mock_voice_instance = MagicMock()
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
    mock_piper_voice_cls.load.assert_called_once_with(str(mock_onnx), str(mock_json))
