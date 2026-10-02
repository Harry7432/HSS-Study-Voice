# Quickstart: Validate the text-audio timeline

## Prerequisites

- Python 3.13 or newer
- Project dependencies installed through `uv`
- FFmpeg available through `FFMPEG_PATH` or `PATH` for integration validation
- Piper voice files for `DEFAULT_VOICE` for real synthesis validation

Run commands from `backend/` unless stated otherwise.

## 1. Validate existing behavior

```powershell
uv run pytest tests
```

Expected outcome: all pre-existing unit scenarios remain green, including the current `list[str]`
text pipeline and MP3 generation contract. Integration scenarios may skip only through their
existing external-dependency guards.

### Baseline recorded for T001

- Date: 2026-10-01
- Environment: Windows, CPython 3.13.15, pytest 9.1.1
- Command: `uv run pytest tests`
- Result: 50 passed, 5 skipped, 1 warning in 8.52 seconds
- Skip reason: all 5 scenarios in `tests/integration/test_audio_pipeline.py` were skipped because
  FFmpeg was not installed or discoverable in the test environment
- Warning: Starlette deprecated the current `httpx` integration used by `fastapi.testclient`; this
  warning does not fail the existing suite

## 2. Validate structured preprocessing

```powershell
uv run pytest tests/unit/test_chunker.py tests/unit/test_pipeline.py -v
```

Expected outcomes:

- canonical sentence boundaries are defined before chunk grouping;
- repeated text has distinct positional identity;
- an oversized logical sentence has multiple synthesis fragments but one sentence identity;
- current `chunk()` and `process()` results remain unchanged.

## 3. Validate timeline accounting and contract

```powershell
uv run pytest tests/unit/test_timeline.py tests/unit/test_audio_orchestrator.py -v
```

Expected outcomes:

- all ranges are contiguous, half-open integer sample ranges;
- sentence lengths use real WAV frame counts;
- chunk bounds aggregate their sentences;
- merged WAV frames equal the final `total_samples`;
- non-22050 or incompatible WAVs fail before publication;
- serialized output conforms to `contracts/timeline-v1.schema.json` plus domain invariants;
- SHA-256 matches the completed MP3;
- exactly one MP3 export occurs.

## 4. Validate atomic publication

Run the orchestrator failure-injection cases included in the previous command.

Expected outcomes:

- pre-publication failures expose no new file;
- failure during either replacement restores the previous MP3 and timeline byte-for-byte;
- first publication failure leaves neither destination present;
- successful publication leaves no staging or backup files;
- a rollback failure retains recoverable backups and reports a dedicated error.

## 5. Run the real pipeline

```powershell
uv run pytest tests/integration/test_audio_pipeline.py -v
```

The suite skips real synthesis when FFmpeg or the configured voice is unavailable. With both
available, expected outcomes are:

- one valid MP3 and one sibling `<stem>.timeline.json` are produced;
- the timeline SHA-256 matches the MP3;
- all sentence and chunk ranges cover exactly the source PCM timeline;
- the final sentence ends at the merged WAV frame count;
- temporary WAV, staging and backup files are removed.

## 6. Inspect a generated pair

For `example.mp3`, confirm `example.timeline.json` contains only:

- `schema_version`;
- `audio` with filename, SHA-256, sample rate and total samples;
- ordered chunks with ordered sentences and sample ranges.

Recompute the MP3 SHA-256 locally and compare it with `audio.sha256`. Convert a sample boundary to
seconds only for inspection by dividing it by `audio.sample_rate_hz`; seconds are not stored in the
canonical timeline.

## 7. Measure the performance gate

Use the same 60-minute fixture, voice, speed, bitrate and machine for baseline and synchronized
runs. Exclude initial voice download. The synchronized run passes when timeline preparation adds no
more than 5% to the baseline total duration.
