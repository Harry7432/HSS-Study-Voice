"""Unit tests for the version 1 text-audio timeline."""

import pytest


def build_timeline(
    *,
    sample_rate_hz=22050,
    total_samples=30,
    ranges=((0, 10), (10, 30)),
):
    from app.services.audio.timeline import (
        TimelineAudio,
        TimelineChunk,
        TimelineDocument,
        TimelineSentence,
    )

    sentences = tuple(
        TimelineSentence(
            index=index,
            text=f"Frase {index}.",
            start_sample=start_sample,
            end_sample=end_sample,
        )
        for index, (start_sample, end_sample) in enumerate(ranges)
    )
    chunk = TimelineChunk(
        index=0,
        start_sample=sentences[0].start_sample,
        end_sample=sentences[-1].end_sample,
        sentences=sentences,
    )
    return TimelineDocument(
        schema_version=1,
        audio=TimelineAudio(
            filename="lesson.mp3",
            sha256="a" * 64,
            sample_rate_hz=sample_rate_hz,
            total_samples=total_samples,
        ),
        chunks=(chunk,),
    )


@pytest.mark.parametrize(
    ("model_name", "missing_field"),
    [
        ("TimelineAudio", "total_samples"),
        ("TimelineSentence", "end_sample"),
        ("TimelineChunk", "sentences"),
        ("TimelineDocument", "chunks"),
    ],
)
def test_timeline_v1_models_require_all_contract_fields(model_name, missing_field):
    from app.services.audio.timeline import (
        TimelineAudio,
        TimelineChunk,
        TimelineDocument,
        TimelineSentence,
    )

    model_types = {
        "TimelineAudio": TimelineAudio,
        "TimelineSentence": TimelineSentence,
        "TimelineChunk": TimelineChunk,
        "TimelineDocument": TimelineDocument,
    }
    complete_fields = {
        "TimelineAudio": {
            "filename": "lesson.mp3",
            "sha256": "a" * 64,
            "sample_rate_hz": 22050,
            "total_samples": 30,
        },
        "TimelineSentence": {
            "index": 0,
            "text": "Frase.",
            "start_sample": 0,
            "end_sample": 30,
        },
        "TimelineChunk": {
            "index": 0,
            "start_sample": 0,
            "end_sample": 30,
            "sentences": (),
        },
        "TimelineDocument": {
            "schema_version": 1,
            "audio": None,
            "chunks": (),
        },
    }
    fields = complete_fields[model_name]
    del fields[missing_field]

    with pytest.raises(TypeError):
        model_types[model_name](**fields)


def test_timeline_v1_has_required_fields_and_valid_half_open_ranges():
    timeline = build_timeline()

    timeline.validate(merged_frame_count=30)

    assert timeline.schema_version == 1
    assert (
        timeline.audio.filename,
        timeline.audio.sha256,
        timeline.audio.sample_rate_hz,
        timeline.audio.total_samples,
    ) == ("lesson.mp3", "a" * 64, 22050, 30)
    assert len(timeline.chunks) == 1
    assert (
        timeline.chunks[0].index,
        timeline.chunks[0].start_sample,
        timeline.chunks[0].end_sample,
    ) == (0, 0, 30)
    assert [
        (
            sentence.index,
            sentence.text,
            sentence.start_sample,
            sentence.end_sample,
        )
        for sentence in timeline.chunks[0].sentences
    ] == [
        (0, "Frase 0.", 0, 10),
        (1, "Frase 1.", 10, 30),
    ]


@pytest.mark.parametrize(
    "ranges",
    [
        ((1, 10), (10, 30)),
        ((0, 10), (11, 30)),
        ((0, 11), (10, 30)),
        ((0, 0), (0, 30)),
    ],
    ids=["non-zero-start", "gap", "overlap", "empty-interval"],
)
def test_timeline_rejects_non_contiguous_or_empty_half_open_ranges(ranges):
    timeline = build_timeline(ranges=ranges)

    with pytest.raises(ValueError):
        timeline.validate(merged_frame_count=30)


def test_timeline_rejects_non_integer_sample_boundaries():
    timeline = build_timeline(ranges=((0, 10.5), (10.5, 30)))

    with pytest.raises(ValueError):
        timeline.validate(merged_frame_count=30)


def test_timeline_rejects_sample_rate_other_than_22050_hz():
    with pytest.raises(ValueError):
        timeline = build_timeline(sample_rate_hz=44100)
        timeline.validate(merged_frame_count=30)


@pytest.mark.parametrize("total_samples", [0, -1])
def test_timeline_rejects_non_positive_total_samples(total_samples):
    with pytest.raises(ValueError):
        timeline = build_timeline(total_samples=total_samples)
        timeline.validate(merged_frame_count=total_samples)


