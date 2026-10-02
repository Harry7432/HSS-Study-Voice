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
