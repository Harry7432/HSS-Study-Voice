import wave


def test_wav_builder_defaults_to_canonical_pcm_format(tmp_path, wav_builder):
    wav_path = wav_builder(tmp_path / "canonical.wav", frame_count=11)

    with wave.open(str(wav_path), "rb") as wav_file:
        assert wav_file.getnframes() == 11
        assert wav_file.getframerate() == 22050
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2


def test_wav_builder_creates_wav_with_configured_pcm_format(tmp_path, wav_builder):
    wav_path = wav_builder(
        tmp_path / "configured.wav",
        frame_count=37,
        sample_rate=16000,
        channels=2,
        sample_width=1,
    )

    assert wav_path == tmp_path / "configured.wav"
    with wave.open(str(wav_path), "rb") as wav_file:
        assert wav_file.getnframes() == 37
        assert wav_file.getframerate() == 16000
        assert wav_file.getnchannels() == 2
        assert wav_file.getsampwidth() == 1