def test_timeline_rejects_merged_frame_count_mismatch():
    timeline = build_timeline()

    with pytest.raises(ValueError):
        timeline.validate(merged_frame_count=29)


def test_timeline_rejects_last_sentence_end_different_from_verified_total():
    timeline = build_timeline(ranges=((0, 10), (10, 29)))

    with pytest.raises(ValueError):
        timeline.validate(merged_frame_count=30)


def build_multi_chunk_timeline(
    chunk_specs=(
        ((0, 10), (10, 20)),
        ((20, 35), (35, 50)),
    ),
    *,
    sample_rate_hz=22050,
    total_samples=50,
    filename="lesson.mp3",
    sha256="a" * 64,
    texts=None,
):
    from app.services.audio.timeline import (
        TimelineAudio,
        TimelineChunk,
        TimelineDocument,
        TimelineSentence,
    )

    chunks = []
    for chunk_idx, ranges in enumerate(chunk_specs):
        sentences = tuple(
            TimelineSentence(
                index=sent_idx,
                text=(
                    texts[chunk_idx][sent_idx]
                    if texts
                    and chunk_idx < len(texts)
                    and sent_idx < len(texts[chunk_idx])
                    else f"Frase {chunk_idx}:{sent_idx}."
                ),
                start_sample=start,
                end_sample=end,
            )
            for sent_idx, (start, end) in enumerate(ranges)
        )
        chunks.append(
            TimelineChunk(
                index=chunk_idx,
                start_sample=sentences[0].start_sample,
                end_sample=sentences[-1].end_sample,
                sentences=sentences,
            )
        )

    return TimelineDocument(
        schema_version=1,
        audio=TimelineAudio(
            filename=filename,
            sha256=sha256,
            sample_rate_hz=sample_rate_hz,
            total_samples=total_samples,
        ),
        chunks=tuple(chunks),
    )


def test_multi_chunk_timeline_ordering_and_aggregate_limits():
    timeline = build_multi_chunk_timeline(
        chunk_specs=(
            ((0, 15), (15, 30)),
            ((30, 45), (45, 70)),
            ((70, 100),),
        ),
        total_samples=100,
    )

    timeline.validate(merged_frame_count=100)

    assert len(timeline.chunks) == 3
    assert [chunk.index for chunk in timeline.chunks] == [0, 1, 2]
    assert [
        (chunk.start_sample, chunk.end_sample) for chunk in timeline.chunks
    ] == [(0, 30), (30, 70), (70, 100)]

    for chunk in timeline.chunks:
        assert [sentence.index for sentence in chunk.sentences] == list(
            range(len(chunk.sentences))
        )

    doc_dict = timeline.to_dict()
    assert len(doc_dict["chunks"]) == 3
    assert [c["index"] for c in doc_dict["chunks"]] == [0, 1, 2]
    assert [
        [s["index"] for s in c["sentences"]] for c in doc_dict["chunks"]
    ] == [[0, 1], [0, 1], [0]]


def test_multi_chunk_timeline_preserves_repeated_sentence_text():
    texts = (
        ("Texto repetido.", "Outra frase.", "Texto repetido."),
        ("Texto repetido.", "Conclusão."),
    )
    timeline = build_multi_chunk_timeline(
        chunk_specs=(
            ((0, 10), (10, 20), (20, 30)),
            ((30, 45), (45, 60)),
        ),
        total_samples=60,
        texts=texts,
    )

    timeline.validate(merged_frame_count=60)

    first_chunk_sentences = timeline.chunks[0].sentences
    second_chunk_sentences = timeline.chunks[1].sentences

    assert first_chunk_sentences[0].text == "Texto repetido."
    assert first_chunk_sentences[2].text == "Texto repetido."
    assert second_chunk_sentences[0].text == "Texto repetido."

    assert (
        (0, 0),
        first_chunk_sentences[0].start_sample,
        first_chunk_sentences[0].end_sample,
    ) == ((0, 0), 0, 10)
    assert (
        (0, 2),
        first_chunk_sentences[2].start_sample,
        first_chunk_sentences[2].end_sample,
    ) == ((0, 2), 20, 30)
    assert (
        (1, 0),
        second_chunk_sentences[0].start_sample,
        second_chunk_sentences[0].end_sample,
    ) == ((1, 0), 30, 45)


