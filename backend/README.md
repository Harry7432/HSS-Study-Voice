# HSS Study Voice — Backend

Local text-to-speech pipeline: Markdown/plain text in, a single MP3 out. Built on Piper TTS
(offline neural synthesis) and FFmpeg (WAV → MP3 encoding).

## Synchronized generation (text-audio timeline)

Besides the legacy `AudioOrchestrator.generate_mp3(chunks: list[str], ...)` flow, the orchestrator
exposes `generate_synchronized(document: PreparedDocument, ...)`, which produces the same single
MP3 **plus** a sidecar JSON timeline that maps every spoken sentence to its exact sample range in
the final audio.

```python
from app.services.text.pipeline import TextPreprocessingPipeline
from app.services.audio.orchestrator import AudioOrchestrator

pipeline = TextPreprocessingPipeline()
document = pipeline.prepare(raw_text)  # structured, sentence-aware — not list[str]

result = AudioOrchestrator().generate_synchronized(
    document=document,
    output_path=Path("output/lesson.mp3"),
)
# result.timeline_path -> output/lesson.timeline.json
```

`document` comes from `pipeline.prepare()`, not `pipeline.process()`. The structured flow defines
canonical sentence boundaries in the normalized text *before* chunk grouping (FR-022), so a
logical sentence keeps a single identity in the timeline even when it is internally split into
several synthesis fragments (long sentences) or when its chunk is grouped differently than the
legacy `chunk()` would group it. Both flows coexist; neither call changes the other's behavior or
output (see `tests/unit/test_pipeline.py` and `tests/unit/test_audio_orchestrator.py` for the
regression tests pinning this).

Exactly one MP3 encoding happens per `generate_synchronized()` call, regardless of how many chunks,
sentences or internal fragments the document has (FR-015, SC-007): all fragments are rendered to
WAV, concatenated once into a single PCM stream, and that stream is encoded to MP3 once.

## Sidecar discovery

The timeline is written next to the MP3, named by replacing the `.mp3` suffix with
`.timeline.json`:

```text
output/lesson.mp3
output/lesson.timeline.json
```

`app.services.audio.timeline.timeline_path_for(mp3_path)` computes this deterministically — no
database or API lookup is involved. `output_path` must be a lowercase-`.mp3` basename; the sidecar
lives in the same directory.

Publication is atomic across both files (FR-016): `generate_synchronized()` stages the new MP3 and
timeline, backs up any previous pair in the destination directory, then replaces both with
`os.replace()` (MP3 first, timeline last — the timeline acts as the commit marker). If staging,
validation, or either replace fails, a compensating rollback restores the previous pair
byte-for-byte and no partial pair is ever exposed; if the rollback itself cannot complete, the
backup files are deliberately **not** deleted and `AudioRollbackError` reports their paths so the
previous state can be recovered manually. On success, no staging or backup files remain.

## PCM-domain timing

Every `start_sample`/`end_sample` boundary is a real PCM frame count read from closed WAV files
with `wave.getnframes()` — never estimated from character count, word count, or predicted
duration (FR-008). Boundaries use the half-open interval convention `[start_sample, end_sample)`,
so a sentence's duration in samples is `end_sample - start_sample`, boundaries never overlap, and
they tile the audio contiguously starting at sample `0`. The sample rate is fixed at 22050 Hz for
schema version 1; any rendered segment at a different rate fails generation before anything is
published, rather than being silently reported as complete.

Accounting is bottom-up and cross-checked twice before publication:

1. Each rendered fragment's frame count is read from its own WAV file.
2. A sentence's samples are the sum of its fragments' frames; a chunk's range spans from its first
   sentence's start to its last sentence's end (FR-012).
3. The merged WAV (the same concatenated PCM later encoded to MP3) must have exactly the same frame
   count as the sum of all fragment frame counts, and the timeline's last `end_sample` must equal
   that merged total (FR-011) — otherwise nothing is published.

## SHA verification

`TimelineAudio.sha256` is computed **after** the MP3 file is completely written — it identifies the
exact delivered artifact, not just the PCM it was encoded from (any later byte change, including
tag edits, invalidates the association). `app.services.audio.timeline.compute_sha256()` hashes the
file in binary mode; `verify_mp3_sha256(mp3_path, expected_sha256)` recomputes and compares it,
entirely offline, with no external service:

```python
from app.services.audio.timeline import compute_sha256, verify_mp3_sha256

digest = compute_sha256(Path("output/lesson.mp3"))
assert verify_mp3_sha256(Path("output/lesson.mp3"), digest)
```

The digest is always 64 lowercase hexadecimal characters. A tampered or swapped MP3 — even one byte
different — fails verification.

## MP3 decoder delay: a known limitation

The timeline's sample boundaries are exact in the **PCM/WAV domain that was encoded**, not in the
decoded output of an arbitrary downstream MP3 player. MP3 (via `libmp3lame`) is a lossy, frame-based
format: encoders commonly prepend encoder/decoder priming samples and pad the final frame to a
multiple of the codec's frame size (1152 samples for the MPEG Layer III used here), and different
decoders handle that padding differently (some strip it via LAME/Xing header gapless metadata, some
don't). This means a player seeking to a `start_sample` converted to a timestamp
(`start_sample / sample_rate_hz`) may be off by a small, decoder-dependent amount — typically on the
order of tens of milliseconds — even though the timeline itself is sample-accurate against the
source WAV.

This was a deliberate trade-off (see `research.md`, "PCM frame accounting" and "MP3 binding"):
measuring the *decoded* MP3 to compensate for this would make correctness depend on which decoder
was used to validate it, which is strictly worse than documenting a bounded, well-understood
limitation. Consumers needing sample-exact playback alignment should decode independently and
verify against `audio.sha256`, or treat the PCM-domain timeline as a close approximation in the
compressed domain rather than an exact one.

## Performance (SC-005)

`scripts/benchmark_timeline.py` compares `generate_mp3()` (baseline) against
`generate_synchronized()` on the same machine, voice, speed, and bitrate, using a generated fixture
sized to a target spoken duration (60 minutes by default, matching the representative scenario in
`spec.md`). Voice-model download time is excluded by design (it is a one-time setup cost, not a
per-run cost); both runs share one warmed-up Piper model so load time is excluded identically from
each. Run it from `backend/`:

```powershell
$env:PYTHONPATH = "."
uv run python scripts/benchmark_timeline.py            # full 60-minute SC-005 gate
uv run python scripts/benchmark_timeline.py --minutes 5 --voice pt_BR-cadu-medium
```

It exits `0` and prints `PASS` when timeline preparation adds no more than 5% to the baseline
total processing time, `1` with `FAIL` otherwise. See `specs/001-text-audio-timeline/quickstart.md`
for the most recently recorded result.
