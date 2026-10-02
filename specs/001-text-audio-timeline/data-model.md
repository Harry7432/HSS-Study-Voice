# Data Model: Timeline de sincronizacao texto-audio

## PreparedDocument

Representa o texto normalizado com identidade preservada antes da sintese.

| Field | Type | Rules |
|-------|------|-------|
| `chunks` | ordered collection of `PreparedChunk` | Non-empty for audio generation |

## PreparedChunk

Agrupamento pai usado pelo pipeline e refletido na timeline.

| Field | Type | Rules |
|-------|------|-------|
| `index` | integer | Zero-based and equal to collection position |
| `sentences` | ordered collection of `PreparedSentence` | Non-empty |
| `text` | derived string | Sentence texts joined in spoken order |

## PreparedSentence

Frase logica definida no texto normalizado antes do agrupamento.

| Field | Type | Rules |
|-------|------|-------|
| `index` | integer | Zero-based within parent chunk |
| `text` | string | Non-empty normalized spoken text |
| `fragments` | ordered collection of `SynthesisFragment` | One or more items |

Repeated text does not imply repeated identity. The identity is `(chunk.index, sentence.index)`.

## SynthesisFragment

Parte interna limitada para sintese. Nao aparece no JSON publico.

| Field | Type | Rules |
|-------|------|-------|
| `index` | integer | Zero-based within logical sentence |
| `text` | string | Non-empty and within configured synthesis limit |
| `wav_path` | path | Temporary, assigned after rendering |
| `frame_count` | integer | Positive, read from actual WAV |

All fragments of one sentence are contiguous and contribute to one public sentence interval.

## TimelineDocument

Root canonical artifact described by the version-1 JSON contract.

| Field | Type | Rules |
|-------|------|-------|
| `schema_version` | integer | Exactly `1` |
| `audio` | `TimelineAudio` | Required |
| `chunks` | ordered collection of `TimelineChunk` | Non-empty |

## TimelineAudio

| Field | Type | Rules |
|-------|------|-------|
| `filename` | string | Basename only, lowercase `.mp3` suffix |
| `sha256` | string | 64 lowercase hexadecimal characters |
| `sample_rate_hz` | integer | Exactly `22050` |
| `total_samples` | integer | Positive verified merged-WAV frame count |

## TimelineChunk

| Field | Type | Rules |
|-------|------|-------|
| `index` | integer | Zero-based and equal to array position |
| `start_sample` | integer | First child sentence start |
| `end_sample` | integer | Last child sentence end |
| `sentences` | ordered collection of `TimelineSentence` | Non-empty |

## TimelineSentence

| Field | Type | Rules |
|-------|------|-------|
| `index` | integer | Zero-based within parent chunk |
| `text` | string | Prepared logical sentence, preserved as Unicode |
| `start_sample` | integer | Inclusive, non-negative |
| `end_sample` | integer | Exclusive and greater than start |

## Timeline invariants

1. First sentence starts at sample `0`.
2. Every sentence starts where the previous sentence ends.
3. Every chunk starts at its first sentence and ends at its last sentence.
4. Every chunk after the first starts where the previous chunk ends.
5. Last sentence and chunk end at `audio.total_samples`.
6. Sum of fragment frames equals each sentence length.
7. Sum of sentence lengths equals the verified merged WAV frame count.
8. All rendered WAVs use compatible PCM format and exactly 22050 Hz.
9. SHA-256 is calculated from the completed MP3 bytes.
10. Sample integers stay at or below `9007199254740991` for interoperable JSON consumers.

## AudioResult extension

The existing result fields remain unchanged. The synchronized flow adds `timeline_path`, pointing
to the published sibling sidecar. Legacy MP3-only calls remain valid and do not fabricate sentence
identity from unstructured chunks.

## Publication state transitions

```text
PREPARING
  -> STAGED        MP3 and timeline written under destination staging
  -> VALIDATED     WAV totals, JSON contract and SHA-256 verified
  -> PUBLISHING    previous state backed up and replacements started
  -> PUBLISHED     both public paths contain the new matching pair
```

On any failure before `PUBLISHING`, staging is removed and public paths are unchanged. On a handled
failure during `PUBLISHING`, rollback restores the exact previous presence and bytes of both paths.
If rollback itself fails, publication raises a dedicated recovery error and retains recoverable
backup material instead of deleting the only valid copy.

## Sidecar derivation

`<stem>.mp3` maps to `<stem>.timeline.json` in the same directory. For example,
`lesson.v2.mp3` maps to `lesson.v2.timeline.json`.