@pytest.mark.parametrize(
    "invalid_chunk_indices",
    [
        (1, 0),
        (0, 2),
        (1, 2),
    ],
    ids=["inverted", "gap-in-indices", "non-zero-start"],
)
def test_multi_chunk_timeline_rejects_out_of_order_chunk_indices(
    invalid_chunk_indices,
):
    from app.services.audio.timeline import (
        TimelineAudio,
        TimelineChunk,
        TimelineDocument,
        TimelineSentence,
    )

    chunks = (
        TimelineChunk(
            index=invalid_chunk_indices[0],
            start_sample=0,
            end_sample=15,
            sentences=(
                TimelineSentence(
                    index=0,
                    text="Chunk 0.",
                    start_sample=0,
                    end_sample=15,
                ),
            ),
        ),
        TimelineChunk(
            index=invalid_chunk_indices[1],
            start_sample=15,
            end_sample=30,
            sentences=(
                TimelineSentence(
                    index=0,
                    text="Chunk 1.",
                    start_sample=15,
                    end_sample=30,
                ),
            ),
        ),
    )
    timeline = TimelineDocument(
        schema_version=1,
        audio=TimelineAudio(
            filename="lesson.mp3",
            sha256="a" * 64,
            sample_rate_hz=22050,
            total_samples=30,
        ),
        chunks=chunks,
    )

    with pytest.raises(
        ValueError, match="TimelineChunk.index must equal its collection position"
    ):
        timeline.validate(merged_frame_count=30)


@pytest.mark.parametrize(
    ("chunk_index", "sentence_indices"),
    [
        (0, (1, 2)),
        (1, (2, 3)),
    ],
    ids=["chunk0-not-zero-based", "chunk1-global-indices-not-zero-based"],
)
def test_multi_chunk_timeline_rejects_non_zero_based_sentence_indices(
    chunk_index,
    sentence_indices,
):
    from app.services.audio.timeline import (
        TimelineAudio,
        TimelineChunk,
        TimelineDocument,
        TimelineSentence,
    )

    def make_sentences(indices, start_offset):
        return tuple(
            TimelineSentence(
                index=idx,
                text=f"Frase {idx}.",
                start_sample=start_offset + pos * 10,
                end_sample=start_offset + (pos + 1) * 10,
            )
            for pos, idx in enumerate(indices)
        )

    sentences_c0 = (
        make_sentences(sentence_indices, 0)
        if chunk_index == 0
        else make_sentences((0, 1), 0)
    )
    sentences_c1 = (
        make_sentences(sentence_indices, 20)
        if chunk_index == 1
        else make_sentences((0, 1), 20)
    )

    chunks = (
        TimelineChunk(
            index=0,
            start_sample=0,
            end_sample=20,
            sentences=sentences_c0,
        ),
        TimelineChunk(
            index=1,
            start_sample=20,
            end_sample=40,
            sentences=sentences_c1,
        ),
    )
    timeline = TimelineDocument(
        schema_version=1,
        audio=TimelineAudio(
            filename="lesson.mp3",
            sha256="a" * 64,
            sample_rate_hz=22050,
            total_samples=40,
        ),
        chunks=chunks,
    )

    with pytest.raises(
        ValueError, match="TimelineSentence.index must equal its collection position"
    ):
        timeline.validate(merged_frame_count=40)


@pytest.mark.parametrize(
    ("chunk_ranges", "expected_match"),
    [
        (
            ((0, 20), (25, 40)),
            "Timeline chunks must form contiguous ranges",
        ),
        (
            ((0, 20), (15, 35)),
            "Timeline chunks must form contiguous ranges",
        ),
        (
            ((5, 20), (20, 40)),
            "Timeline chunks must form contiguous ranges",
        ),
    ],
    ids=["gap-between-chunks", "overlap-between-chunks", "first-chunk-non-zero-start"],
)
def test_multi_chunk_timeline_rejects_non_contiguous_chunks(
    chunk_ranges,
    expected_match,
):
    from app.services.audio.timeline import (
        TimelineAudio,
        TimelineChunk,
        TimelineDocument,
        TimelineSentence,
    )

    chunks = tuple(
        TimelineChunk(
            index=idx,
            start_sample=start,
            end_sample=end,
            sentences=(
                TimelineSentence(
                    index=0,
                    text=f"Frase chunk {idx}.",
                    start_sample=start,
                    end_sample=end,
                ),
            ),
        )
        for idx, (start, end) in enumerate(chunk_ranges)
    )
    timeline = TimelineDocument(
        schema_version=1,
        audio=TimelineAudio(
            filename="lesson.mp3",
            sha256="a" * 64,
            sample_rate_hz=22050,
            total_samples=chunks[-1].end_sample,
        ),
        chunks=chunks,
    )

    with pytest.raises(ValueError, match=expected_match):
        timeline.validate(merged_frame_count=chunks[-1].end_sample)


def test_multi_chunk_timeline_rejects_chunk_start_different_from_first_sentence():
    from app.services.audio.timeline import (
        TimelineAudio,
        TimelineChunk,
        TimelineDocument,
        TimelineSentence,
    )

    chunks = (
        TimelineChunk(
            index=0,
            start_sample=0,
            end_sample=20,
            sentences=(
                TimelineSentence(
                    index=0,
                    text="Frase.",
                    start_sample=5,
                    end_sample=20,
                ),
            ),
        ),
    )
    timeline = TimelineDocument(
        schema_version=1,
        audio=TimelineAudio(
            filename="lesson.mp3",
            sha256="a" * 64,
            sample_rate_hz=22050,
            total_samples=20,
        ),
        chunks=chunks,
    )

    with pytest.raises(
        ValueError,
        match="TimelineChunk.start_sample must equal its first sentence start",
    ):
        timeline.validate(merged_frame_count=20)


def test_multi_chunk_timeline_rejects_chunk_end_different_from_last_sentence():
    from app.services.audio.timeline import (
        TimelineAudio,
        TimelineChunk,
        TimelineDocument,
        TimelineSentence,
    )

    chunks = (
        TimelineChunk(
            index=0,
            start_sample=0,
            end_sample=25,
            sentences=(
                TimelineSentence(
                    index=0,
                    text="Frase.",
                    start_sample=0,
                    end_sample=20,
                ),
            ),
        ),
    )
    timeline = TimelineDocument(
        schema_version=1,
        audio=TimelineAudio(
            filename="lesson.mp3",
            sha256="a" * 64,
            sample_rate_hz=22050,
            total_samples=25,
        ),
        chunks=chunks,
    )

    with pytest.raises(
        ValueError,
        match="TimelineChunk.end_sample must equal its last sentence end",
    ):
        timeline.validate(merged_frame_count=25)


def test_multi_chunk_timeline_write_json_roundtrip(tmp_path):
    import json

    timeline = build_multi_chunk_timeline(
        chunk_specs=(
            ((0, 10), (10, 20)),
            ((20, 35), (35, 50)),
        ),
        total_samples=50,
    )
    target_path = tmp_path / "lesson.timeline.json"

    written = timeline.write(target_path, merged_frame_count=50)

    assert written == target_path
    assert written.is_file()

    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["audio"]["total_samples"] == 50
    assert len(payload["chunks"]) == 2
    assert payload["chunks"][0]["index"] == 0
    assert payload["chunks"][0]["start_sample"] == 0
    assert payload["chunks"][0]["end_sample"] == 20
    assert payload["chunks"][1]["index"] == 1
    assert payload["chunks"][1]["start_sample"] == 20
    assert payload["chunks"][1]["end_sample"] == 50


def test_timeline_path_for_derives_sidecar_and_validates_suffix():
    from pathlib import Path
    import pytest
    from app.services.audio.timeline import timeline_path_for

    assert timeline_path_for(Path("audio/lesson.mp3")) == Path("audio/lesson.timeline.json")
    assert timeline_path_for(Path("lesson.mp3")) == Path("lesson.timeline.json")

    for invalid_path in [
        Path("lesson.MP3"),
        Path("lesson.wav"),
        Path("lesson"),
        Path(".mp3"),
    ]:
        with pytest.raises(ValueError):
            timeline_path_for(invalid_path)


def test_timeline_audio_validates_lowercase_sha256_and_filename_basename():
    import pytest
    from app.services.audio.timeline import TimelineAudio

    audio = TimelineAudio(
        filename="lesson.mp3",
        sha256="a" * 64,
        sample_rate_hz=22050,
        total_samples=100,
    )
    audio.validate()

    with pytest.raises(ValueError, match="sha256"):
        TimelineAudio(
            filename="lesson.mp3",
            sha256="A" * 64,
            sample_rate_hz=22050,
            total_samples=100,
        ).validate()

    with pytest.raises(ValueError, match="filename"):
        TimelineAudio(
            filename="dir/lesson.mp3",
            sha256="a" * 64,
            sample_rate_hz=22050,
            total_samples=100,
        ).validate()


def test_sha256_calculation_and_mp3_tamper_detection(tmp_path):
    from app.services.audio.timeline import compute_sha256, verify_mp3_sha256

    mp3_file = tmp_path / "sample.mp3"
    original_bytes = b"ID3v2_sample_audio_data_12345"
    mp3_file.write_bytes(original_bytes)

    digest = compute_sha256(mp3_file)
    assert len(digest) == 64
    assert digest == digest.lower()
    assert verify_mp3_sha256(mp3_file, digest) is True

    mp3_file.write_bytes(b"ID3v2_TAMPERED_audio_data_67890")
    assert verify_mp3_sha256(mp3_file, digest) is False


